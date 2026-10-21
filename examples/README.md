# Examples

[English](README.md) · [简体中文](README.zh-CN.md) · [Main README](../README.md)

| Directory | Input | Actual checks | Not established |
| --- | --- | --- | --- |
| self-made-demo | Original two-second tone and 2×2 colour blocks | Full WAV decoding and explicit fixture gates | No real ASR/OCR inference, source visits, or audio review |
| real-ocr | Original silent three-second `LOCAL DEMO 123` text-card video | 30 decoded frames; actual RapidOCR inference on three frames, hashes, and checkpoint reuse | No audio or ASR; not an accuracy benchmark for complex screens |

All inputs are original generated tones/blocks or an original text-card video. No platform media, private user data, model weights, browser state, or font files are included. The actual OCR sample retains its unreviewed machine status and has no fabricated `review.json`. See [verification details and hashes](../VALIDATION.md).

A real 5.67619-second system-speech ASR check was completed, but its audio and full run are not distributed. Redistribution permission for system-generated speech has not been established. Public documentation retains the recognition text, source hash, environment, and commands for reproducing the check using your own recording.

Synthetic fixtures test structure and gates only. Actual media/inference samples do not claim complete knowledge delivery.
