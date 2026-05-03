# Release procedure

## v0.1.0 — manual steps still pending

The local tag `v0.1.0` is created. To finalize the public release, run
the following from `~/PycharmProjects/omnisus-db/`:

```bash
# 1. Create the GitHub repo (one-time)
gh repo create raphaelfh/omnisus-db --public \
    --description "Python library for ingesting Brazilian public health databases into DuckLake" \
    --source . --remote origin

# 2. Push main + tag
git push -u origin main
git push origin v0.1.0

# 3. Create the GitHub Release
gh release create v0.1.0 \
    --title "v0.1.0 — Initial release" \
    --notes-file CHANGELOG.md
```

## PyPI placeholder (per spec §11.6)

GitHub-only distribution for v0.x. To reserve the `omnisus-db` PyPI
namespace with a placeholder before the namespace is squatted:

```bash
# 0. Confirm name is free
curl -sI https://pypi.org/project/omnisus-db/ | head -1
# 404 = free. 200 = abort.

# 1. Build a v0.0.0 stub from a temporary directory
mkdir -p /tmp/omnisus-db-stub && cd /tmp/omnisus-db-stub
cat > pyproject.toml <<EOF
[project]
name = "omnisus-db"
version = "0.0.0"
description = "Reserved placeholder. See https://github.com/raphaelfh/omnisus-db"
requires-python = ">=3.13"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF
mkdir omnisus_db && touch omnisus_db/__init__.py

# 2. Build + publish (requires PyPI token)
uv build
uv publish  # uses ~/.pypirc / UV_PUBLISH_TOKEN env

# 3. Verify
pip index versions omnisus-db
```

## Subsequent releases

For v0.x.y patches:

```bash
# 1. Bump version
sed -i '' "s/version = \".*\"/version = \"0.x.y\"/" pyproject.toml
sed -i '' 's/__version__ = ".*"/__version__ = "0.x.y"/' src/omnisus_db/_version.py

# 2. Update CHANGELOG.md (add new section at top)

# 3. Commit + tag + push
git add CHANGELOG.md pyproject.toml src/omnisus_db/_version.py uv.lock
git commit -m "chore: release v0.x.y"
git tag -a v0.x.y -m "omnisus-db v0.x.y"
git push origin main --tags
gh release create v0.x.y --notes-file CHANGELOG.md
```
