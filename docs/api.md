# API reference

Everything in `omnisus_db.__all__`, rendered from the source.

## Discovery

Ask the server what exists before deciding what to import.

::: omnisus_db.available
::: omnisus_db.browse

## Planning

Planning is composition: build a list of scopes any way you like and hand it
to `import_dataset`. There is no planner flag on the Python API.

::: omnisus_db.scopes_for
::: omnisus_db.ALL_UFS

## Importing

::: omnisus_db.import_dataset
::: omnisus_db.import_sim
::: omnisus_db.import_sinasc
::: omnisus_db.import_sih
::: omnisus_db.import_cnes_st
::: omnisus_db.import_ibge_pop
::: omnisus_db.import_cnes_master

## Results

::: omnisus_db.sources._base.ImportReport
::: omnisus_db.sources._base.ScopeOutcome
::: omnisus_db.sources._base.ImportResult
::: omnisus_db.sources._base.ScopeKey

## The lake

::: omnisus_db.Lake

## Registry

::: omnisus_db.Dataset
::: omnisus_db.resolve

## Errors

::: omnisus_db.FtpPathNotFound
::: omnisus_db.FtpUnavailable
::: omnisus_db.FtpEntry
