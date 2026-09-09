# Release procedure

Tag and push. Everything else is `release.yml`.

```bash
# 1. Set the version. It has exactly one home.
$EDITOR src/omnisus_db/_version.py

# 2. Move the Unreleased section of CHANGELOG.md under the new version.
$EDITOR CHANGELOG.md

git commit -am "release: v0.2.0"
git tag v0.2.0
git push origin main --tags
```

`release.yml` then checks the tag against the packaged version, runs the
wheel-only install gate on Linux, macOS and Windows, builds, and publishes to
PyPI via Trusted Publishing (OIDC) with PEP 740 attestations. There is no
long-lived token to configure or rotate.

## One-time setup, still pending

This repository has **no git remote**. Nothing in `.github/workflows/` has ever
run, `https://raphaelfh.github.io/omnisus-db` does not exist, and the install
URL in the README 404s.

```bash
gh repo create raphaelfh/omnisus-db --public \
    --description "Python library for ingesting Brazilian public health databases into DuckLake" \
    --source . --remote origin
git push -u origin main
```

Then, in the repository settings:

- **Pages** → build from GitHub Actions (for `docs.yml`).
- **Environments** → create `pypi`, and register the Trusted Publisher on PyPI
  (project `omnisus-db`, owner `raphaelfh`, repo `omnisus-db`, workflow
  `release.yml`, environment `pypi`).

## The wheel gap, and why the floor is 3.12

`datasus-dbc` publishes cp313 wheels only for manylinux
aarch64/armv7l/ppc64le/s390x. On cp313 for any mainstream platform,
`pip install omnisus-db` falls back to the sdist and needs a Rust toolchain.
It does publish cp312 wheels for Linux, macOS and Windows.

`requires-python` was `>=3.13` for no reason anyone recorded — there is no
3.13-only syntax in the package, and the whole suite passes on 3.12. Lowering
the floor to `>=3.12` is what unblocks release. Verified directly:

```
$ uv venv -p 3.12 .g
$ uv pip install --only-binary=:all: dist/omnisus_db-0.1.0-py3-none-any.whl
Installed 78 packages
$ .g/bin/python -c "import omnisus_db; print(omnisus_db.__version__)"
0.1.0
```

**This is a partial fix, and the CI comments say so.** A user who is already on
3.13 still cannot install without cargo; they need 3.12, or they need upstream
to ship wheels. `release.yml` gates on 3.12, where the install genuinely works.
`test.yml` also runs the gate on 3.13 without blocking, so the remaining gap
stays visible and turns green on its own the day upstream fixes it.

The real fix is still worth doing: a PR to `datasus-dbc` adding cp313/cp314 for
mainstream targets. Their matrix already builds cp313 for the exotic arches, so
it is a cibuildwheel configuration change, not new work.
