# Scoped Capture

[English](capture.md) · [简体中文](capture.zh-CN.md)

Read the repository's `THIRD_PARTY.md` for the fixed MediaCrawler commit and license. It is called externally, not bundled; non-commercial learning restrictions still apply. Users obtain/install it and authenticate a dedicated Chrome profile themselves.

Use the single-work command in `INSTALL.md`. Establish the explicit work ID, authorization reference, new output directory, collector location, and private profile. Do not place credentials in commands. An existing profile does not establish valid authentication.

The adapter stops on expired login or CAPTCHA. Users resolve the requirement and retry in a new directory; do not loop or use solvers.

Only the selected work's detail capture is supported. Do not use creator mode as a purported bounded capture. Verify the actual ID and complete media; the first MP4 on a page is not a substitute. Raw state may contain temporary media URLs and stays in a private processing directory.
