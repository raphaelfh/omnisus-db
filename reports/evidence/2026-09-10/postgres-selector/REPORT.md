# Correção PostgreSQL/DuckLake — 10/09/2026

A falha continuava presente na revisão `7d08a43fc501689c90d5e2a0ccb95969fcf1db47`.
O checkout começou limpo; as mudanças recentes da auditoria de fontes já estavam
incorporadas nessa revisão (incluindo suporte nacional de Chagas). Nenhuma alteração
preexistente foi descartada. Não havia AGENTS.md/CLAUDE.md no repositório; foram
consideradas as instruções fornecidas na sessão e os três documentos de evidência
em `/private/tmp/omnisus-restructure-20260910/docs/architecture/`.

## Arquivos alterados

- `src/omnisus_db/lake/connection.py`: acrescenta `postgres:` antes da URI apenas
  para os esquemas `postgres` e `postgresql`. Mudança de produção: 5 linhas novas
  e substituição da expressão do ATTACH. Contratos públicos, parser, quoting SQL,
  esquemas locais, fechamento em erro e exceção sem credenciais preservados.
- `tests/unit/lake/test_connection.py`: seis casos novos para ambos os esquemas
  PostgreSQL, SQLite/DuckDB locais, escaping de aspas e ocultação de credenciais
  no traceback com fechamento da conexão.
- `tests/integration/test_postgres_lake.py`: dois casos reais pela API pública
  `from omnisus_db import Lake, ScopeKey`. Banco UUID exclusivo por caso, staging
  de duas linhas sintéticas, cleanup em finally e variável de ambiente explícita.
- Esta pasta: relatório, logs, patch das alterações rastreadas e manifest com
  hashes dos arquivos, incluindo o novo teste ainda não rastreado.

Não foi criado commit, merge, release ou publicação PyPI.

## Testes realmente executados

| Execução | Resultado | Evidência |
| --- | --- | --- |
| Unitários novos antes da correção | 2 falharam (seletores PostgreSQL), 4 passaram | unit-before.log |
| Gate PostgreSQL antes da correção | 2 falharam em Lake.cloud/ATTACH | postgres-before.log |
| Gate PostgreSQL + tests/unit/lake + tests/unit/test_public_api.py após correção | 123 passaram; 2 avisos de depreciação de vacuum em testes existentes | tests-after.log |
| Gate com wheel instalado em ambiente novo, Python -I e pytest pythonpath vazio | 2 passaram | wheel-gate.log |
| Ruff check e format --check nos três arquivos Python alterados | passaram | lint.log |
| git diff --check | passou | verificação final da sessão |
| uv build --wheel | passou | build.log |
| Comparação de todos os arquivos do pacote dentro do wheel com src/ | hashes iguais | manifest.json |

Ambiente: PostgreSQL **17.11**, DuckDB **1.5.5**, Python **3.13.12**, psycopg **3.3.5**.
O PostgreSQL veio da imagem local `postgres:17`, contêiner exclusivo sem volumes,
porta publicada apenas em 127.0.0.1 e autenticação trust para este ensaio descartável.
Não foram usados dados reais nem bancos operacionais. Nenhuma base de teste restou
na consulta final; o contêiner `--rm` foi encerrado.

O gate valida abertura, publicação gerenciada com hash do staging, leitura ordenada,
publication_id no manifest, snapshot_id retornado e presente no histórico, uma
única nova snapshot, skip_same sem novas linhas/publicações/snapshots e persistência
após fechar/reabrir. O caso roda tanto com postgres:// quanto com postgresql://.
Leitura usa o método público Lake.connect(); não implementa um novo reader.

## Identidade do wheel

Arquivo local (162797 bytes):

`/Users/raphael/PycharmProjects/omnisus-db/dist/postgres-selector-20260910/omnisus_db-0.1.0-py3-none-any.whl`

- Revisão base: `7d08a43fc501689c90d5e2a0ccb95969fcf1db47`
- Conteúdo: revisão base **mais a correção local não commitada**.
- SHA-256: `583dc545b399df86a8efb85f867561f8e0936c22f924fde28e5ae81679251f4e`
- SHA-512: `fb9c7f513fbed1fad6288a3c7974b90f7400bc23bc5becf6a91b25df6278b8554fb7177eb4aba1b95be0a550a9aa70159bb916e0ecc59fbb9ccf1f6cded64e8a`

