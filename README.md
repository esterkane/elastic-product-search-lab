# Elastic Repo Inventory

Local Python 3.12 CLI for cloning/updating a fixed set of Elastic repositories
and writing deterministic inventory manifests.

## Usage

```powershell
python tools/repo_inventory.py
```

By default the tool writes:

- `sources/` for cloned repositories
- `artifacts/repo-manifest.json`
- `artifacts/repo-manifest.md`

Useful options:

```powershell
python tools/repo_inventory.py --skip-update
python tools/repo_inventory.py --sources-dir C:\tmp\sources --artifacts-dir C:\tmp\artifacts
```

Run tests:

```powershell
python -m pytest
```

