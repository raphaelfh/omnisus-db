# Handoff para a equipe do app Omnisus — omnisus-db `main` em `e8ad836`

Data: 2026-09-11. Repositório local, sem publicação. Tudo abaixo está em `main`,
com CHANGELOG, testes unitários (700 passando, cobertura 92%), lint/mypy limpos
e os dois casos de integração PostgreSQL executados contra um `postgres:17`
descartável.

## 1. O que mudou no `main` desde `ee97cb9`

| Commit | Entrega |
| --- | --- |
| `3e0da96` | CHANGELOG preenchido para os quatro commits anteriores; `CatalogAttachError` |
| `e3ee8c3` | `LakeReader` (U3), base `Session` compartilhada com `Lake`, correção de `parse_target` |
| `8b13de0`, `eea2a34` | Spec e plano de U4/U5 (`docs/superpowers/`) |
| `2d5ec43` | `publications()` devolve `scope` decodificado (`ScopeKey`) |
| `41bfef5` | `Lake.delete_scope` + `DeletionResult` (U5) |
| `629dc11`, `fe971c4` | Caso PostgreSQL de remoção; docs (remoção, migração por rebuild, reconciliação) |
| `e8ad836` | `datasets()`, `products()`, `Product` (U1) |

## 2. Decisões tomadas (com o porquê)

- **Sem adoção de dados legados (U4).** Linhas sem manifest nunca são certificadas
  no lugar. Migração é rebuild em um target novo, com proveniência desde o primeiro
  import. Roteiro em `docs/guides/reprocessing-and-maintenance.md`, "Migrate a
  legacy lake". Isso é o que desbloqueia T14: não esperem uma função de adoção.
- **U2 (metadados versionados) adiado.** É o roteiro de `docs/dicionario/consumo.md`,
  etapas 2–6, majoritariamente curadoria editorial de 1.326 colunas. Um resolver
  sem essa curadoria devolveria `applicability: unknown` para tudo — o que o
  `legacy_unreviewed` de vocês já diz. Continuem com `load_dicionario` (caminho
  interno, estável) até U2 ter uma data.
- **IBGE e cnes_master não entram em `_omnisus_publications`.** A limitação está
  declarada nas docstrings e em `products()`: `ibge_pop` reconcilia por
  `publication_id` em `ibge_population_manifest`; `cnes_master` é upsert idempotente,
  reconcilia rodando de novo.
- **Falha de ATTACH:** `CatalogAttachError.stage` ∈ `install | attach | set_option`,
  mensagem com a classe DuckDB, DSN nunca incluída (causa não encadeada em
  catálogos remotos).
- **Revisão instalada / `__version__`:** adiado. Mantenham o registro de SHA do wheel
  e `git_status` do lado do app.
- **Auxiliares e manutenção (501):** nada a fazer no pacote — `bootstrap_auxiliares`,
  `optimize`, `expire_snapshots` e `cleanup_files` já existem em `Lake`. O "contrato
  durável" citado nos 501 é do worker de vocês.

## 3. API pública nova

```python
import omnisus_db as odb

# Leitura sem lock, sem bootstrap, sem set_option; mesma gramática de target.
with odb.LakeReader(target, snapshot_id=None) as reader:      # snapshot_id fixa a sessão
    reader.connect(); reader.tables(); reader.snapshots()
    reader.publications(run_id=...)   # cada linha tem row["scope"]: ScopeKey | None
    reader.attempts(run_id=...)

# Remoção coerente com o manifest (transação gerenciada; escopo anual cobre os meses).
with odb.Lake.local(target) as lake:
    result = lake.delete_scope("sih_rd", odb.ScopeKey(uf="RR", ano=2023))
    result.rows_deleted, result.publications_retired   # odb.DeletionResult

# Catálogo declarado uma vez.
odb.datasets()   # tuple[Dataset, ...] — a face pública do REGISTRY
odb.products()   # tuple[Product, ...]: name, dataset, scope_fields, policies, reconcile_by, inventory

# Erro tipado ao abrir o catálogo (Lake.local, Lake.cloud, LakeReader).
odb.CatalogAttachError  # .stage
```

`products()` para os três tipos de família:

| name | scope_fields | policies | reconcile_by | inventory |
| --- | --- | --- | --- | --- |
| FTP estadual (`sim_do`, `sih_rd`, …) | `("uf","ano")` ou `("uf","ano","mes")` | as quatro | `run_id` | sim |
| FTP nacional (`sinan_chagas_prelim`) | `("ano",)` | as quatro | `run_id` | sim |
| `ibge_pop` | `("product","ano")` | `("append",)` | `publication_id` | não |
| `cnes_master` | `()` | `("append",)` | `rerun` | não |

