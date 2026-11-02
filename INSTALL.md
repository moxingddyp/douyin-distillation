# Setup and Models

[English](INSTALL.md) · [简体中文](INSTALL.zh-CN.md) · [README](README.md)

## Python and Dependencies

Core checks and synthetic examples use only the Python 3.10+ standard library. For real media processing, install the dependencies listed in `requirements-media.txt` into your own virtual environment:

```sh
python3 -m venv .venv
# macOS/Linux
.venv/bin/python -m pip install -r requirements-media.txt
# Windows: .venv\Scripts\python.exe
```

The recorded versions come from two working Windows environments, not a complete cross-platform dependency lock. Users prepare their own environment. Missing optional dependencies produce an error; the program does not install them automatically. PyAV decoding does not require a system `ffmpeg` command.

## Local Models

ASR requires a locally available Whisper model in CTranslate2 format, with `model.bin` in its directory. Obtain the model according to upstream faster-whisper instructions and check its model-card license. The program uses `local_files_only=True`, does not download a model from an online name, and does not switch automatically between CPU and GPU. All model-directory files contribute to the profile hash; changing the model invalidates reuse.

- CPU: `--device cpu --compute-type int8`, one thread.
- NVIDIA GPU: configure a compatible CTranslate2, CUDA, and cuDNN combination, then explicitly select `--device cuda --compute-type float16`. The tool does not install drivers or stop other jobs.
- Reserve storage for the source copy, decoding, frames, and results according to your media size and sampling interval.

OCR requires local detection, orientation-classification, and recognition models plus a character dictionary: `det`, `cls`, `rec`, and `keys`. Files and hashes are checked before model initialization. Missing assets produce an error rather than an implicit download. The CLI configures single-threaded CPU execution and blocks socket connections during model initialization and inference.

Users obtain models and the dictionary separately and check their licenses. If a recognition ONNX model contains a `character` dictionary, `scripts/extract_onnx_dictionary.py --model ... --output ...` can export it to a private local file; this does not authorize redistribution.

## Optional Capture

MediaCrawler is an external dependency, not included in this package. Read [its targeted version and restrictions](THIRD_PARTY.md) before use.

Install it in your own environment and authenticate a dedicated Chrome profile yourself. Close browsers using that profile before running:

```sh
/path/to/collector-python scripts/capture_one.py --id NUMERIC_WORK_ID --output /path/to/new-capture --crawler-dir /path/to/MediaCrawler --browser-profile /path/to/private-profile --authorization-reference local-task-approval --accept-external-license
```

Accepting the flag is not platform authorization or third-party written commercial permission. The adapter performs one selected work's detail capture, without account inventory, bulk comments, proxy pools, stealth, or CAPTCHA solving. It stops on expired login, verification, rate limits, or identity mismatch.

Capture output can contain temporary media URLs and belongs in a private processing directory. Select the media using `media_file_relative` in `status.json`, then use `pipeline.py ingest` for complete decoding. Capture alone is not transcription, OCR, or completed distillation.

## Install the Skill

Copy `skill/distillation-workflow` into your personal Codex skills directory. Keep this repository at a stable location and provide its root path on first use so the skill can locate the workflow, scripts, and templates. Do not include work data or models when copying the skill.

## Remote Execution and Recovery

You may copy the package and necessary inputs to your own execution machine. Configure your own SSH aliases; the package contains no host, drive, or authentication settings. Keep SSH host verification enabled.

Before reconnecting or retrying, verify the machine, work directory, running process, and logs. A disconnected foreground SSH session does not establish whether the remote task is still running.

Failures do not advance successful checkpoints. Check source hashes, parseable JSON, and time ranges; preserve failed outputs and retry in a new directory. Changed input requires a new version rather than reuse of stale ASR or OCR.

Bilibili capture uses `requirements-capture.txt` and the bundled Skill helper; follow [its profile and scope requirements](skill/distillation-workflow/references/bilibili.md). Chrome is installed separately. The standalone Skill ZIP needs this repository for root pipeline scripts.
