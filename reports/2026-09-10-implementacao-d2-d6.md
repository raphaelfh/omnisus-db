# Implementação D2–D6

Implementação em `codex/d2-d6`, no worktree
`.claude/worktrees/d2-d6`. Base inicial `468145d`; o commit `c795b39` de
notebooks foi incorporado à branch para ajustar os exemplos à nova API.
O checkout principal não foi alterado por esta implementação.

## Entregas

| Entrega | Resultado implementado | Limite explícito |
|---|---|---|
| D2 — origem populacional | Produto/edição obrigatórios; validação de metadados, períodos, categorias, municípios e cobertura; dados e manifesto atômicos; UUID de publicação e referências temporais separadas | Censos 2010/2022 e última edição de estimativa. Estimativas históricas exigem universos territoriais próprios e são recusadas |
| D3 — manutenção/URIs | Compactação com API real; expiração e limpeza separadas com simulação; preservação dos parâmetros PostgreSQL; escape de SQL; CLI retorna erro nas falhas | Validação local. Exclusividade cloud continua externa; `vacuum` legado executa limpeza e está depreciado |
| D4 — tipos/tempo CNES | Promoções de tipo sem perda dentro de famílias; rejeição de coerções incompatíveis; seleção da linha completa mais recente, preservando NULL e recusando empates conflitantes | Dados anteriormente truncados/arredondados precisam ser reconstruídos da fonte. Nome do master não é histórico |
| D5 — coordenação/reprocessamento | Lock cooperativo local antes da conexão; políticas append/skip_same/error_if_exists/replace; manifesto, run/batch IDs e consulta após confirmação perdida; tentativas falhas separadas | SQL externo e alterações que preservem contagens não são certificados pelo manifesto. Escopos legados exigem inventário/reconstrução |
| D6 — recursos | Staging por lotes em disco; inserção direta do Parquet; orçamento de payloads aplicado durante download; cancelamento aguarda liberação do worker; benchmark reproduzível | DBF completo ainda é materializado. Redução de memória medida com custo de tempo/disco; desempenho nacional permanece sem medição representativa |

## Como usar

```python
import omnisus_db as odb

population = odb.import_ibge_pop(years=[2022], product="census")
publication_id = population[0].publication_id

report = odb.import_dataset(
    "sim_do",
    scopes=[odb.ScopeKey(uf="RR", ano=2023)],
    policy="skip_same",
    run_id="sim-rr-2023-01",
)
```

Depois de fechar um handle com confirmação de commit desconhecida, consulte
`Lake.publications(run_id=...)` em um novo handle antes de repetir a escrita.
O manifesto e os dados compartilham a transação; `Lake.attempts(run_id=...)`
lista falhas conhecidas registradas separadamente após rollback.

`append` continua sendo o padrão. `replace` valida um escopo não vazio e exclui
somente UF/ano/mês correspondentes, inclusive no CNES. Duplicatas de eventos não
são removidas com `DISTINCT`. Um manifesto novo não certifica dados legados.

```bash
omnisus-db import ibge-pop --year 2022 --population-product census
omnisus-db import sim --year 2023 --ufs RR --policy skip_same --run-id sim-rr-2023-01
omnisus-db lake optimize sim_do
omnisus-db lake expire-snapshots --before 2026-08-01T00:00:00+00:00 --dry-run
omnisus-db lake cleanup-files --before 2026-08-01T00:00:00+00:00 --dry-run
```

Expiração e limpeza só executam com `--execute`; os métodos Python correspondentes
usam `dry_run=False`. O `vacuum` legado mantém seu comportamento de execução da
limpeza física, sem expirar snapshots.

## Verificação

- Python 3.13.12, macOS: **520 testes aprovados**, cobertura final **92,12%** após
  incorporar os notebooks e normalizar as fixtures. A seleção
  `not e2e and not perf` deixa 47 casos externos/performance fora da suíte normal.
- Python 3.12.13, ambiente temporário: **520 testes aprovados**. A execução final
  inclui os 37 casos Hypothesis inicialmente ausentes do cache offline.
