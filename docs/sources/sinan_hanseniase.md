# SINAN — Hanseníase

`sinan_hanseniase` importa notificações nacionais de hanseníase, arquivos
`HANSBRYY.dbc`, publicados em **dois diretórios**:
`/dissemin/publicos/SINAN/DADOS/FINAIS` (edição final) e
`/dissemin/publicos/SINAN/DADOS/PRELIM` (edição preliminar). O inventário
consultado em 12/09/2026 continha 2001–2023 como final e 2024–2026 como
preliminar. Disponibilidade e modalidade devem ser consultadas novamente antes
de cada estudo: um ano migra de `prelim` para `final` quando o DATASUS o
republica no outro diretório, e a biblioteca não converte uma modalidade na
outra silenciosamente.

## Descobrir a modalidade de cada ano

```python
import omnisus_db as odb

releases = odb.available_releases("sinan_hanseniase", refresh=True)
for scope, release in sorted(releases.items(), key=lambda item: item[0].ano):
    print(scope.ano, release)
```

`available_releases` lê os dois diretórios e responde de qual deles cada ano
veio. `available()` continua devolvendo apenas os recortes, sem a modalidade.

## Importar e publicar

```python
scopes = [s for s, r in releases.items() if s.ano in (2023, 2026)]
report = odb.import_dataset(
    "sinan_hanseniase", scopes=scopes,
    target="ducklake:./hanseniase.ducklake", policy="skip_same",
    run_id="hanseniase-2026-estudo-01", concurrency=1, batch_size=1,
)
print(report.rows, report.failed)
```

```bash
omnisus-db inventory sinan_hanseniase
omnisus-db import sinan_hanseniase --years 2023 --plan inventory --policy skip_same
```

O recorte nacional é `ScopeKey(uf=None, ano=2026)`. Não aceita filtros de UF ou
mês na aquisição. Use `sg_uf_not` (notificação) ou os campos de residência
originais na consulta, conforme a pergunta científica.

Cada arquivo é buscado no diretório em que foi listado e a linha registra a
modalidade em `_source_release` (`final` ou `prelim`), ao lado de
`_source_ano`. Anos finais e preliminares convivem na mesma tabela; a coluna
diz qual é qual, e `lake.publications()` repete a modalidade por publicação.

## Contrato de integridade e publicação

- O arquivo inteiro passa pela verificação de tamanho e contagem DBF, pelo
  staging Arrow/Parquet e pela mesma transação dos importadores estaduais.
- A identidade da fonte é declarada no YAML (`x-identity`) e verificada por
  moda: `nu_ano` precisa ser o ano pedido e `id_agravo` precisa ser `A309`.
  Erros rejeitam o arquivo inteiro; não há descarte silencioso de linhas.
- `_source_ano` e `_source_release` são reservados à biblioteca e não
  sobrescrevem campos originais.
- `skip_same` verifica novamente a fonte. Se hash ou parser/dicionário mudou,
  exige uma decisão explícita de substituição.
- O manifesto mantém SHA-256, versão, URL de origem, IDs de execução/publicação
  e situação ativa.

## Quando o ano deixa de ser preliminar

```python
with odb.Lake.local("ducklake:./hanseniase.ducklake") as lake:
    movidos = odb.outdated("sinan_hanseniase", lake=lake)
    print(movidos)  # escopos cuja modalidade mudou no servidor
    if movidos:
        odb.import_dataset(
            "sinan_hanseniase", scopes=movidos,
            target="ducklake:./hanseniase.ducklake", policy="replace",
            run_id="hanseniase-final-2024",
        )
```

`outdated()` compara a modalidade publicada no lake com a modalidade listada
hoje no servidor e devolve apenas os escopos que se moveram. A substituição é
sempre explícita: `replace` valida antes de substituir exatamente aquele ano
nacional, e dados e manifesto são publicados atomicamente. Nada é atualizado
por conta própria.

## Interpretação e reprodução

Os 63 campos do YAML são um inventário físico observado em `HANSBR26.dbc`,
**não uma auditoria semântica integral**. Campos adicionais são preservados;
incompatibilidades de tipo seguem a política geral de esquema.

Não confundir notificações com casos confirmados, indivíduos únicos ou
incidência: um registro é uma notificação compulsória, sujeita a revisão,
duplicidade e encerramento posterior. A edição preliminar pode ser revisada,
recontada ou retirada do diretório; a final é a versão consolidada pelo
Ministério da Saúde para aquele ano, e ainda assim não equivale a encerramento
epidemiológico de cada registro. Comparar um ano preliminar com um ano final
compara duas coisas diferentes; use `_source_release` para separá-los.

Fontes: [dicionário SINAN NET Hanseníase v5](https://portalsinan.saude.gov.br/images/documentos/Agravos/Hanseniase/DIC_DADOS_Hanseniase_v5.pdf).
