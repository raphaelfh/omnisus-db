# Ferramentas de metadados

Utilitários de desenvolvimento e consulta experimental do checkout. A CLI
instalada `omnisusdb` ainda não possui um comando nativo de metadados.

| Local | Responsabilidade |
| --- | --- |
| `scripts/metadados/` | Consultar, validar e gerar os catálogos |
| `docs/dicionario/` | Documentação, contrato experimental e exemplos declarativos |
| `notebooks/desenvolvimento/metadados_cli.py` | Demonstração interativa com comandos executados |
| `src/omnisus_db/data/dicionarios/` | Dicionários usados pela biblioteca |
| `reports/` | Evidências e retratos históricos das auditorias |

Na raiz do checkout, usando o ambiente do projeto:

```bash
# JSON validado; stdout pode ser consumido por outros programas
uv run --locked python scripts/metadados/consultar.py --json

# Documento específico
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
`atualizar_catalogo.py` usa a biblioteca padrão. Os caminhos padrão são
independentes do diretório de execução; caminhos fornecidos como argumentos
são relativos ao diretório atual. Nenhum script faz consultas à rede.

O catálogo é gerado, não editado manualmente. Uma reconstrução não renova as
datas da auditoria nem confirma a semântica de campos ainda pendentes. Veja
[contrato e limitações](../../docs/dicionario/index.md).
