"""Live portal discovery and bounded FTP downloads for the learning archive."""

from __future__ import annotations

import ftplib
import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

import httpx

from omnisus_db.sources.datasus_ftp.inventory import list_dir

from .catalogo import PORTAL_API, PORTAL_SCRIPT, SOURCES, Source, portal_types
from .tabelas import inspect_file

MAX_DOWNLOAD_BYTES = 64 * 1024**2
MAX_TOTAL_BYTES = 256 * 1024**2


def now():
    return datetime.now(UTC).isoformat()


def save_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def safe_ftp_path(url):
    parsed = urlsplit(url)
    path = unquote(parsed.path)
    if (
        parsed.scheme != "ftp"
        or parsed.hostname != "ftp.datasus.gov.br"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 21)
        or any(c in path for c in "\r\n\x00")
        or ".." in Path(path).parts
    ):
        raise ValueError("URL fora do FTP público DATASUS ou caminho inválido")
    return path


def discover(source: Source, folder: Path):
    params = {
        "fonte[]": source.key,
        "tipo_arquivo[]": source.subtype,
        "modalidade[]": source.modality,
    }
    if source.year:
        params.update({"ano[]": str(source.year), "uf[]": source.uf, "mes[]": "01"})
    portal_error = None
    try:
        with httpx.Client(timeout=45) as client:
            response = client.post(PORTAL_API, data=params)
            response.raise_for_status()
            portal_rows = response.json()
            if not isinstance(portal_rows, list):
                raise ValueError("formato inesperado no inventário do portal")
        save_json(
            folder / "portal.json",
            {
                "consulta_utc": now(),
                "endpoint": PORTAL_API,
                "parametros": params,
                "resposta": portal_rows,
            },
        )
    except (httpx.HTTPError, ValueError) as error:
        portal_rows, portal_error = [], f"{type(error).__name__}: {error}"
        save_json(
            folder / "portal.json",
            {
                "consulta_utc": now(),
                "endpoint": PORTAL_API,
                "parametros": params,
                "erro": portal_error,
            },
        )
    primary = [
        r
        for r in portal_rows
        if str(r.get("arquivo", "")).lower().endswith((".dbc", ".zip", ".dbf"))
    ]
    # A live portal URL takes precedence. Fixed fallback roots are documented in catalogo.py.
    directory = (
        str(Path(safe_ftp_path(primary[0]["endereco"])).parent) if primary else source.directory
    )
    listing = list_dir(directory, timeout_seconds=30, max_retries=2)
    entries = [asdict(e) for e in listing.files]
    save_json(
        folder / "inventario.json",
        {
            "consulta_utc": now(),
            "diretorio": directory,
            "linhas_nao_interpretadas": listing.skipped,
            "arquivos": entries,
        },
    )
    files = [
        e
        for e in listing.files
        if e.name.lower().endswith((".dbc", ".zip", ".dbf"))
        and 0 < e.size_bytes <= MAX_DOWNLOAD_BYTES
    ]
    if source.key == "DATASUS":
        files = [e for e in files if e.name.upper().startswith("TAB")]
    elif source.key != "Base Territorial":
        files = [e for e in files if e.name.upper().startswith(source.subtype.upper())]
    primary_names = {r["arquivo"].upper() for r in primary}

    def rank(entry):
        name = entry.name.upper()
        # Prefer requested UF, then a small but useful file instead of empty headers.
        state_matches = name.startswith(source.subtype.upper() + source.uf) if source.uf else True
        return (
            name not in primary_names,
            entry.size_bytes < 10000,
            not state_matches,
            entry.size_bytes,
            name,
        )

    candidates = sorted(files, key=rank)
    if not candidates:
        raise ValueError(f"Nenhum arquivo elegível até 64 MiB em {directory}")
    return candidates, {
        "diretorio": directory,
        "arquivos_no_diretorio": len(entries),
        "candidatos": len(candidates),
        "portal_erro": portal_error,
        "portal_resultados": portal_rows,
        "listagem_nao_interpretadas": listing.skipped,
    }


def download(entry, path: Path):
    """Download once to .part; verify advertised length before publication."""
    part = path.with_suffix(path.suffix + ".part")
    remote = safe_ftp_path("ftp://ftp.datasus.gov.br" + entry.path)
    received = 0
    digest = hashlib.sha256()
    try:
        with ftplib.FTP("ftp.datasus.gov.br", timeout=45) as ftp, part.open("wb") as output:
            ftp.encoding = "latin-1"
            ftp.login()

            def write(block):
                nonlocal received
                received += len(block)
                if received > MAX_DOWNLOAD_BYTES:
                    raise ValueError("Download excedeu limite de 64 MiB")
                digest.update(block)
                output.write(block)

            ftp.retrbinary("RETR " + remote, write)
        if received != entry.size_bytes:
            raise ValueError(f"Tamanho diverge da listagem: {received} != {entry.size_bytes}")
        part.replace(path)
    finally:
        part.unlink(missing_ok=True)
    return digest.hexdigest(), received


