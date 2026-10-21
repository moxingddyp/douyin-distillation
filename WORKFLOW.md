# Workflow and Recovery

[English](WORKFLOW.md) · [简体中文](WORKFLOW.zh-CN.md) · [README](README.md)

## Before Starting

Establish the selected work or local file, topic, authorization scope, execution location, output directory, and existing progress. On recovery, inspect the original process, logs, source hash, and outputs before restarting. A disconnected session does not prove the job has stopped.

Only ask for material missing information. A capability question is not collection authorization. The included capture adapter supports a single selected video, not account-wide inventory.

## From Media to Traceable Knowledge

1. **Identity and source.** Resolve the real work and creator before capture; do not substitute a recommendation page or its first MP4. Import preserves a copy and fully decodes the media. For image posts, verify pages and hashes individually; the CLI does not automate independent page-count verification.
2. **Machine navigation.** ASR and OCR retain source hashes, timestamps, model configurations, and relevant original frames. Out-of-range, mismatched, or corrupted records must not be adopted. OCR locates original visuals; sampled frames are not a claim of frame-by-frame viewing.
3. **Content review.** Read the machine text and comments actually obtained, inspect key visuals, and identify important software, URLs, papers, and dataset identifiers. State comment coverage and gaps; even the last available page does not prove platform-wide completeness. Mark comments as not applicable when appropriate rather than inventing a count.
4. **Source review.** Trace important claims to original papers or official documents/data. Preserve claim → source URL → applicability → scope actually visited and verified. Keep quotations, visible evidence, commenter opinions, external facts, interpretations, and recommendations separate.
5. **Audio review.** Perform independent audio review, or obtain explicit acceptance by the current user of visual/original-source cross-checking with unverified audio-only claims excluded. Record that task's actual approval reference and exclusions in `review.json`. Do not inherit another task's approval or treat model agreement as human audio review.
6. **Per-work note.** Use [the note template](templates/note.md); link conclusions to timestamps/pages and actual sources. Classify promotional content without forcing it into a research method.
7. **Method synthesis.** Use [the method template](templates/methods.md). Organize by question, inputs, prerequisites, steps, outputs, and failure signals. Preserve differences and disagreements. Repeated explanations of one source do not count as independent evidence.
8. **Validate and hand off.** Run `validate` after notes and synthesis. It checks source and frame hashes, time limits, review gates, comment counts, and required documents—not whether a person really read a source or whether the semantic conclusion is correct. Stage transfers and verify SHA256; do not publish a whole processing directory.

## Records and Recovery

Each work retains `manifest.json`, `transcript.json`, `ocr.json`, `comments.json`, `review.json`, `note.md`, `methods.md`, and necessary frames. Distinguish media passed, machine draft, evidence reviewed, and note completed. A process exiting or JSON existing is not completion.

Comments must bind to the current `work_id` and `source_sha256`, including a zero-comment list. Counts describe obtained comments, not all platform comments.

Only one process may write to a work directory. Creation refuses to overwrite; writes use atomic replacement. Reuse requires matching sources and configurations, parseable JSON, valid time bounds, and—for OCR—matching frame hashes. Uncommitted frames from failed OCR are preserved; retry in a new directory rather than overwrite them.

Keep failures, missing material, and disagreements visible; do not remove them from the denominator. Updates handle only requested new or changed works. An unavailable old work does not authorize deleting history.

Account-level indices, full pagination, bulk comments, and independent image-page verification are not included in this CLI.
