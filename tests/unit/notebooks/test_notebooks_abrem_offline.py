"""Opening a notebook opens no network connection; a bases/ notebook writes nothing.

Every notebook runs in-process with `app.run()`, as `marimo export` would.
Button-gated cells stop at `mo.stop`, so anything reaching the network or the
research lake on open is a failure. The unit conftest also refuses FTP listings.

The guard below patches `socket.socket.connect`, which is what both `ftplib` and
`httpx` use to open a connection. It does not intercept `connect_ex`, DuckDB's
native HTTP client, or Windows asyncio's `ConnectEx`; a notebook that reached the
network through one of those would not be caught here. Loopback addresses are
allowed through because asyncio's event loop builds a self-pipe with a loopback
connect on some platforms.
"""

import importlib.util
import socket
from pathlib import Path

import pytest

NOTEBOOKS = Path(__file__).resolve().parents[3] / "notebooks"

# Helper modules are not notebooks: `_comum.py`, `_performance_dbf.py`, `_acervo/`.
TODOS = sorted(
    p
    for p in NOTEBOOKS.rglob("*.py")
    if not any(part.startswith("_") for part in p.relative_to(NOTEBOOKS).parts)
)

ESPERADOS = {
    "bases/cnes_estabelecimentos.py",
    "bases/ibge_populacao.py",
    "bases/medicamentos.py",
    "bases/sia.py",
    "bases/sih_aih_reduzida.py",
    "bases/sim_obitos.py",
    "bases/sinan.py",
    "bases/sinasc_nascidos_vivos.py",
    "desenvolvimento/api_cenarios.py",
    "desenvolvimento/metadados_cli.py",
    "desenvolvimento/performance_dbf.py",
    "explorar/inventario_dados_reais.py",
    "explorar/panorama_datasus.py",
}

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def test_every_notebook_is_checked():
    assert {p.relative_to(NOTEBOOKS).as_posix() for p in TODOS} == ESPERADOS


@pytest.mark.parametrize("caminho", TODOS, ids=lambda p: p.relative_to(NOTEBOOKS).as_posix())
def test_opening_downloads_and_writes_nothing(caminho, monkeypatch, tmp_path):
    real_connect = socket.socket.connect

    def guarded_connect(self, address):
        # Windows asyncio builds its self-pipe with a loopback connect.
        if not isinstance(address, tuple) or address[0] in _LOOPBACK:
            return real_connect(self, address)
        raise AssertionError(f"{caminho.name} opened a connection to {address!r}")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    dados = tmp_path / "dados"
    monkeypatch.setenv("OMNISUS_NOTEBOOK_DATA", str(dados))
    # `python notebook.py` and marimo put the notebook's folder on sys.path.
    monkeypatch.syspath_prepend(str(caminho.parent))
    spec = importlib.util.spec_from_file_location(f"notebook_{caminho.stem}", caminho)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.app.run()

    if caminho.parent.name == "bases":
        assert not dados.exists(), f"{caminho.name} wrote to the research lake on open"
