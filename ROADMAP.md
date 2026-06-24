# Roadmap

This repository is currently a research release. The code is useful as a local workflow, but several areas should mature before it is treated as a polished end-user tool.

## Near-term

- Add a real implementation or documented adapter contract for `scripts/05_generate_audio_chunks.py`.
- Validate required local files before each stage starts, with clear error messages.
- Add sample ASR and refined JSON fixtures so non-GPU tests can verify timestamp and assembly behavior.
- Add a dry-run command that checks config paths, environment variables, FFmpeg, and optional model directories.
- Document how to create `paths.input_wav` from `paths.input_video`.

## Project quality

- Add unit tests for timestamp parsing, subtitle escaping, JSON alignment, and speed adjustment decisions.
- Add shell checks for `scripts/01_process_vocals.sh`.
- Pin or constrain dependency versions once a known-good environment is tested.
- Separate optional dependency groups for ASR, translation, TTS, subtitles, and LatentSync.

## User experience

- Consider a single orchestrator CLI that runs selected stages in order.
- Add resumable stage output checks so users can restart after failures.
- Improve failure handling for missing chunks, malformed model output, and invalid subtitle text.

## Release readiness

- Add versioned releases when the pipeline has a reproducible setup.
- Add screenshots or short demo clips only if the media can be redistributed.
- Keep model weights, generated media, and source content outside the repository.
