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

## Publishing is blocked on the wheel gap

`datasus-dbc` publishes cp313 wheels only for manylinux
aarch64/armv7l/ppc64le/s390x. On every mainstream platform `pip install
omnisus-db` resolves to the sdist and needs a Rust toolchain, so most users
cannot install it. Verified directly:

```
$ uv pip install --only-binary=:all: dist/omnisus_db-0.1.0-py3-none-any.whl
  Because all versions of datasus-dbc have no usable wheels and
  omnisus-db==0.1.0 depends on datasus-dbc, we can conclude that
  omnisus-db==0.1.0 cannot be used.
```

`release.yml` runs this as a hard gate and will refuse to publish until it
passes. `test.yml` runs the same check on every PR without blocking, so the
day upstream ships wheels it turns green on its own.

Ways out, in order of preference:

1. Upstream PR to `datasus-dbc` adding cp313/cp314 for mainstream targets.
   Their matrix already builds cp313 for the exotic arches, so this is a
   cibuildwheel configuration change, not new work.
2. Relax `requires-python` to `>=3.12`, where wheels exist today. One line.
3. Document the Rust requirement and publish anyway — the worst option, and
   the reason the gate exists.

Until then, GitHub-only distribution:

```bash
pip install git+https://github.com/raphaelfh/omnisus-db@v0.1.0
```
