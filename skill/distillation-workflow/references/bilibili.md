# Bilibili: selected single-part capture

[简体中文](bilibili.zh-CN.md)

Process only the supplied BV identifier and explicitly selected part. Resolve short links to the canonical video URL first. Read video metadata to confirm title, author, aid, part number and CID; when a multi-part scope is ambiguous, clarify it before starting. The helper captures one part per invocation.

Use an execution machine with Python 3.10+, Playwright and installed Google Chrome. Authenticate a dedicated Chrome profile interactively on the official site first; pass its existing directory and close any process using it. Never export cookies, solve verification or recreate a profile automatically. Stop for login, permission, CAPTCHA or rate-limit failures. Do not change proxies or identity to retry.

```sh
python -m pip install -r requirements-capture.txt
python skill/distillation-workflow/scripts/bilibili_capture.py --bvid BV_IDENTIFIER --part 1 --browser-profile /path/to/your-private-profile --output /path/to/new-private-capture
```

Replace BV_IDENTIFIER with the actual 12-character BV identifier. The output must not exist. The script confirms authenticated nav status, binds BV/aid/part/CID, saves subtitle originals and downloads separate video/audio DASH tracks. It selects the highest available resolution up to 1080p, preferring AVC at equal resolution. Missing suitable streams fail visibly. It does not implement comments, danmaku or account-wide inventory.

Capture reports omit cookies and temporary media/subtitle URLs, but include source identity, author metadata, file paths and hashes. Treat all outputs as private work data. Runtime API response failures are recorded by error type without signed URL details.

Downloading is not integrity acceptance. Fully decode each track with PyAV, check durations, audio, actual resolution and SHA256 before use. Preserve original subtitle JSON; classify AI subtitles from platform metadata, and do not assume non-AI tracks were independently human verified. Read all text, inspect frames around important transitions and uncertain claims, and retain timestamp navigation. When subtitles are absent or inadequate, use explicitly configured local ASR/OCR; do not silently download models or switch devices.

For a separate execution machine, retain original media and browser state there and transfer only authorized notes/subtitles/necessary frames. Verify transferred sizes and SHA256. The full repository provides local-media processing and review templates; the standalone skill ZIP includes this capture helper but not the root processing pipeline.

Validation basis: the source workflow completed authenticated capture, full 1080p video/AAC decoding and automatic-subtitle reading for one selected single-part tutorial. This public profile-parameterized adaptation has offline CLI and regression checks; no fresh public-adapter platform capture or multi-part end-to-end test was run for this release.
