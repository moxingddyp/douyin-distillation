# Douyin Distillation and Transcription Workflow

[English](README.md) · [简体中文](README.zh-CN.md)

Turn selected videos or local media into traceable notes and reusable methods—not just transcripts.

Capture or import → Integrity checks → Speech recognition and frame OCR → Content and source review → Per-work notes → Method synthesis → Delivery checks.

## What's Included

- Local media import, complete decoding, and SHA256 checks.
- Speech recognition using a local faster-whisper model.
- Video frame sampling and text recognition using local RapidOCR models.
- Time-range reading of transcripts and visual evidence.
- Checks linking comments and review records to the correct work and source file.
- A distillation skill for Codex, note templates, and method-synthesis templates.
- An optional MediaCrawler adapter for one selected work.

The current CLI targets individual videos or local media. It does not include account-wide pagination, bulk comment collection, or automatic image-post page-count verification.

Content interpretation, external source verification, and method synthesis still require a model or a human reviewer. The program checks record consistency; it does not automatically establish that a conclusion is correct.

## Verified Environment

Core examples and automated tests require Python 3.10 or later.

Real CPU transcription and OCR were run in existing Windows environments using:

- PyAV 18.1.0.
- faster-whisper 1.2.1.
- CTranslate2 4.8.2.
- RapidOCR 3.9.2.
- ONNX Runtime 1.30.0.
- Pillow 12.3.0.

These versions were recorded from two working environments. They are not a complete cross-platform dependency lock. Users prepare their own Python environment, models, and required runtime libraries.

## Try the Example

Run the synthetic example without installing models:

```sh
python3 scripts/pipeline.py demo --output ./demo-work
python3 scripts/pipeline.py verify-media --work ./demo-work
python3 scripts/pipeline.py read --work ./demo-work --section transcript
python3 scripts/pipeline.py validate --work ./demo-work --allow-fixture
```

The output directory must not already exist.

This example uses a generated tone, colour blocks, and explicitly marked synthetic records. It is not real ASR or OCR output. Validation rejects fixtures by default; `--allow-fixture` explicitly enables demonstration checks.

[examples/real-ocr/](examples/real-ocr/) also contains an original text-card video and actual OCR output.

## Process Your Own Media

After preparing the optional dependencies and local models:

```sh
python3 scripts/pipeline.py ingest --media /path/to/input.mp4 --id work-001 --source-url https://example.org/source --output /path/to/new-work
python3 scripts/pipeline.py asr --work /path/to/new-work --model-dir /path/to/local-whisper-model --device cpu --compute-type int8 --language zh
python3 scripts/pipeline.py ocr --work /path/to/new-work --interval 15 --det /path/to/det.onnx --cls /path/to/cls.onnx --rec /path/to/rec.onnx --keys /path/to/keys.txt
```

The program does not move original files or automatically download models. Existing work directories are not overwritten. Reuse checks verify the source, configuration, and outputs before accepting previous ASR or OCR results.

If models are missing, authentication expires, or a CAPTCHA appears, address that specific requirement rather than repeatedly retrying or bypassing verification.

## From Transcription to Distillation

Transcripts and OCR are reading aids, not verified knowledge.

Review the machine text, inspect key original frames, examine the comments actually obtained, and trace important claims to original papers or official sources. Keep quotations, visible evidence, externally verified facts, interpretations, and recommendations separate.

When synthesizing across works, preserve sources, applicability conditions, and disagreements. Repeated explanations of the same source do not count as independent evidence.

## Tests and Examples

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

All 26 automated tests passed. Real short-sample CPU transcription, OCR, and checkpoint reuse were also verified.

An original three-second text-card video was fully decoded into 30 frames. Three sampled frames all produced “LOCAL DEMO 123”. Short-sample results do not establish accuracy for arbitrary long Chinese videos, noisy audio, or complex screens.

## Capture, Privacy, and Licensing

MediaCrawler is an optional external dependency. The targeted version uses a non-commercial learning license; this project's MIT license does not remove those restrictions.

This repository does not contain browser sessions, cookies, tokens, private captures, original platform videos, raw comments, model weights, or historical knowledge libraries.

Process only material you are entitled to use. Public accessibility alone does not grant redistribution rights.

Original project code is licensed under [MIT](LICENSE).

Author: [moxingddyp](https://github.com/moxingddyp).

## Documentation

- [Setup and models](INSTALL.md)
- [Workflow and recovery](WORKFLOW.md)
- [Components and licensing](THIRD_PARTY.md)
- [Validation scope](VALIDATION.md)
- [Privacy and publication boundaries](PUBLICATION.md)
- [Examples](examples/README.md)
- [Per-work note](templates/note.md) and [method synthesis](templates/methods.md)
