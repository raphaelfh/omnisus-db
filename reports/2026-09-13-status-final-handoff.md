# Status final do omnisus-db para a equipe Omnisus — 2026-09-13

Varredura de `main` em `480ddcb`. A tag `v0.2.0` aponta para `b46ae4d`; desde
então `main` recebeu as correções de CI e de Windows do PR #7 e as seis
atualizações do Dependabot (#1–#6), sem mudança de API.

Este documento substitui o estado "sem remote" de
`reports/2026-09-12-entrega-v0.2.0.md`. O conteúdo técnico daquele relatório e
de `reports/2026-09-11-handoff-omnisus-app.md` continua válido.

## 1. Resumo

| Item | Estado | Evidência |
| --- | --- | --- |
| Versão | `0.2.0` (`src/omnisus_db/_version.py`) | tag `v0.2.0` local e no remote |
| Repositório | Público: https://github.com/raphaelfh/omnisus-db | `main` sincronizado com `origin/main` |
| Documentação | No ar: https://raphaelfh.github.io/omnisus-db/ | HTTP 200 |
| PyPI | Não publicado, por decisão | — |
| GitHub Release | Publicada: https://github.com/raphaelfh/omnisus-db/releases/tag/v0.2.0 | roda, sdist e `SHA256SUMS` |
| Workflow `release` da tag | Gate de instalação verde em Linux, macOS e Windows; falha do `publish` (`invalid-publisher`) é esperada e não será reexecutada | run 34734467309 |
| CI | Verde em `main` (`480ddcb`, depois do PR #7 e dos seis PRs do Dependabot): `test`, `native DBF` e `docs` com sucesso em Linux, macOS e Windows; só falha `wheel-only install (ubuntu, py3.13)`, não bloqueante e esperada | runs 34741554932, 34741555062, 34741554896 |
| Suíte local (offline) | 744 passed, 2 skipped (PostgreSQL descartável ausente) | `uv run pytest -m "not e2e and not perf"` |
| Lint e tipos | `ruff check` e `mypy src` limpos | 49 arquivos-fonte |
| Roda | `omnisus_db-0.2.0-py3-none-any.whl`, 173 KB, construída da tag | instala com `--only-binary=:all:` em Python 3.12 limpo |

## 2. Como instalar hoje

Não há PyPI, por decisão. O canal é a roda da GitHub Release `v0.2.0`, com SHA-256
`03fdce3f7508856b8a6fe898e0e615d74972e1c1cbb127e387871e2888d30217`
(173 KB). Para reconstruí-la: `git checkout v0.2.0 && uv build --wheel`.

```bash
# A roda da GitHub Release
pip install --only-binary=:all: https://github.com/raphaelfh/omnisus-db/releases/download/v0.2.0/omnisus_db-0.2.0-py3-none-any.whl

# Ou direto da tag, sem arquivo
pip install "git+https://github.com/raphaelfh/omnisus-db@v0.2.0"
```

Python 3.12 é o piso e o caminho sem toolchain Rust. Em 3.13, `datasus-dbc`
não tem roda cp313 para macOS/Linux x86_64 e exige `cargo`.

## 3. Superfície pública (congelada em 0.2.0)

- Importação: `import_dataset(nome, scopes=, policy=, concurrency=, batch_size=)`,
  `import_cnes_estabelecimentos`, `import_cnes_master`, `import_ibge_populacao`.
- Descoberta: `available()`, `available_releases()`, `scopes_for()`, `outdated()`,
  `datasets()`, `products()`.
- Lake: `Lake.local/cloud`, `Lake.publications()`, `Lake.delete_scope()`,
  `LakeReader` (leitura sem lock, `snapshot_id` opcional), `CatalogAttachError`.
- CLI: `omnisus-db init | inventory | import | query | doctor | lake`.
- Datasets do FTP (13): `sim_obitos`, `sinasc_nascidos_vivos`, `sih_aih_reduzida`,
  `cnes_estabelecimentos`, `sia_bpa_individualizado`, `sia_apac_medicamentos`,
  `sia_apac_quimioterapia`, `sia_apac_tratamento_dialitico`,
  `sia_apac_laudos_diversos`, `sia_apac_cirurgia_bariatrica`, `sia_psicossocial`,
  `sinan_chagas`, `sinan_hanseniase`. Mais `ibge_populacao` por função própria.

Quebra em relação a 0.1.0: nomes antigos (`sim_do`, `sih_rd`, `import_sim`, ...)
não existem mais e não há alias. A tabela de renomeação está no adendo de
`reports/2026-09-11-handoff-omnisus-app.md`.

## 4. O que a equipe do app faz agora

1. Instalar a roda da GitHub Release `v0.2.0` e conferir o SHA-256 contra `SHA256SUMS`.
2. Aplicar as trocas por módulo da seção 4 de `reports/2026-09-11-handoff-omnisus-app.md`
   (`LakeReader`, `products()`, `row["scope"]`, `delete_scope`), usando os nomes novos.
3. Reconstruir o lake em um target novo ("Migrate a legacy lake" em
   `docs/guides/reprocessing-and-maintenance.md`): `available()` → `import_dataset`
   com `policy="skip_same"` → conferir `publications()` → trocar o target.
4. Agendar `outdated()` para reimportar escopos que migraram de preliminar para final.
5. Validar com `OMNISUS_TEST_POSTGRES_URL` apontando para um PostgreSQL descartável
   (os 2 testes pulados localmente).

## 5. Correções e pendências do lado do pacote

Corrigido em `main` pelo PR #7, com CI verde em Linux, macOS e Windows:

- **Bug real no Windows:** o staging mapeava em memória cada lote `.arrow` e o
  apagava com a tabela ainda viva; o Windows nega o `unlink` (`WinError 5`) e
  todo import falhava. Agora o lote é lido para a memória.
- `mypy` no Windows: `locking.py` passa a ramificar por `sys.platform`.
- Cache de listagem: expira quando a idade é igual ao TTL (`>=`). O relógio do
  Windows avança a cada ~16 ms, e `ttl_hours=0` não expirava.
- `tzdata` como dependência só no Windows: sem ela, `expire_snapshots` e
  `cleanup_files` falhavam ao converter `TIMESTAMPTZ` (o Windows não tem base de fusos).
- Notebook `_acervo`: o DBF temporário é fechado antes da leitura e removido depois.
- Testes e notebooks leem JSON e YAML como UTF-8 (o Windows usava cp1252).
- `test.yml`: `UV_PYTHON` por célula; a célula 3.12 perdia o `ruff`.
- `native.yml`: roda principal fora do `dist/` do contêiner root; roda do sdist
  construída para 3.12.
- `docs.yml`: deploy num job só de push; PRs não tocam mais o environment.
- CHANGELOG (padrão do DBF é `auto`) e `RELEASE.md` (sem as notas pré-remote).

Atualizações mescladas depois do PR #7, cada uma com CI verde:

- GitHub Actions: `actions/checkout` 7, `actions/setup-python` 7,
  `astral-sh/setup-uv` 7, `actions/upload-pages-artifact` 5, `actions/deploy-pages` 5
  (PRs #5, #3, #1, #2, #6). Somem os avisos de Node 20 obsoleto.
- `marimo` 0.24.0 (PR #4).

Ainda abertas:

| Pendência | Impacto | Ação |
| --- | --- | --- |
| Extensão Rust `omnisus-db-dbf` não publicada | Nenhum: Python é usado quando ela falta | Trusted Publisher próprio e tag `dbf-v*` |
| Python 3.13 sem `cargo` | Instalação falha em 3.13 x86_64/macOS | Aguardar rodas cp313 do `datasus-dbc`; usar 3.12 |
| U2 (metadados versionados), revisão instalada | Adiados | `load_dicionario` e SHA da roda no app |
| Medicamentos (dispensação) | Sem fonte pública | `docs/sources/medicamentos.md` |
| Outros agravos SINAN | Um YAML e uma linha do registro cada | Caminho de `sinan_hanseniase` |
| Timeouts de 2 s em `tests/unit/sources/datasus_ftp/test_runner_failures.py` | Falha intermitente no Windows (ocorreu uma vez no PR #4; passou ao reexecutar) | Ampliar para um limite generoso que só detecte deadlock |

**Aviso ao app sobre Windows:** a `v0.2.0` tem três defeitos que só aparecem no
Windows. O staging falha em todo import (`WinError 5`), `expire_snapshots` e
`cleanup_files` falham sem `tzdata`, e o cache de listagem nunca expira com
`ttl_hours=0`. Todos estão corrigidos em `main` pelo PR #7.
As notas da GitHub Release registram isso como problema conhecido. Quem roda
imports no Windows deve esperar a versão seguinte.

## 6. Referências

- Entrega e caminho do primeiro dia medido: `reports/2026-09-12-entrega-v0.2.0.md`
- Mudanças por módulo no app: `reports/2026-09-11-handoff-omnisus-app.md`
- SINAN e dispensação: `reports/2026-09-12-sinan-e-dispensacao.md`
- Decisões: `docs/decisions/0001-rust-dbf.md`, `docs/decisions/0002-registry-as-catalog.md`
- Histórico completo: `CHANGELOG.md`
