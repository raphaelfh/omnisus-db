# Expansão de fontes: SINAN e medicamentos

## Entrega

- `sinan_chagas_prelim`: arquivos nacionais preliminares, sem UF artificial,
  identidade verificada antes da publicação e reutilização do núcleo transacional.
- URL da fonte nas publicações FTP; migração aditiva dos manifestos antigos.
- Marimo `sinan_chagas.py`: descoberta, contrato, plano salvo, aquisição explícita,
  recuperação e análise com proveniência.
- Inventário Marimo existente adaptado a seleção, resumo e exportação nacionais.
- Marimo `medicamentos.py`: caminho SIA-AM existente apresentado como APAC de
  medicamentos, com aquisição, relatório, resumo e proveniência persistidos.
- Cliente `fetch_stock_page`: observação HTTP limitada do estoque BNAFAR/Hórus,
  com bytes originais, URL, horário e hash. Sem promessa de completude ou
  publicação transacional de uma página como se fosse o dataset integral.

## Evidência real

[SINAN](sinan-chagas-verification.json): arquivos preliminares completos de 2023
(6.253 registros), 2024 (6.520) e 2025 (7.588), total 20.361. Reexecução com
`skip_same`: zero linhas novas e três publicações preservadas.

[Medicamentos](medicamentos-verification.json): SIA-AM/RR janeiro de 2024,
2.083 registros; reexecução sem linhas novas. Uma página de estoque público
BNAFAR/Hórus adquirida com identidade preservada. Os lakes de verificação foram
criados em diretórios próprios, registrados nos JSONs; não alteraram lakes anteriores.

## Garantias e verificação

| Garantia | Evidência automatizada |
|---|---|
| Recorte nacional não inventa UF nem sobrescreve ano/geografia originais | `test_sinan_chagas.py` — pipeline DBF sintético completo |
| Agravo/ano incorretos e DBF truncado não substituem publicação válida | `test_sinan_chagas.py` — validação e preservação de dados/manifesto |
| Substituição nacional preserva outros anos; rollback restaura manifesto e linhas | `test_national_publication_replace_and_rollback` |
| Não misturar publicação estadual e nacional na mesma tabela | `test_national_cannot_replace_state_table` |
| URL da fonte adicionada a manifesto antigo, inclusive vários escopos na mesma transação | `test_legacy_manifest_url_migration_and_two_publications_in_one_transaction` |
| Fluxo nacional existente exporta dados completos em CSV/Parquet | `test_sinan_inventory.py` executa a célula real contra DuckLake |
| Página HTTP curta/vazia não comprova completude; falhas não viram dados vazios | 22 testes do cliente BNAFAR/Hórus |
| Arquivo real pode ser publicado e repetido sem duplicação | `tests/integration/test_sinan_chagas_e2e.py` (rede, execução explícita) |

A suíte offline ampla passou com **650 testes**, 59 desmarcados e duas advertências
de depreciação já exercitadas pelos testes de manutenção. Depois, a regressão
adicional de migração e os fluxos novos passaram no grupo focado de **30 testes**.
Esses grupos se sobrepõem; não devem ser somados como testes distintos.
Mypy passou nos 48 arquivos de código; Ruff e formatação passaram. MkDocs passou
em modo estrito. Os dois novos notebooks passaram na checagem estrutural Marimo
e em exportação HTML sem iniciar aquisição de dados.

Uma revisão independente encontrou agrupamento estadual remanescente no resultado
do inventário nacional: corrigido e coberto por execução da célula. A suíte ampla
encontrou uso de cache obsoleto na migração do manifesto durante uma transação
com vários escopos: corrigido com leitura do esquema atual e teste de regressão.
Um link documental antigo para relatório fora de `docs/` foi ajustado para que
o build estrito permanecesse verificável.

## Limitações que continuam explícitas

- Não houve benchmark comparativo com PySUS; esta entrega não comprova
  superioridade global de desempenho ou cobertura.
- Chagas final/histórica e outros agravos não estão incluídos neste contrato.
  O dicionário é inventário físico, sem alegação de auditoria semântica integral.
- Notificações não são casos confirmados ou pessoas únicas. APAC não é contagem
  de doses, pessoas únicas ou eventos individuais de dispensação.
- Extração pública de eventos de dispensação da assistência farmacêutica básica
  **não foi confirmada e não foi implementada**. Estoque e indicadores MGDI
  não preenchem essa lacuna. Fontes e alternativas estão em
  `docs/sources/medicamentos.md`.
- O notebook ainda usa thread para a API síncrona. Interromper célula não garante
  cancelamento da aquisição; plano/run_id permitem inspecionar a execução.
- `append` continua padrão da API; exemplos novos escolhem `skip_same`.
  Locks são locais/cooperativos; não há nova garantia de escrita distribuída.

## Reproduzir

```bash
uv run --locked pytest tests -m 'not e2e and not perf' -q
uv run --locked pytest tests/integration/test_sinan_chagas_e2e.py -q
uv run --locked --extra notebooks marimo edit notebooks/sinan_chagas.py
uv run --locked --extra notebooks marimo edit notebooks/medicamentos.py
```

O teste de rede depende da disponibilidade e da estabilidade da edição publicada
durante suas duas aquisições. Mudança de hash no intervalo deve falhar, não ser
tratada como replay equivalente.
