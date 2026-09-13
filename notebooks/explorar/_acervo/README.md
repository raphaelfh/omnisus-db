# Auxiliares do panorama DATASUS

Estes módulos apoiam `../panorama_datasus.py`; não ampliam o registro de importadores
nem a API pública de `omnisus_db`. A leitura é exploratória e conserva códigos como
texto, com os descritores físicos DBF em separado.

| Arquivo | Responsabilidade |
| --- | --- |
| `catalogo.py` | 18 categorias, subtipos sugeridos, perguntas de estudo e diretórios de fallback verificados |
| `coleta.py` | Consulta ao portal, listagem FTP, seleção, download limitado, hashes, tentativas e manifesto |
| `tabelas.py` | Integridade DBF, descompressão DBC, inspeção ZIP, amostras e descritores |
| `relatorio.py` | Mapas CSV/JSON e relatório Markdown gerados do mesmo manifesto |

A seleção tenta primeiro o arquivo retornado pelo portal. Os candidatos seguintes
priorizam arquivos com pelo menos 10 KB (para reduzir a chance de cabeçalhos vazios),
a UF sugerida e depois o menor tamanho. O nome escolhido e a modalidade do portal
são registrados; a sugestão de ano/UF não garante o recorte final. Até quatro
arquivos podem ser tentados. O arquivo nacional pode ser grande, mesmo quando a
amostra final tem apenas 200 linhas.

O inventário guarda todos os arquivos do diretório listado, inclusive outros subtipos.
O relatório de colunas descreve apenas as tabelas dos arquivos amostrados. Os
subtipos documentados no JavaScript oficial são extraídos como campos textuais;
o código remoto não é executado.

ZIPs são lidos em memória, sem extrair caminhos fornecidos pelo servidor e sem
executar seus componentes. A expansão é limitada a 512 MiB e 5.000 membros.
O DBF é preferido quando o ZIP contém uma cópia CSV da mesma tabela. Um DBF com
registros truncados não é publicado como uma amostra válida. Os bytes originais
sempre permanecem preservados.

Testes: `uv run --locked --extra dev pytest tests/unit/notebooks/test_acervo.py -q`.
A validação real das 18 categorias está em `../../../reports/2026-09-10-mapa-datasus/`.
