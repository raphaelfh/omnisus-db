# Ferramentas de metadados

Utilitários de desenvolvimento e consulta ao contrato público do pacote. A CLI
instalada `omnisus-db` ainda não possui um comando nativo de metadados.

| Local | Responsabilidade |
| --- | --- |
| `scripts/metadados/` | Consultar, validar e gerar os catálogos |
| `docs/dicionario/` | Documentação, contrato público e exemplos históricos identificados |
| `notebooks/desenvolvimento/metadados_cli.py` | Demonstração interativa com comandos executados |
| `src/omnisus_db/data/dicionarios/` | Dicionários usados pela biblioteca |
| `reports/` | Evidências e retratos históricos das auditorias |

Na raiz do checkout, usando o ambiente do projeto:

```bash
# Coluna resolvida pelo pacote; JSON validado pode ser consumido por outros programas
uv run --locked python scripts/metadados/consultar.py --json

# Outro campo, com fontes e revisão declaradas
uv run --locked python scripts/metadados/consultar.py \
  --dataset sih_aih_reduzida --field cod_idade --json

# Exemplo histórico 0.1.0-draft, preservado para comparação
uv run --locked python scripts/metadados/consultar.py \
  --metadata docs/dicionario/exemplos/sim_obitos.sexo.json --json

# Verificação de transporte por coluna
uv run --locked python scripts/metadados/consultar.py --arrow

# Reconstruir catálogo a partir da auditoria existente e conferir PDFs locais
uv run --locked python scripts/metadados/atualizar_catalogo.py --check-local

# Abrir a demonstração
uv run --locked --extra notebooks marimo edit notebooks/desenvolvimento/metadados_cli.py
```

`consultar.py` usa `jsonschema`; o modo `--arrow` também usa `pyarrow`.
`atualizar_catalogo.py` lê o registro canônico empacotado. Os caminhos padrão são
independentes do diretório de execução; caminhos fornecidos como argumentos
são relativos ao diretório atual. Nenhum script faz consultas à rede.

O catálogo é gerado, não editado manualmente. Uma reconstrução não renova as
datas da auditoria nem confirma a semântica de campos ainda pendentes. Veja
[contrato e limitações](../../docs/dicionario/index.md).

`auditar_contrato.py --target <target> --snapshot-id 5 --out <diretorio>` registra
schemas, publicações, SQL e agregados via `LakeReader` somente leitura.
`--acceptance-only` verifica a projeção pública, os estados de conversão e a
preservação de contagens, schemas e histórico de snapshots. Não exporta linhas
individuais; requer acesso ao lake indicado e não faz parte da CI com fixtures.