`manifest.json` registra também árvore Git, hashes dos fontes, entradas empacotadas,
inputs de build e alterações/testes. `source-environment.txt` e
`wheel-environment.txt` distinguem os ambientes. A versão 0.1.0 foi preservada e
**não identifica sozinha este conteúdo**. O diretório dist é ignorado pelo Git;
transportar wheel e manifest juntos. O manifest é a identidade deste build, não de
futuros builds nem de um checkout editável em evolução.

## Consumo pela sessão do Omnisus

Verificar SHA-256 antes de instalar. Exemplo para o ambiente isolado daquela sessão:

```bash
shasum -a 256 /Users/raphael/PycharmProjects/omnisus-db/dist/postgres-selector-20260910/omnisus_db-0.1.0-py3-none-any.whl
uv pip install --python /private/tmp/omnisus-restructure-backend-venv/bin/python --reinstall-package omnisus-db --no-deps /Users/raphael/PycharmProjects/omnisus-db/dist/postgres-selector-20260910/omnisus_db-0.1.0-py3-none-any.whl
```

`--no-deps` pressupõe aquele ambiente já preparado; num ambiente vazio, instalar
as dependências normalmente. Manter DuckDB 1.5.5 para reproduzir este ensaio.
Não instalar pelo número de versão no índice nem usar instalação editável como
substituto da identidade do artefato. Preservar o manifest anterior e registrar
este novo artefato no manifest do Omnisus. A instalação acima é instrução de
handoff: esta tarefa não modificou o ambiente da sessão do Omnisus.

Com PostgreSQL **descartável novo** e `OMNISUS_TEST_POSTGRES_URL` exportada para ele,
com permissão CREATE DATABASE, executar na worktree do aplicativo:

```bash
cd /private/tmp/omnisus-restructure-20260910
make check-import-gate BACKEND_PYTEST=/private/tmp/omnisus-restructure-backend-venv/bin/pytest
make check-postgres BACKEND_PYTEST=/private/tmp/omnisus-restructure-backend-venv/bin/pytest
```

Primeiro executar check-import-gate (já usa --runxfail). Após aprovação, remover o
xfail estrito obsoleto de test_upstream_cloud_writer_gate no Omnisus antes de
check-postgres: com a correção, esse marcador produz XPASS(strict) e falha a suíte.
Repetir também os contratos/backend/notebooks daquele aplicativo, pois este wheel
inclui a revisão recente das fontes, diferente do wheel anterior da reestruturação.
Não foi executado o gate do aplicativo nesta tarefa.

Para repetir o novo gate deste pacote com o wheel já instalado no ambiente de
validação criado aqui:

```bash
cd /Users/raphael/PycharmProjects/omnisus-db
OMNISUS_TEST_POSTGRES_URL='postgresql://postgres@127.0.0.1:PORTA/postgres' /private/tmp/omnisus-db-selector-wheel-20260910/bin/python -I -m pytest -o pythonpath= tests/integration/test_postgres_lake.py -q
```

Sem a variável, o teste é pulado; um skip não é aprovação do gate. São necessários
psycopg, pytest e as extensões DuckLake/PostgreSQL disponíveis para DuckDB. O
ambiente novo foi instalado com acesso à rede após o cache offline se mostrar
incompleto. O build inicialmente esbarrou na restrição de acesso ao cache uv e
foi repetido com acesso autorizado. Nenhuma dessas tentativas valida funcionamento
offline.

## Limites

Não executada a suíte completa de todas as fontes, FTP real, S3/cloud storage,
outros servidores/versões, Python 3.12, desempenho ou concorrência PostgreSQL.
Catálogo PostgreSQL foi real; os arquivos Parquet ficaram em armazenamento local
temporário. Os testes não ampliam contratos de metadados nem fazem migração/delete,
novo reader público ou cutover. A aprovação é da falha de seleção e da publicação
sintética nesta combinação de versões; a liberação integral do Omnisus depende
dos gates próprios e das frentes separadas já registradas.
