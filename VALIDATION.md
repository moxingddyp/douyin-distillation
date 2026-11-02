# Verification Scope

[English](VALIDATION.md) · [简体中文](VALIDATION.zh-CN.md) · [README](README.md)

## Completed Checks

| Check | Result | Scope |
| --- | --- | --- |
| Standard-library tests | 26/26 passed | Complete WAV decoding, hashes, fixture isolation, invalid time bounds, cross-source and same-count cross-work comments, frame tampering, path escape/symlinks, missing audio approval/sources/review, refusal before missing-model initialization, and preservation of interrupted OCR frames |
| Skill quick_validate | Passed | Frontmatter, naming, and unfinished scaffold checks; not semantic judgment |
| Synthetic example | Passed | Two-second tone, 32,000 decoded samples; ASR/OCR/comments/review are explicit fixtures rejected by default validation |
| Real ASR, test audio not distributed | Passed | 5.67619-second English system-generated AIFF, 62 decoded audio frames; local small model, CPU int8, one thread; one 0–5.5-second segment matching the input sentence |
| Real OCR | Passed | Original silent 640×240 three-second text video, 30 decoded frames; local CPU det/cls/rec/dictionary, one thread, socket connections blocked; frames at 0, 1, 2 seconds produced `LOCAL DEMO 123` with scores 0.99517/0.99511/0.97972 |
| Checkpoint reuse | ASR/OCR: reused=true | Matching source, model/configuration, and valid outputs skip model execution, not merely file existence |
| Run cleanup | No Python test job at inspection | Independent temporary test processes ended; GPU, WSL, and capture were not started |

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 scripts/pipeline.py verify-media --work examples/self-made-demo
python3 scripts/pipeline.py validate --work examples/self-made-demo --allow-fixture
python3 scripts/pipeline.py read --work examples/real-ocr --section ocr
```

Skill structure was checked with Codex's skill-creator `quick_validate.py skill/distillation-workflow`; that upstream validator is not bundled.

## Inputs and Outputs

- ASR input: “This is a local demonstration. We keep the source and verify every result.” The machine transcript matched it in one 0–5.5-second segment; the transcript was not rewritten to an expected answer. Source SHA256: `605ecbc43eb887e0950c71d2d72027f2e56155f60bfe86d79681840368dc5747`. System-generated audio and the full run remain private; no redistribution conclusion was made under the applicable [Apple terms](https://www.apple.com/legal/sla/).
- `examples/real-ocr/source.mp4`: original white-background black text, rendered with system Arial without bundling font files. SHA256: `d1ddefe1359824d609139ea523b0a6ba03f84051250305d4e9fdfbfc56361b03`. Three original frames and actual outputs are included.
- Actual samples have no fabricated comments, review, or notes, and therefore do not pass a complete knowledge-delivery gate. They verify media, inference, and reading—not completed content review.
- Fixture records demonstrate structure and gates only. `fixture=true` must not be used for real work.

## Reproduce ASR with Your Recording

Record a short clip you are entitled to use, then run with your local model:

```sh
python3 scripts/pipeline.py ingest --media /path/to/your-own-recording.wav --id own-voice --source-url https://example.org/own-recording --output /path/to/new-voice-work
python3 scripts/pipeline.py asr --work /path/to/new-voice-work --model-dir /path/to/local-whisper-model --device cpu --compute-type int8 --language en
python3 scripts/pipeline.py read --work /path/to/new-voice-work --section transcript
```

Record the actual content, language, and expected text yourself. Do not substitute the undistributed system-speech binary.

## Not Verified or Not Included

- No clean-machine full dependency installation; the recorded versions came from two existing Windows environments. A macOS inference environment was not verified.
- No live Douyin collection or login/rate-limit/CAPTCHA test for the optional adapter. Parameter checks are not real-platform acceptance.
- Account-wide inventory/pagination, bulk comments, and independent image-post page-count checks are not implemented.
- No accuracy evaluation on long Chinese videos, noisy audio, or complex screens. Short tests do not establish general accuracy.
- Semantic review, actual external-source reading, and method synthesis still need a model/human. Validation does not grant rights to historical media.
- Complete transitive dependency and model license coverage depends on the selected runtime environment. MIT does not establish unrestricted commercial use of external components.

Users prepare their own environment. These unverified areas are disclosed limits of the source preview, not a claim of universal deployment support.

## 0.2.0 release verification / 本版验证

Root offline suite: 32 checks (26 existing pipeline, 3 Bilibili API-fixture checks, 3 route checks); Xiaohongshu: 19 offline checks. Bilibili fixtures check exact identity, existing-output preservation and omission of signed URLs from reports. No fixture opens a browser or establishes live-platform acceptance. CLI help, Python syntax, Skill structure and package privacy checks are performed for this release. The original one-part Bilibili workflow was previously tested; the public profile-parameterized adapter and Xiaohongshu portable adapter have not been freshly tested against platform login/capture. No new ASR/OCR inference or model installation was run for this release.
