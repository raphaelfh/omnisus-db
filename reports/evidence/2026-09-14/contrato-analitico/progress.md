# Execução — tipos, idade e contrato analítico

Plano: `docs/superpowers/plans/2026-09-14-tipos-idade-e-contrato-analitico.md`.
Biblioteca: commit de implementação `c51d08d432f19feb17fecda05de444d2f13f31b9`,
branch `codex/contrato-analitico`. App: commit `d98a0c953652deecefc3529c2539ef2edecf0499`, branch homônima no repositório Omnisus;
o recibo da integração fica em `docs/architecture/analytics-snapshot5-acceptance.json`.

## Implementação e limpeza

- Contrato público offline `describe_dataset`, apresentação `display_row` e
  `analytical_projection`, com versões, hash e fontes empacotadas. Tipos físicos
  documentais, tipos lógicos e schema observado têm responsabilidades separadas.
- Regras finitas de idade, sexo e 15 datas SIM/SIH; escopo/release/hash da origem
  precisam coincidir com os arquivos auditados. Valores não interpretáveis têm
  estado explícito. Cálculos nativos DuckDB, sem UDF Python ou alteração do lake.
- Uma definição etária alimenta apresentação e SQL. Foram removidos o schema
  Arrow fictício, o mapa de tipos exclusivo, dois decoders independentes, os
  helpers Polars sem consumidores e a falsa anotação executável `x-transform`.
- No app, relatórios usam idade e sexo analíticos; datas tipadas passam pelo mesmo
  compilador em consulta, filtro, ordenação, paginação e exportação. As faixas
  pertencem ao app. Heurísticas `x-display`, casts de código como idade e o estado
  `age_coded_pending_upstream` foram substituídos pelas capacidades reais.
- Para manter os checks completos, exports de variantes sem consumidores foram
  removidos no frontend e o contexto compartilhado da sidebar ganhou módulo
  próprio, usado pelo componente e pelo app.
- Metadados e apresentação no app usam APIs públicas; backend e notebooks fixam
  o mesmo wheel em `backend/vendor`, com versão e hash nos dois lockfiles.

## Verificação

| Verificação | Resultado |
|---|---|
| Suíte da biblioteca, sem e2e/perf | 894 passaram, 76 skips, 78 deselected; cobertura 93,60% |
| Núcleo final de idade, projeções e metadados | 89 passaram após ajuste da serialização SQL |
| Ruff check/format, mypy e hooks do commit | Passaram; mypy conferiu 53 módulos |
| Contrato JSON das colunas SIM/SIH/SINASC/CNES | 295 colunas válidas |
| Instalação binária fora do checkout, macOS arm64 | Python 3.12.13, 3.13.12 e 3.14.0 passaram |
| Uso offline dos recursos e APIs; SQL nativo no wheel | Passou nas três versões |
| Wheel reconstruído do sdist | Byte a byte idêntico |
| Auditoria do wheel final via LakeReader, snapshot 5 | Contagens, schemas e histórico preservados |
| Backend completo, wheel final | 626 passaram; 137 testes de integração deselected |
| Frontend completo | 282 testes passaram; lint, TypeScript/build e tipos OpenAPI passaram |
| Notebooks completos | 52 passaram; 3 testes PostgreSQL deselected |
| Backend e notebooks, instalação limpa | Ambos instalaram o wheel fixado; verificação de dependências e recursos passou |
| Revisão independente | Sem achados concretos pendentes; inclui distribuição, lockfiles e CI/Docker |

A suíte geral foi executada antes do ajuste da representação de whitespace no SQL;
os 89 testes afetados e a auditoria real foram repetidos depois dele. Não houve
mudança de regra nessa representação. Os skips incluem a extensão Rust opcional
não instalada; e2e/performance e a matriz Linux/Windows não foram executados aqui.
Os workflows conservam/configuram os gates multiplataforma para execução remota.

## Aceitação do recorte

`acceptance.json` e `acceptance.sql` foram produzidos com o **wheel final instalado**,
fora do checkout. Registram a revisão limpa da biblioteca, identidade das regras,
publicações e SQL. O histórico de snapshots permaneceu idêntico.

| Medida | SIM | SIH |
|---|---:|---:|
| Total bruto e analítico | 361.228 | 1.646.463 |
| 0–4 anos | 7.359 | 121.427 |
| 75+ | 159.568 | 192.798 |
| Idade desconhecida | 351 | 0 |
| Categoria feminina | 169.054 | 913.968 |
| Sexo ignorado | 74 | 0 |

Todas as faixas, estados de conversão e contagens estão no recibo JSON; as somas
reconciliam com o denominador completo. A auditoria exporta apenas agregados.

## Artefato

- Versão: `0.3.0`, candidato local ainda não publicado remotamente.
- Wheel: `omnisus_db-0.3.0-py3-none-any.whl`.
- SHA-256: `1a7387cbfc3ee4264be3454fe95c26b3bbf291399ce7cbe282e9a303fc363b0c`.
- Sdist: `omnisus_db-0.3.0.tar.gz`, SHA-256
  `9d08e1507a155ce75e7baf43692124d74f736f118bc777eab128ea21b9d8e8bf`.
- `release-manifest.json` registra cada arquivo e o commit limpo de origem;
  `release-SHA256SUMS` identifica os dois artefatos; `install-smoke.jsonl` registra
  os ambientes. `install_smoke.py` reproduz a verificação do contrato instalado.
- Cópia local durável: `/Users/raphael/PycharmProjects/omnisus-db/dist/0.3.0-candidate/`.

Os commits posteriores de evidência/documentação não alteram os bytes do pacote.
PyPI permanece desabilitado por padrão; não houve tag, push ou publicação remota.

## Limites e pendências reais

- A aplicabilidade inicial cobre somente os hashes/recortes auditados. Ampliar
  anos, UFs, releases ou fontes exige nova evidência, sem fallback numérico.
- SIM: `100`/`200` aparecem em 91 linhas e divergem dos mínimos do documento DOM.
  A regra aceita zero anos nesses arquivos confirmados; a divergência é explícita.
- SIH: o bruto `IDADE=999` não é uma sentinela universal; os compostos `000`/`999`
  são inválidos. `312` e domínios sem idade exata confirmada seguem sem interpretação.
- `ufinform`, `covid_clas`, `mat_clas` e vigências não demonstradas continuam
  pendências documentais. Ausência no snapshot não apaga campos históricos.
- A construção local da imagem Docker foi tentada com tag isolada, mas o Docker
  Desktop falhou ao acessar `ghcr.io:443` para obter a imagem-base uv (`cannot
  assign requested address`). Não chegou às camadas do app. O daemon e sua rede
  não foram reconfigurados; a revisão estática dos caminhos Docker passou.
- Testes específicos de PostgreSQL não foram executados; as suites locais
  de backend e notebooks respeitaram os marcadores existentes.
- A matriz remota Linux/macOS/Windows, a integração em main e a publicação do
  candidato ainda dependem da etapa de distribuição; nenhum resultado remoto
  foi presumido a partir dos testes locais.

Os checkouts originais foram preservados: base da biblioteca `ea6c33f`, app
`1eb65d1`; o plano original não versionado e `.claude/launch.json` do usuário
continuam intactos. Trabalho revisável em `/private/tmp/omnisus-analytics-db` e
`/private/tmp/omnisus-analytics-app`; as branches locais preservam os commits.
