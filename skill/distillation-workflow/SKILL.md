---
name: distillation-workflow
description: Transcribe and distill user-selected Douyin works, Bilibili videos, Xiaohongshu notes or local media through visual/comment review, original-source tracing, scoped capture and recovery. Use for traceable per-work notes and method synthesis, not automatic collection from usage questions.
---

# Distillation and Transcription

[简体中文](SKILL.zh-CN.md)

Locate the repository supplied by the user and read its root `WORKFLOW.md`. Load `INSTALL.md`, `PUBLICATION.md`, and templates as needed. If the package location is unknown, ask for it rather than searching the original maintainer's private workspace. Use actual repository paths for scripts outside this skill.

Establish the selected work/local media, topic, authorization scope, progress, and execution location. A capability or usage question does not authorize collection. On recovery, verify the source hash, directory, original process, and logs before restarting. Stop for login, CAPTCHA, rate limits, or missing permissions; do not change networking or make payments automatically.

For Xiaohongshu, read the repository `platforms/xiaohongshu/README.md` and use `scripts/media.py xiaohongshu`. Default to faithful local content/media and obtainable comments/interactions; deeper method synthesis follows the user request. Missing counts remain unknown; no full-comment claim. The standalone Skill requires the full repository for this platform.

For a Bilibili video, read [the single-part capture branch](references/bilibili.md); it uses the bundled script and your own existing Chrome profile. Resolve short links and confirm the selected part before capture.

For local media, use `pipeline.py ingest`, `asr`, `ocr`, and `read`. Before optional capture, read [capture boundaries](references/capture.md). The external collector's license is not commercial-use permission. The current CLI supports individual videos, not account-wide or image-post completeness claims.

Read the machine text and comments actually obtained; inspect key original frames/pages and trace important claims to original papers or official sources. Separate quotations, visual evidence, commenter opinions, external facts, interpretations, and recommendations. Counts describe obtained comments. Sampled frames do not prove frame-by-frame viewing, and model agreement is not independent audio review.

For requested deep knowledge distillation, complete `review.json` from evidence actually reviewed. Basic Xiaohongshu content export does not require a fabricated deep-review record. Require independent audio review or this task's explicit user acceptance of visual/original-source cross-checking, excluding unverified audio-only claims. Do not inherit another task's approval or fabricate visits, audio review, or completion flags.

Complete per-work notes and method synthesis using root templates, then run `validate` and review semantics. Fixtures are rejected by default; a fixture pass is not a real ASR/OCR result. Keep failures, gaps, disagreements, and source links. Do not remove failures to claim full coverage.

Across works, deduplicate by question, inputs, steps, outputs, prerequisites, and evidence while preserving conflicts. Repeated explanations of one source are not independent studies. Questions about existing knowledge read relevant results without automatically collecting again.
