# Security Policy

## Supported versions

This repository is currently a research release. Security fixes are handled on the `main` branch.

## Reporting a vulnerability

Please open a private security advisory on GitHub or contact the maintainer through GitHub if you find a vulnerability.

Do not include secrets, private model paths, API keys, copyrighted media, or generated voice/video samples in public issues.

## Secrets and local files

The project reads API keys from environment variables and local `.env` files. Keep these files out of Git:

- `.env`
- `configs/local.yaml`
- model weights and checkpoints
- input videos and generated outputs

If a secret is committed accidentally, revoke it immediately before removing it from Git history.
