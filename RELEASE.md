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
URL in `README.md` 404s.

> **Do not push tags on the first push.** A local `v0.1.0` tag exists and points
> 45 commits back, at code without the inventory, tolerance or performance work.
> `_version.py` still reads `0.1.0`, so `release.yml`'s tag-vs-version check
> would *pass* and it would publish that old tree as 0.1.0. Push the branch
> alone; cut a fresh tag afterwards.

```bash
cd ~/PycharmProjects/omnisus-db

gh repo create raphaelfh/omnisus-db --public \
    --description "Python library for ingesting Brazilian public health databases into DuckLake" \
    --source . --remote origin

git push -u origin main        # note: no --tags
```

That alone starts `test.yml` and `docs.yml`. Then, before any release:

- **Settings → Pages** → source "GitHub Actions", so `docs.yml` can deploy.
- **Settings → Environments** → create `pypi`.
- **PyPI → Publishing** → add a Trusted Publisher: project `omnisus-db`, owner
  `raphaelfh`, repository `omnisus-db`, workflow `release.yml`, environment
  `pypi`. No token is created; this is the whole point of OIDC.

### Then cut the next version

The `Unreleased` section of `CHANGELOG.md` contains a **breaking** change —
`import_dataset` and the named importers now return `ImportReport` rather than
`list[ImportResult]` — so the next version is `0.2.0`, not `0.1.1`.

Follow "Release procedure" above. Optionally delete the stale local tag first,
so it cannot be pushed by accident:

```bash
git tag -d v0.1.0
```

`README.md` pins its install example to `@v0.1.0`; update it to the new tag
once one exists, or the documented install gives users code without any of
this work.

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