Não há "primeiro ano de estimativa": o pacote só rejeita `ESTIMATE_UNAVAILABLE_YEARS`
e uma estimativa é importável apenas como última edição, verificada ao vivo.

## 4. O que fazer no app, por módulo

1. **`integrations/omnisus_db/queries.py`** — trocar o `read_session` caseiro por
   `LakeReader(target, snapshot_id=snapshot_id)`; manter `SET threads/memory_limit/
   enable_progress_bar` sobre `reader.connect()`; capturar `odb.CatalogAttachError`
   no lugar de `duckdb.Error` no ATTACH; remover `parse_target`, `quote_literal` e o
   ATTACH manual com seletor `postgres:`. A exigência de catálogo PostgreSQL no perfil
   shared vira política do app (o reader aceita SQLite também).
2. **`notebooks/src/omnisus_notebooks/connection.py`** — `LakeReader` em vez de
   `Lake.local`; a checagem de arquivo com `parse_target` sai (catálogo ausente é
   `CatalogAttachError` com `stage == "attach"`, sem criar nada).
3. **`integrations/omnisus_db/metadata.py`** — `list_datasets`/`import_form` derivam de
   `odb.products()`; somem `REGISTRY`, os casos especiais e o piso 2010. Campos de
   escopo vêm de `Product.scope_fields`, políticas de `Product.policies`,
   `availability_supported` de `Product.inventory`.
4. **`integrations/omnisus_db/imports.py`** — `reconcile()` usa `row["scope"]`; a ponte
   `_publication_scope` sobre `_source_ano` sai. `_IBGE_LIMITATIONS` e
   `_MASTER_LIMITATIONS` continuam corretos; `Product.reconcile_by` diz o mesmo.
5. **`api/data_management.py`** — `DELETE /{sistema}/{uf}/{ano}` passa a chamar
   `Lake.delete_scope(tabela, ScopeKey(uf=uf, ano=ano))` no worker de escrita e
   responder o `DeletionResult`; em datasets mensais o ano cobre todos os meses e
   retira cada publicação mensal. Os 501 de auxiliares/manutenção dependem só do
   contrato do worker de vocês.
6. **`tests/unit/test_integration_boundary.py`** — continua valendo. Caminhos internos
   que podem deixar de ser usados: `sources.datasus_ftp.datasets.REGISTRY`,
   `lake.catalog.parse_target`, `lake.sql.quote_literal`. Permanecem internos e
   estáveis por enquanto: `transforms.dictionaries` (até U2) e as constantes de
   `sources.ibge.products`.
7. **T14 (cutover)** — seguir "Migrate a legacy lake": target novo → `available()` +
   import com `run_id` e `policy="skip_same"` → conferir `publications()` → trocar a
   string de target → aposentar o lake antigo. O lake antigo não é tocado.

## 5. Como validar

Como no procedimento de vocês: `make local-wheel` a partir de `e8ad836` com árvore
limpa; `make check-backend-tests`; `make check-postgres` com
`OMNISUS_TEST_POSTGRES_URL` descartável. `ImportPolicy` não mudou, logo o CHECK da
migration 0005 continua igual. Correção que afeta vocês diretamente: `parse_target`
perdia o `//` de DSNs `postgresql:///?host=…` (só parâmetros); se algum ambiente
usa esse formato, ele passa a funcionar.

## 6. Pendências do lado do pacote

- U2: aguardando agenda de curadoria; brainstorm próprio quando houver.
- Identificação da revisão instalada: adiado.

## Adendo 2026-09-12 — nomes

Toda linha do registro foi renomeada para o nome legível do DATASUS; não existe
alias e os lakes existentes precisam ser reconstruídos em um target novo (ver
"Migrate a legacy lake" em `docs/guides/reprocessing-and-maintenance.md`):

| Antes | Depois |
| --- | --- |
| `sim_do` | `sim_obitos` |
| `sinasc_nv` | `sinasc_nascidos_vivos` |
| `sih_rd` | `sih_aih_reduzida` |
| `sia_bi` | `sia_bpa_individualizado` |
| `sia_am` | `sia_apac_medicamentos` |
| `sia_aq` | `sia_apac_quimioterapia` |
| `sia_atd` | `sia_apac_tratamento_dialitico` |
| `sia_ad` | `sia_apac_laudos_diversos` |
| `sia_abo` | `sia_apac_cirurgia_bariatrica` |
| `sia_ps` | `sia_psicossocial` |
| `cnes_st` | `cnes_estabelecimentos` |
| `sinan_chagas_prelim` | `sinan_chagas` |
| `ibge_pop` | `ibge_populacao` |
| `import_cnes_st` | `import_cnes_estabelecimentos` |

Não existe alias nenhum; as tabelas do lake carregam os nomes novos e um lake
existente precisa ser reconstruído em um target novo.
