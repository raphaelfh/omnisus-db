# Manutenção e atualização

## Fluxo de trabalho

1. **Identificar o produto.** Registrar categoria, subtipo, tabela física,
   período, situação preliminar/final e arquivo amostrado. Confirmar o dataset
   correspondente; não associar SIA/PA ao YAML de SIA/BI só pela categoria.
2. **Localizar a referência oficial.** Priorizar leiaute/dicionário do órgão
   produtor para a edição do produto. Tabelas auxiliares oficiais sustentam
   domínios. Material secundário serve como pista e deve ser identificado como
   tal, sem receber a autoridade de uma fonte primária.
3. **Congelar a evidência.** Registrar URL, órgão, título, edição, tamanho,
   SHA-256 e data da obtenção. Arquivos podem ficar em cache fora do Git;
   preservar uma cópia recuperável na infraestrutura do projeto quando existir
   um arquivo institucional autorizado. Uma URL com hash detecta alteração,
   mas não garante que a versão antiga continuará disponível.
4. **Extrair afirmações.** Preencher descrição, domínio, formato e relações com
   página/seção. OCR ou busca de nomes gera candidatos para revisão, não
   confirmação semântica.
5. **Fazer a segunda checagem.** Comparar a extração com o documento renderizado
   e conferir o vínculo com o leiaute/período do arquivo real. Registrar cada
   método e sua evidência. Comparar outra referência oficial aplicável quando
   disponível; uma inconsistência não deve ser resolvida por suposição.
6. **Revisar valores e estrutura.** Comparar nomes, tipos e valores observados
   com a definição, guardando o arquivo/hash/recorte. Frequências observadas
   não completam um domínio documental nem provam vigência histórica.
7. **Validar e publicar uma edição.** Validar contratos, referências, hashes,
   intervalos e cobertura; gerar docs/JSON; revisar o diff. Distribuir os
   metadados com a lib somente após passar pelos critérios abaixo.

“Double check” tem dois resultados independentes: **transcrição conferida** e
**aplicabilidade conferida**. No exemplo SIM, o primeiro foi realizado e o
segundo está pendente para os dados de 2023. Uma revisão por outra pessoa pode
ser registrada com identidade própria; não inventar essa etapa quando não houve.

## Quando atualizar

Rever o produto quando surgir documento com hash novo, campo novo/removido,
tipo incompatível, código fora do domínio ou divergência relatada por usuário.
Antes de cada publicação da lib, gerar o relatório de pendências e conferir as
fontes dos produtos alterados. Como política inicial, revisar trimestralmente o
índice de fontes de produtos ativos; o responsável pode ajustar a cadência por
produto. Nenhuma automação periódica foi instalada por estes documentos.

Uma consulta que encontra os mesmos bytes atualiza `last_checked_on` da fonte,
não a data de revisão de cada afirmação. Novo hash cria **nova revisão** da
fonte e abre a revisão dos campos dependentes. Conservar o histórico anterior.

## Critérios de validação para a integração

| Verificação | Resultado esperado |
| --- | --- |
| Contrato | JSON/YAML válido e versão suportada |
| Referências | IDs únicos; todos os IDs de fontes/domínios resolvidos |
| Evidência | Afirmação verificada com fonte oficial, localizador, responsável, método e data |
| Mudança editorial | Hash do valor checado coincide com o valor publicado |
| Identidade | Campo pertence ao produto e à edição corretos |
| Vigência | Sem ambiguidades silenciosas para o mesmo recorte |
| Domínio | Códigos string únicos, sem perda de zeros; desconhecidos preservados |
| Observação | Arquivo e hash identificados; diferenças explicitadas |
| Cobertura | Denominador por tabela/edição; campo ausente não desaparece do relatório |
| Compatibilidade | Decodificadores existentes e ingestão não mudam por edição bibliográfica |
| Distribuição | JSON, Arrow/Parquet e recursos no wheel conferidos |

Separar cobertura de descoberta, de descrição verificada, de códigos verificados
e de aplicabilidade confirmada. Não somar menções textuais com campos validados.
A contagem de ocorrências considera cada tabela; campos homônimos em tabelas
diferentes não são deduplicados globalmente.

## Falhas e conflitos

Quando não houver documentação, manter o campo com significado desconhecido e
registrar onde se procurou e a data. “Não encontrado” não significa “não existe”.
Em conflito, registrar as duas referências, as afirmações concorrentes e o
recorte afetado; impedir interpretação automática nova até resolução. Não
substituir o valor bruto por um palpite ou descartar códigos desconhecidos.

## Atualizar o catálogo inicial

Na raiz do repositório:

```bash
python docs/dicionario/scripts/atualizar_catalogo.py
python docs/dicionario/scripts/atualizar_catalogo.py --check-local
```

O primeiro comando reconstrói os arquivos documentais a partir da auditoria
congelada de 10/09/2026. O segundo também verifica tamanho e SHA-256 dos PDFs
presentes no cache local. **Esses comandos não fazem uma nova consulta à rede**
nem avançam a data de checagem. Para uma auditoria nova, produzir seus relatórios
e indicar `--audit-dir reports/AAAA-MM-DD-mapa-datasus`.
