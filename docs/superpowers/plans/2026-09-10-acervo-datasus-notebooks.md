# Plano: acervo didático DATASUS

Objetivo: organizar os notebooks e estudar as 18 categorias indicadas pelo usuário
com arquivos reais, amostras inspecionáveis e relatório de tabelas/colunas.

- [x] Organizar a navegação em uma trilha: panorama das 18 categorias, inventário,
  análise SIM e cenários da API; preservar arquivos e mudanças preexistentes.
- [x] Descobrir pelo endpoint do portal e confirmar arquivos no FTP. Registrar
  consultas, diretórios efetivamente listados, metadados e limites da cobertura.
- [x] Baixar um arquivo por categoria em acervo local, com SHA-256, limites de
  bytes e isolamento de falhas; guardar os originais sem executar programas.
- [x] Extrair primeiras 200 linhas por tabela, descritores DBF, esquema e
  indicadores da amostra; inspecionar membros ZIP e documentos auxiliares.
- [x] Criar notebook marimo com download explícito, reutilização da última cópia,
  filtros por categoria/tabela, esquema, amostras e exportação.
- [x] Gerar mapa Markdown/CSV/JSON das categorias, arquivos, tabelas, colunas,
  contagens e limitações. Distinguir esquema observado de dicionário semântico.
- [x] Verificar limites e parsers com testes específicos, executar aquisição real
  nas 18 categorias, conferir artefatos e exportar o notebook para HTML.

Escopo: uma amostra por categoria do seletor, sem alegar cobertura de todos os
subtipos, anos, UFs ou registros existentes no DATASUS. Períodos históricos são
escolhidos deliberadamente quando os sistemas foram descontinuados. Falhas e
artefatos sem linhas tabulares permanecem no mapa, sem substituição sintética.
