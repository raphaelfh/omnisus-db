# Release procedure

## Optional native package

`native/omnisus-db-dbf` provides the Rust DBF reader and DBC decompressor. It
builds independently of the main Hatchling package. Its version has one home
in `Cargo.toml`; Maturin exposes that version to Python. The pinned toolchain
and `Cargo.lock` are committed. Build with:

```bash
uv build native/omnisus-db-dbf --wheel --out-dir dist/native
uv build native/omnisus-db-dbf --sdist --out-dir dist/native
```

One abi3 wheel per platform (Linux x86_64, Windows x86_64, macOS arm64/x86_64)
serves CPython 3.12 and later; it is smoke-tested on 3.12, 3.13 and 3.14. The
`native.yml` workflow produces tested artifacts on pull requests, main pushes,
manual dispatch and `dbf-v*` tags. It does not publish packages. Every
native-only installation must use binary dependencies and pass outside the
checkout.

`omnisus-db` does not depend on this package: it decodes DBF and DBC in pure
Python without it. Before a native PyPI release, configure its own Trusted
Publisher and promote the artifacts that passed the complete matrix. Use
`dbf-v<version>` for the native package; `v<version>` continues to identify
the main package. Only after the native version is available in the index
should the main package add a `native` extra and update `uv.lock`; an
unpublished dependency must not break base installs. Until then, install the
locally built wheel directly. The main wheel stays `py3-none-any` and Python
decoding remains available.

## Main Python package

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

## Repository setup

The remote is public at https://github.com/raphaelfh/omnisus-db and the
documentation site deploys from `main` to https://raphaelfh.github.io/omnisus-db.
The `github-pages` and `pypi` environments exist.

**The package is not published to PyPI, by decision.** The distribution
channel is the wheel file built from the tag:

```bash
git checkout v0.2.0
uv build --wheel --out-dir dist
pip install dist/omnisus_db-0.2.0-py3-none-any.whl
```

`release.yml` still runs on every `v*` tag. Its install gate is useful, and its
`publish` job fails with `invalid-publisher` because no PyPI Trusted Publisher
exists. That failure is expected, as in the `v0.2.0` run; do not re-run it.

To publish later, the PyPI account owner adds a pending Trusted Publisher
(project `omnisus-db`, owner `raphaelfh`, repository `omnisus-db`, workflow
`release.yml`, environment `pypi`) and re-runs only the failed job with
`gh run rerun <run-id> --failed`.

## Supported Python

`requires-python` is `>=3.12`. The wheel-only install gate in `test.yml` and
`release.yml` installs the built wheel with `--only-binary=:all:` on 3.12, 3.13
and 3.14 and must pass; no dependency needs a Rust toolchain.