- Wheel e sdist construídos. Instalação nova em Python 3.12 usando exclusivamente
  dependências binárias passou; importação do pacote instalado e uma
  transação real de DuckLake também passaram.
- Ruff, formatação, mypy, catálogo gerado, Frictionless e MkDocs estrito aprovados.
  O notebook ajustado também passou no `marimo check --strict`.
  As mensagens de depreciação de `vacuum` nos testes são esperadas.
- Revisões independentes de IBGE, Lake e integração aprovadas. Os achados de
  retenção de buffers, cancelamento FTP e skip dependente de transação foram
  reproduzidos e corrigidos antes da aprovação final.
- Fontes reais IBGE verificadas em 10/09/2026: censo 2010 com 5.565 municípios,
  censo 2022 com 5.570 e estimativa 2026 com 5.571. URLs, revisões, hashes e soma
  populacional estão em [evidência da fonte](evidence/2026-09-10/d2-d6/task-1-live-verification.json).
  Essa verificação fez coleta e validação completa; os testes transacionais usam
  respostas controladas e lakes temporários.

As referências de população, território, publicação e coleta não são confundidas.
Datas territorial e de publicação ficam NULL quando os documentos selecionados
não as estabelecem. A revisão da fonte é verificada antes/depois da coleta,
sem alegar um snapshot transacional do servidor IBGE.

## Medição de D6

Processos separados, lotes padrão de 100.000 registros, corpus ampliado de
132.440 linhas:

| Medida | Caminho anterior | Staging |
|---|---:|---:|
| Pico RSS | 1328,5 MiB | 758,0 MiB |
| Tempo | 3,705 s | 6,571 s |
| Pico de disco temporário amostrado | 61,9 MiB | 112,5 MiB |

Linhas, schema e hash com ordem preservada coincidiram. O ganho observado de
memória é aproximadamente 43%, acompanhado de aumento de tempo e disco. Há uma
execução por modo; o corpus ampliado repete uma fixture municipal, e a amostragem
de disco a cada 5 ms é um limite inferior. Não é uma medição de carga nacional.
O caso ampliado alimenta o parser com DBF repetido e ignora a descompressão DBC;
esses tempos não representam o pipeline DBC completo. O benchmark também inclui
um caso separado de DBC real com 3.311 linhas, que exercita a descompressão.

Reprodução: `PYTHONPATH=src python scripts/benchmark_resources.py --repeat 40
--batch-rows 100000 --output /tmp/benchmark-d6.json`.
Resultados completos: [benchmark padrão](benchmark-d6-default.json) e
[benchmark com lotes menores](benchmark-d6.json).

Os limites padrão são 512 MiB por DBC e 1 GiB em reservas de payloads comprimidos;
eles não limitam RSS total. DNS/conexão sem socket disponível ainda pode precisar
terminar por timeout após cancelamento, mantendo a reserva até o worker sair.
Windows, Linux e escrita concorrente cloud não foram executados nesta sessão.

## Arquivos de referência

- [Guia operacional](../docs/guides/reprocessing-and-maintenance.md)
- [Contrato IBGE](../docs/sources/ibge_pop.md)
- [Contrato CNES](../docs/sources/cnes_st.md)
- [Revisão final](evidence/2026-09-10/d2-d6/final-review.md)
- [Testes Python 3.13 finais](evidence/2026-09-10/d2-d6/pytest-merged.log)
- [Testes Python 3.12 finais](evidence/2026-09-10/d2-d6/pytest-py312-final.log)
- [Plano executado](../docs/superpowers/plans/2026-09-10-d2-d6.md)

Os logs de regressão anteriores e as revisões preservam os resultados históricos,
incluindo falhas corrigidas; não representam falhas atuais. Espaços de fim de
linha foram normalizados pelos hooks do repositório. Nenhum dado legado foi
migrado, nenhuma carga real foi substituída, e não houve push ou merge na `main`.
