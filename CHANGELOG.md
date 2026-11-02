# Changes / 升级说明

## 0.2.0 — 2026-11-02

- Include the existing portable Xiaohongshu single-note component: ordered media, observed comments/interactions, private raw capture and local ASR/OCR integration. Preserve both observed share-count field names without inventing missing counts.
- Add selected Bilibili BV/part capture, original subtitle retrieval and up-to-1080p DASH video/audio selection.
- Require an explicit existing user-owned Chrome profile; remove maintainer-specific host, drive, project and login paths.
- Keep login/CAPTCHA/permission failures visible and omit signed media URLs from reports.
- Preserve existing Douyin and local media commands. No account-wide, comment or danmaku completeness claim is added.
- Replace the installed `distillation-workflow` folder from the Skill ZIP; retain your work directories, local models and private browser profile separately. The full source ZIP is required for root pipeline commands. Optional Playwright capture dependencies are separate from offline processing dependencies.

新增B站单分P、原字幕、音视频分轨下载；须自行准备已有登录profile。升级只替换技能目录，保留个人模型、过程目录和登录资料；完整处理命令需完整源码包。不自动迁移用户数据或启动采集。没有新增全账号、评论或弹幕能力。
