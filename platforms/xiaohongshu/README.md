# Xiaohongshu: single-note capture and local processing

[简体中文](README.zh-CN.md)

This component captures **one explicitly authorized note per command** on a Windows PC using installed Google Chrome and Playwright. It exports Agent-readable Markdown/JSON, ordered images and available video, and can run local ASR/OCR. It does not search accounts, collect an author's entire feed, publish content or interact with other users.

## Prerequisites and private directories

Live capture and media download run only on Windows. Offline `export`, `process` and tests can run on other operating systems. Install Python 3.10+, native Google Chrome and the Python `playwright` package in your own environment. This component uses `channel='chrome'`; it does not require downloading another Chromium browser. ASR/OCR dependencies and model assets are described in the repository root README.

Create a **dedicated Chrome user-data directory**, launch native Chrome manually with that directory, log in yourself, then close its windows before collection. Pass that same directory as `--profile`. An example native-Chrome launch is `chrome --user-data-dir="..\private-profiles\xhs"` when Chrome is on PATH; use the installed executable's actual location otherwise. A default profile already used by an open Chrome window is unsuitable.

Use three separate, non-nested directories: browser profile, private raw responses, and delivered output. Keep them outside this repository and outside folders you publish. Windows users must restrict their permissions through Windows file security settings; Unix mode bits are not a substitute for Windows ACLs. The profile contains login state. Raw page responses can contain signed media links and authentication parameters. Neither belongs in Git or a public deliverable.

The native profile is sufficient. `--session-file` optionally imports your own locally stored JSON cookie list (or an object containing a `cookies` list) for Xiaohongshu domains once for that profile. No pre-existing project-specific session file is required. Keep any import file private. Do not send passwords or cookies to an Agent chat.

## Capture one note

Put the user-approved URL in an external private file, for example `../private-xhs/request.json`, instead of a command-line argument or shell history:

```json
{"source_url":"https://www.xiaohongshu.com/explore/REPLACE_WITH_THE_AUTHORIZED_NOTE_ID"}
```

Keep any parameters needed by your own working link in that private file. Then run from the repository root:

```sh
python scripts/media.py xiaohongshu capture --input ../private-xhs/request.json --profile ../private-profiles/xhs --private-dir ../private-xhs/raw --output-root ../work/xhs --authorization-reference user-request
```

`--authorization-reference` records a description of your actual authorization in the private receipt; the argument does not grant authorization itself. The default does not scroll comments. To sample currently available comments, add `--comment-scrolls 1` (maximum 3). `--max-media-bytes` sets a per-file byte ceiling; the default is 1 GiB. A missing comment or interaction count stays unknown, rather than zero. If an image lacks its URL, a video note lacks its main video, or no media sources are available, the command reports `partial` with expected/available/obtained/missing media counts and stops before replacing any previous media manifest; this is not a successful complete capture.

On a CAPTCHA, login failure, unavailable note or unexpected redirect, the command stops. Complete any verification manually in the dedicated native profile, close Chrome and retry. It does not solve or bypass verification. Existing verified local files are reused by note identity, media location hash and content SHA-256. Failed downloads keep partial files for inspection and do not replace a completed manifest. Run only one command against a note/profile/work directory at a time.

## Export an already obtained private response

`export` makes no network request and does not download media:

```sh
python scripts/media.py xiaohongshu export --input ../private-xhs/raw/NOTE_ID-detail.json --output-root ../work/xhs
```

The response shape is `{"note":{"noteId":"...","title":"...","desc":"...","imageList":[],"interactInfo":{}},"comments":{"list":[],"hasMore":true}}`; nested `data` wrappers are accepted. Media previously downloaded by this component is discovered through the same note's `media-manifest.json` and hash-checked. A standalone response without that manifest produces text-only output. The export allowlists fields, canonicalizes the note link and removes authentication/signature URL parameters and authentication key-value fragments while retaining ordinary query parameters; temporary CDN links are omitted. It is not a general-purpose anonymizer of names, prose or media content. Review output before making it public.

Each note directory contains `content.md`, `data.json`, and, after live capture, `media-manifest.json` plus `images/` or `video/`. Image indices retain the source order. H264 is preferred when offered. Previous exported snapshots remain under `snapshots/`. If the same note changes its media mapping, old machine-processing links are invalidated; the prior snapshot and derived files remain available for review. An empty comment refresh never erases previously obtained comments; old comments retain their original observation timestamps. Coverage records distinguish current observations from retained records and **never claim a complete comment archive**.

## Local ASR and OCR

Use model files you already prepared explicitly; processing does not silently fetch missing models. Keep the shared video work directory separate from the note directory:

```sh
python scripts/media.py xiaohongshu process --note-dir ../work/xhs/NOTE_ID --work-dir ../video-work/NOTE_ID --asr --model-dir ../models/local-asr
python scripts/media.py xiaohongshu process --note-dir ../work/xhs/NOTE_ID --work-dir ../video-work/NOTE_ID --ocr --det ../models/ocr/det.onnx --cls ../models/ocr/cls.onnx --rec ../models/ocr/rec.onnx --keys ../models/ocr/keys.txt
```

ASR uses the root pipeline and a complete local faster-whisper model directory. OCR uses explicitly supplied local RapidOCR detection/classification/recognition models and character dictionary. The OCR command processes ordered note images and, if present, video frames (`--interval 15` seconds by default). CUDA ASR can be selected with `--device cuda --compute-type float16` when your environment supports it. Inference outputs are marked `machine_unreviewed`; they are not an independently corrected transcript.

The machine results are linked from `content.md` and stored in `derived/`. Video work preserves root-pipeline source/model profiles. Image OCR checks source/model hashes before reusing a result. If a model or image changes, use a new result version rather than overwriting the previous result. Raw OCR/transcripts can contain private information from the content itself; inspect them before sharing.

## Verification status

```sh
python -m unittest discover -s platforms/xiaohongshu/tests -v
```

Synthetic offline tests cover export redaction, missing counts, comment retention, source identity, media hashes, path/symlink escape, CDN/redirect restrictions, bounded downloads/reuse, missing-media coverage and preservation of the prior manifest on empty refresh, original image order and Windows-only capture guards. This public adapter has **not** been tested with a real login, real note, live Windows browser, ASR model or OCR model. The private predecessor used this native-Chrome approach; that history does not validate this portable adapter. Website state and selectors can change; a failure remains visible for diagnosis.

Share counts accept both observed source fields, `shareCount` and `sharedCount`; JSON keeps the original key and display value, and absent counts remain unknown.
