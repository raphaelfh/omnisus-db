"""The researcher guide keeps its shape: seven sections, notebook links, cited sources."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GITHUB = "https://github.com/raphaelfh/omnisus-db/blob/main/"
SECOES = [
    "Em uma frase",
    "O que um registro representa",
    "Datas e geografia",
    "Cobertura e modalidade",
    "Armadilhas",
    "Como usar",
    "Fontes",
]

# Profile page in docs/sources/ -> notebook in notebooks/bases/.
PERFIS = {
    "sim_obitos": "sim_obitos",
    "sinasc_nascidos_vivos": "sinasc_nascidos_vivos",
    "sih_aih_reduzida": "sih_aih_reduzida",
    "sia": "sia",
    "cnes_estabelecimentos": "cnes_estabelecimentos",
    "ibge_populacao": "ibge_populacao",
}


def _texto(perfil: str) -> str:
    return (ROOT / "docs/sources" / f"{perfil}.md").read_text(encoding="utf-8")


def _secao(texto: str, titulo: str) -> str:
    return texto.split(f"\n## {titulo}\n", 1)[1].split("\n## ", 1)[0]


@pytest.mark.parametrize("perfil", sorted(PERFIS))
def test_profile_has_the_seven_sections_in_order(perfil):
    secoes = re.findall(r"^## (.+?)\s*$", _texto(perfil), flags=re.MULTILINE)
    assert secoes[:7] == SECOES
    assert secoes[7:] in ([], ["Detalhes técnicos"])


@pytest.mark.parametrize("perfil", sorted(PERFIS))
def test_profile_links_its_notebook(perfil):
    caminho = f"notebooks/bases/{PERFIS[perfil]}.py"
    assert (ROOT / caminho).is_file()
    assert GITHUB + caminho in _secao(_texto(perfil), "Como usar")


@pytest.mark.parametrize("perfil", sorted(PERFIS))
def test_sources_section_cites_a_document(perfil):
    assert re.search(r"(https?|ftp)://\S+", _secao(_texto(perfil), "Fontes"))
