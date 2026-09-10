"""Checks for the educational archive, independent of live DATASUS availability."""

import io
import struct
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "notebooks"))
from _acervo import tabelas


def dbf_bytes():
    # Two physical rows: one active and one deleted. Codes must keep zeros.
    header = bytearray(32)
    header[0] = 3
    struct.pack_into("<IHH", header, 4, 2, 65, 7)
    field = bytearray(32)
    field[:6] = b"CODIGO"
    field[11] = ord("C")
    field[16] = 6
    return bytes(header + field + b"\r" + b" 001234" + b"*999999" + b"\x1a")


def test_dbf_sample_preserves_codes_and_counts_deleted(tmp_path):
    result, df = tabelas.read_dbf(dbf_bytes(), tmp_path, limit=1)
    assert df.to_dicts() == [{"CODIGO": "001234"}]
    assert result["registros_declarados"] == 2
    assert result["registros_ativos"] == 1
    assert result["registros_excluidos"] == 1
    assert result["colunas"][0]["tipo_origem"] == "C"
    assert result["colunas"][0]["largura"] == 6


def test_truncated_dbf_is_not_published_as_complete(tmp_path):
    with pytest.raises(ValueError, match="truncado"):
        tabelas.read_dbf(dbf_bytes()[:-5], tmp_path, limit=200)


def test_archive_members_are_not_extracted_as_paths(tmp_path):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("../../outside.dbf", dbf_bytes())
    source = tmp_path / "raw.zip"
    source.write_bytes(stream.getvalue())
    with pytest.raises(ValueError, match="caminho"):
        tabelas.inspect_file(source, tmp_path / "output", limit=200)
    assert not (tmp_path.parent / "outside.dbf").exists()


def test_zip_identifies_tables_and_binaries_without_running_them(tmp_path):
    source = tmp_path / "raw.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("tabela.dbf", dbf_bytes())
        archive.writestr("program.exe", b"MZ example only")
        archive.writestr("LEIAME.txt", b"Arquivo de teste")
    result = tabelas.inspect_file(source, tmp_path / "output", limit=200)
    assert len(result["tabelas"]) == 1
    assert len(result["membros"]) == 3
    assert result["tabelas"][0]["linhas_amostra"] == 1
    assert not list((tmp_path / "output").rglob("*.exe"))


def test_zip_expansion_limit(tmp_path, monkeypatch):
    source = tmp_path / "raw.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("large.dbf", dbf_bytes())
    monkeypatch.setattr(tabelas, "MAX_EXPANDED_BYTES", 10)
    with pytest.raises(ValueError, match="limite"):
        tabelas.inspect_file(source, tmp_path / "output", limit=200)


@pytest.mark.parametrize(
    "url",
    [
        "https://ftp.datasus.gov.br/x",
        "ftp://example.org/x",
        "ftp://ftp.datasus.gov.br/a/../secret",
        "ftp://ftp.datasus.gov.br/%0d%0aDELE%20x",
    ],
)
def test_ftp_download_only_accepts_public_datasus_paths(url):
    from _acervo.coleta import safe_ftp_path

    with pytest.raises(ValueError):
        safe_ftp_path(url)


def test_fallback_can_leave_a_state_with_only_empty_files(tmp_path, monkeypatch):
    from datetime import datetime

    from _acervo import coleta
    from _acervo.catalogo import BY_KEY

    from omnisus_db.sources.datasus_ftp.inventory import FtpEntry, Listing

    source = BY_KEY["SISMAMA"]

    def entry(name, size):
        return FtpEntry(
            name,
            source.directory + "/" + name,
            source.directory,
            False,
            size,
            datetime(2023, 1, 1),
        )

    entries = (
        entry("CMRR1301.dbc", 1771),
        entry("CMRR1302.dbc", 1771),
        entry("CMSP1409.dbc", 10012),
    )

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return [
                {
                    "arquivo": "CMRR1301.dbc",
                    "endereco": "ftp://ftp.datasus.gov.br" + entries[0].path,
                }
            ]

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(coleta.httpx, "Client", Client)
    monkeypatch.setattr(coleta, "list_dir", lambda *a, **kw: Listing(entries, 0, source.directory))
    candidates, _ = coleta.discover(source, tmp_path)
    assert [e.name for e in candidates[:2]] == ["CMRR1301.dbc", "CMSP1409.dbc"]


def test_portal_subtypes_are_parsed_without_executing_script():
    from _acervo.catalogo import portal_types

    script = 'throw new Error("must not run"); var a=[{fonte:"SIM", sigla_arquivo:"DO", desc_arquivo:"Obitos", abrangencia:"UF"}];'
    assert portal_types(script) == [
        {"fonte": "SIM", "sigla_arquivo": "DO", "desc_arquivo": "Obitos", "abrangencia": "UF"}
    ]