def collect(run_dir: Path, keys=None, *, limit=200, progress=print):
    run_dir.mkdir(parents=True, exist_ok=False)
    sources = [s for s in SOURCES if keys is None or s.key in keys]
    if not sources:
        raise ValueError("Selecione ao menos uma categoria")
    manifest = {
        "inicio_utc": now(),
        "limite_linhas": limit,
        "fontes": [],
        "escopo": "Um arquivo por categoria; primeiras linhas por tabela, sem representatividade estatística.",
    }
    # Retain the source of the portal's labels/subtype definitions, without executing JS.
    try:
        response = httpx.get(PORTAL_SCRIPT, timeout=30)
        response.raise_for_status()
        (run_dir / "portal_transferencia.js").write_bytes(response.content)
        manifest["portal_script"] = {
            "url": PORTAL_SCRIPT,
            "sha256": hashlib.sha256(response.content).hexdigest(),
        }
        manifest["tipos_portal"] = portal_types(response.text)
    except (httpx.HTTPError, ValueError) as error:
        manifest["portal_script_erro"] = str(error)
    total_bytes = 0
    for index, source in enumerate(sources):
        progress(f"[{index + 1}/{len(sources)}] {source.key}: inventário e amostra real")
        folder = run_dir / source.key.replace(" ", "_")
        folder.mkdir()
        item = {
            **source.as_dict(),
            "status": "falha",
            "tentativas": [],
            "tabelas": [],
            "membros": [],
            "documentos": [],
        }
        try:
            candidates, inventory = discover(source, folder)
            item["inventario"] = inventory
            for candidate in candidates[:4]:
                if total_bytes + candidate.size_bytes > MAX_TOTAL_BYTES:
                    raise ValueError("A execução atingiria o limite total de 256 MiB")
                raw = folder / candidate.name
                # Count attempted reservations even on transfer failure to bound retries.
                total_bytes += candidate.size_bytes
                try:
                    sha, size = download(candidate, raw)
                    output = folder / (candidate.name + "_amostras")
                    inspected = inspect_file(raw, output, limit=limit)
                    attempt = {
                        "arquivo": candidate.name,
                        "url": "ftp://ftp.datasus.gov.br" + candidate.path,
                        "bytes": size,
                        "sha256": sha,
                        "coleta_utc": now(),
                        "modificado_servidor": candidate.modified.isoformat(),
                    }
                    populated = any(t["linhas_amostra"] > 0 for t in inspected["tabelas"])
                    if not populated and source.kind != "aplicativo":
                        item["tentativas"].append(
                            {
                                **attempt,
                                "status": "vazio",
                                "motivo": "Arquivo sem registros nas tabelas lidas.",
                            }
                        )
                        continue
                    item.update(inspected)
                    item.update(
                        {
                            "status": "artefato" if source.kind == "aplicativo" else "amostra",
                            "arquivo": {**attempt, "local": str(raw.resolve())},
                        }
                    )
                    item["tentativas"].append({**attempt, "status": item["status"]})
                    break
                except (OSError, ValueError, RuntimeError, ftplib.Error) as error:
                    item["tentativas"].append(
                        {
                            "arquivo": candidate.name,
                            "status": "falha",
                            "motivo": f"{type(error).__name__}: {error}",
                        }
                    )
            if item["status"] == "falha":
                item["erro"] = "Nenhuma amostra utilizável nas tentativas; consulte os motivos."
        except Exception as error:
            # A failed source is an explicit result, never a replacement with mock data.
            item["erro"] = f"{type(error).__name__}: {error}"
        manifest["fontes"].append(item)
        save_json(folder / "fonte.json", item)
        save_json(run_dir / "manifesto.json", manifest)
        progress(f"  {source.key}: {item['status']}, {len(item['tabelas'])} tabela(s)")
    manifest["fim_utc"] = now()
    manifest["completo"] = len(sources) == len(SOURCES) and all(
        s["status"] != "falha" for s in manifest["fontes"]
    )
    save_json(run_dir / "manifesto.json", manifest)
    # Readers always receive a finished attempt, with explicit per-source failures.
    latest = run_dir.parent / "latest.json"
    save_json(
        latest.with_suffix(".tmp"), {"manifesto": str((run_dir / "manifesto.json").resolve())}
    )
    latest.with_suffix(".tmp").replace(latest)
    return manifest
