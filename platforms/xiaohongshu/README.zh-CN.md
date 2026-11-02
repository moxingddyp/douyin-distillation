# 小红书：单篇采集与本地处理

[English](README.md)

本组件在 Windows PC 上使用已安装的原生 Google Chrome 和 Playwright，**每条命令采集一篇明确获授权的笔记**，导出 Agent 可读的 Markdown/JSON、原顺序图片及可取得的视频，并可执行本地转写/OCR。不搜索账号、不采集作者全量作品、不发布内容或执行互动。

## 环境与私有目录

真实采集和媒体下载仅在 Windows 执行；离线 `export`、`process` 和测试可在其他系统运行。请在自己的环境准备 Python 3.10+、原生 Google Chrome 和 Python `playwright` 包。组件使用 `channel='chrome'`，无需另下一个 Chromium 浏览器。转写/OCR 依赖和模型准备见根目录 README。

创建一个**专用的 Chrome 用户数据目录**，手动以该目录启动原生 Chrome、亲自登录，然后关闭其窗口，再把同一目录传给 `--profile`。Chrome 已加入 PATH 时，可用 `chrome --user-data-dir="..\private-profiles\xhs"` 手动启动；否则使用实际安装的 Chrome 可执行文件路径。不适合直接使用仍被打开的 Chrome 占用的默认目录。

浏览器用户数据、私有原始响应、交付输出使用三个独立且互不嵌套的目录，放在仓库及公开目录之外。Windows 用户应通过文件安全设置限制目录权限；Unix 权限位不能代替 Windows ACL。用户数据目录含登录状态，原始响应可能含带签名媒体链接和认证参数，均不能进入 Git 或公开交付包。

原生登录目录本身即可使用。`--session-file` 可选地导入你自行保存在本机的 JSON Cookie 列表，或带 `cookies` 列表的对象，仅接受小红书域名，每个用户数据目录导入一次。不要求任何旧项目专用的会话文件。导入文件也要私密保存，不把密码或 Cookie 发到 Agent 聊天中。

## 采集单篇笔记

将用户批准的链接放在仓库外的私有文件，例如 `../private-xhs/request.json`，避免把完整签名链接放进命令参数或终端历史：

```json
{"source_url":"https://www.xiaohongshu.com/explore/REPLACE_WITH_THE_AUTHORIZED_NOTE_ID"}
```

你自己的有效链接若需要参数，将参数留在此私有文件中。在仓库根目录执行：

```sh
python scripts/media.py xiaohongshu capture --input ../private-xhs/request.json --profile ../private-profiles/xhs --private-dir ../private-xhs/raw --output-root ../work/xhs --authorization-reference user-request
```

`--authorization-reference` 在私有回执中记录真实授权的说明，此参数本身不授予权限。默认不滚动评论；需要尝试采集当前可见评论时，加 `--comment-scrolls 1`，最多为 3。`--max-media-bytes` 限制每个文件的下载字节数，默认 1 GiB。未取得的评论或互动计数保持未知，不补零。图片缺 URL、视频笔记缺主视频或没有媒体源时，命令返回 `partial`，列明预期、可用链接、实际取得和缺失媒体数，停止处理且不替换旧媒体清单，不能视为完整采集成功。

遇验证码、登录失败、笔记不可用或异常跳转时停止。在专用原生浏览器中亲自完成验证并关闭 Chrome 后再试，不解决或绕过验证。现有本地文件按笔记身份、媒体位置哈希和内容 SHA-256 核实复用。下载失败保留部分文件供检查，不替换已完成的媒体清单。同一笔记、用户数据目录和工作目录同时只运行一个命令。

## 导出已取得的私有响应

`export` 不联网，也不下载媒体：

```sh
python scripts/media.py xiaohongshu export --input ../private-xhs/raw/NOTE_ID-detail.json --output-root ../work/xhs
```

输入结构为 `{"note":{"noteId":"...","title":"...","desc":"...","imageList":[],"interactInfo":{}},"comments":{"list":[],"hasMore":true}}`，也接受外层嵌套的 `data`。通过同一笔记的 `media-manifest.json` 发现已由本组件下载的媒体，并核验哈希；单独导入响应而没有媒体清单时，只导出文本。导出仅保留指定字段，将笔记链接规范化，去除 URL 中的认证/签名参数及认证键值片段，保留普通查询参数，省略临时 CDN 链接。它不是姓名、正文或媒体内容的通用匿名化工具，公开前仍应审阅实际内容。

每篇输出包含 `content.md`、`data.json`；真实采集后还包含 `media-manifest.json` 及 `images/` 或 `video/`。图片编号保留原顺序；提供 H264 时优先选用。旧导出快照留在 `snapshots/`。同一笔记的媒体映射发生变化时，旧机器处理结果不再作为当前结果链接；旧快照和衍生文件仍可供审阅。新一轮没有读到评论时，不删除旧评论；旧评论保留原观察时间。覆盖记录区分本轮取得和历史保留，**不声明评论已全量归档**。

## 本地转写和 OCR

显式传入已准备好的本地模型，不隐式下载缺失模型。共享视频工作目录与笔记目录分开：

```sh
python scripts/media.py xiaohongshu process --note-dir ../work/xhs/NOTE_ID --work-dir ../video-work/NOTE_ID --asr --model-dir ../models/local-asr
python scripts/media.py xiaohongshu process --note-dir ../work/xhs/NOTE_ID --work-dir ../video-work/NOTE_ID --ocr --det ../models/ocr/det.onnx --cls ../models/ocr/cls.onnx --rec ../models/ocr/rec.onnx --keys ../models/ocr/keys.txt
```

转写复用根目录流程，使用完整的本地 faster-whisper 模型目录。OCR 显式指定本地 RapidOCR 检测、方向分类、识别模型及字符字典。OCR 命令处理原顺序图片；如有视频，也处理视频抽帧，默认 `--interval 15` 秒。环境支持时可用 `--device cuda --compute-type float16` 运行 CUDA 转写。输出标记为 `machine_unreviewed`，不是独立听校后的转写稿。

机器结果存入 `derived/`，在 `content.md` 中提供链接。视频工作目录保留根流程的源文件和模型档案；图片 OCR 复用前核对源文件与模型哈希。模型或图片改变时，应建立新的结果版本，避免覆盖旧结果。原始 OCR/转写可能包含内容本身的私人信息，分享前需检查。

## 验证范围

```sh
python -m unittest discover -s platforms/xiaohongshu/tests -v
```

合成数据离线测试覆盖导出脱敏、未知计数、评论保留、来源身份、媒体哈希、路径/符号链接越界、CDN/跳转限制、下载限额与复用、媒体缺失覆盖及空刷新保留旧媒体清单、原图片顺序及仅 Windows 采集限制。本公开适配器**尚未使用真实登录、真实笔记、Windows 浏览器、转写模型或 OCR 模型验证**。私有前身使用过此原生 Chrome 方案，这段历史不等于本可移植适配器已通过验证。网站状态与选择器可能变化，失败会保留为可诊断的错误。

分享数兼容源字段 `shareCount` 和 `sharedCount`，JSON保留实际键与原始显示值；缺失仍为未知。
