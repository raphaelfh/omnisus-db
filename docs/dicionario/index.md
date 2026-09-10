# Dicionário de dados e proveniência

O dicionário deve responder, para **cada campo de uma tabela e edição**: o que
significa, como interpretar os valores, de onde veio essa interpretação, quando
foi conferida e a quais dados ela se aplica.

**Decisão de estrutura:** manter os YAMLs empacotados da biblioteca como fonte
única das definições; acrescentar proveniência e versões; gerar documentação e
JSON para consumo a partir deles. A referência oficial é a evidência externa;
o YAML é a representação editorial dessa evidência. Um rótulo já existente na
biblioteca não constitui confirmação oficial.

## O que está disponível aqui

| Material | Uso |
| --- | --- |
| [Arquitetura e organização](estrutura.md) | Onde editar cada informação, identidades e versões |
| [Contrato por coluna](contrato.md) | Descrição, códigos, evidência e aplicabilidade |
| [Catálogo da auditoria](catalogo.md) | Cobertura das 18 categorias e fontes consultadas |
| [Manutenção e checagem](manutencao.md) | Atualização, conflitos, revisão e critérios de publicação |
| [Consumo e integração](consumo.md) | Uso atual, protótipo JSON/Arrow e implantação na lib |
| [JSON Schema](schemas/column-metadata.schema.json) | Contrato experimental `0.1.0-draft` |
| [Exemplo SIM / DO / SEXO](exemplos/sim_do.sexo.json) | Um campo com evidência oficial localizada |
| [Registro das fontes](fontes/registro.json) | URLs, SHA-256, tamanho e data da consulta |
| [Cobertura em CSV](cobertura.csv) | Inventário consumível das lacunas |
| [Inventário por campo](campos.csv) | 1.326 ocorrências, tipos físicos, definições locais e fontes candidatas |

O contrato e a integração descritos são uma proposta implementável. O protótipo
JSON e seu validador são executáveis; a biblioteca **ainda não fornece** a API
pública de metadados proposta nem anexa automaticamente esses metadados a todas
as colunas. Os YAMLs e decodificadores de produção não foram alterados por esta
organização documental.

## Escopo e limites da evidência

A auditoria de 10/09/2026 amostrou as 18 categorias do portal: 17 produziram
tabelas e uma corresponde a aplicativos TABWIN/TABNET. Foram observadas 65
tabelas e 1.326 ocorrências de colunas. Isso cobre as categorias escolhidas,
**não todos os subtipos, períodos e esquemas possíveis** do DATASUS.

“Subtipo” corresponde ao tipo de arquivo/produto dentro da categoria, como
CNES/ST ou SIHSUS/RD. Dentro de um ZIP ainda pode haver várias tabelas. A mesma
grafia de coluna em produtos diferentes não garante o mesmo significado.

Foram obtidos 14 PDFs oficiais. A auditoria encontrou rótulos locais para 252
ocorrências de colunas e mapas locais de códigos para 87. Essas contagens são de
correspondência nominal, não de validação semântica. O catálogo preserva essa
distinção. A checagem pontual do exemplo `SEXO` não altera retroativamente os
resultados da auditoria.

## Começar

1. Consulte [catálogo](catalogo.md) para identificar o produto e suas lacunas.
2. Use o [contrato](contrato.md) ao documentar um campo.
3. Siga o processo de [checagem](manutencao.md) antes de marcar uma interpretação
   como conferida.
4. Execute o [protótipo](consumo.md) para consumir o exemplo como metadado de
   coluna e verificar seu transporte em Arrow/Parquet.
