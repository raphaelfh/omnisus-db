"""The optional native package is found, rejected or skipped, never silently misused."""

from types import SimpleNamespace

import pytest

from omnisus_db.sources.datasus_ftp import native


def missing(name):
    raise ModuleNotFoundError("module absent", name=name)


@pytest.mark.parametrize("value", ["python", "rust", "auto"])
def test_explicit_backend_wins_over_environment(monkeypatch, value):
    monkeypatch.setenv("OMNISUS_X_BACKEND", "typo")
    assert native.requested_backend(value, variable="OMNISUS_X_BACKEND", label="X") == value


def test_environment_then_auto(monkeypatch):
    monkeypatch.delenv("OMNISUS_X_BACKEND", raising=False)
    assert native.requested_backend(None, variable="OMNISUS_X_BACKEND", label="X") == "auto"
    monkeypatch.setenv("OMNISUS_X_BACKEND", "python")
    assert native.requested_backend(None, variable="OMNISUS_X_BACKEND", label="X") == "python"


def test_unknown_backend_names_the_capability(monkeypatch):
    monkeypatch.setenv("OMNISUS_X_BACKEND", "typo")
    with pytest.raises(ValueError, match=r"^X backend must be python, rust or auto$"):
        native.requested_backend(None, variable="OMNISUS_X_BACKEND", label="X")


def test_python_never_imports(monkeypatch):
    monkeypatch.setattr(native, "import_module", lambda _: pytest.fail("imported"))
    assert native.load_native("python") is None


def test_auto_without_package_is_none(monkeypatch):
    monkeypatch.setattr(native, "import_module", lambda _: missing("omnisus_db_dbf"))
    assert native.load_native("auto") is None


def test_rust_without_package_raises(monkeypatch):
    monkeypatch.setattr(native, "import_module", lambda _: missing("omnisus_db_dbf"))
    with pytest.raises(ImportError, match="omnisus-db-dbf"):
        native.load_native("rust")


def test_missing_transitive_dependency_is_not_hidden(monkeypatch):
    monkeypatch.setattr(native, "import_module", lambda _: missing("pyarrow"))
    with pytest.raises(ModuleNotFoundError):
        native.load_native("auto")


def test_incompatible_api_is_an_error_even_for_auto(monkeypatch):
    monkeypatch.setattr(native, "import_module", lambda _: SimpleNamespace(API_VERSION=99))
    with pytest.raises(ImportError, match=f"API_VERSION={native.API_VERSION}"):
        native.load_native("auto")


def test_compatible_module_is_returned(monkeypatch):
    module = SimpleNamespace(API_VERSION=native.API_VERSION)
    monkeypatch.setattr(native, "import_module", lambda _: module)
    assert native.load_native("rust") is module
