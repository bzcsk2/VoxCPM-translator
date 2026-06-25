# CI setup

The repository includes lightweight pytest coverage and a `pyproject.toml` pytest configuration. A maintainer can enable GitHub Actions by adding a workflow file under `.github/workflows/` from the GitHub web UI.

Recommended checks:

```bash
python -m compileall scripts
pytest -q
python scripts/run_pipeline.py --config configs/default.yaml --dry-run --from-stage 0 --to-stage 6
```

Recommended workflow file path:

```text
.github/workflows/python-checks.yml
```

Recommended workflow content:

```yaml
name: Python checks

on:
  pull_request:
  push:
    branches:
      - main

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest
      - name: Compile scripts
        run: python -m compileall scripts
      - name: Run tests
        run: pytest -q
      - name: Dry-run pipeline
        run: python scripts/run_pipeline.py --config configs/default.yaml --dry-run --from-stage 0 --to-stage 6
```

This workflow does not require GPU, model weights, paid APIs, or media files. It only validates syntax, helper behavior, and the command orchestration layer.
