## Summary

- 

## Validation

- [ ] `python scripts/dev_check.py`
- [ ] Focused subset only:
  - [ ] `python scripts/dev_check.py --check compile`
  - [ ] `python scripts/dev_check.py --check shell`
  - [ ] `python scripts/dev_check.py --check tests`
  - [ ] `python scripts/dev_check.py --check pipeline-dry-run`
- [ ] Diagnostic report generated, if this changes runtime troubleshooting:
  - [ ] `python scripts/diagnose.py --config configs/local.yaml --include-artifacts`
- [ ] Full local pipeline checks, if runtime behavior changed
- [ ] Not run, because:

## Local runtime details, if applicable

- OS:
- Python:
- FFmpeg:
- CUDA / GPU:
- Backend mode:
- Model directories or model IDs:
- Pipeline stages run:

## Checklist

- [ ] No model weights, media files, generated outputs, secrets, or private paths are committed.
- [ ] Documentation is updated for user-facing behavior changes.
- [ ] Model/license implications are documented if this adds or changes an integration.
- [ ] CI and local validation commands remain aligned through `scripts/dev_check.py`.
