# Contributing

VoxCPM Translator is a research workflow for local AI dubbing. Contributions are welcome when they keep the repository usable without bundling private models, copyrighted media, generated output, or machine-specific paths.

## Good contribution areas

- Documentation fixes for setup, models, and troubleshooting.
- Safer validation around JSON, timestamps, and missing files.
- Backend adapters for local audio generation, as long as model weights stay outside the repository.
- CI checks that do not require GPUs, paid APIs, local media, or model downloads.

## Development setup

```bash
conda create -n voxcpm-translator python=3.10 -y
conda activate voxcpm-translator
pip install -r requirements.txt
```

Create local configuration from the template:

```bash
cp configs/default.yaml configs/local.yaml
```

Do not commit `configs/local.yaml`, `.env`, model files, input videos, generated audio, or generated videos.

## Before opening a pull request

Run the lightweight checks that do not require external models:

```bash
python -m compileall scripts
python scripts/04_verify_translation.py --config configs/local.yaml
```

The verification command requires local ASR and refined JSON files. If your change does not touch pipeline data, explain what you could and could not run in the pull request.

## Legal and content policy

Only test with content you have the right to process. Do not upload copyrighted media, voice samples, model weights, private datasets, secrets, or generated output that cannot be redistributed.
