# 已验证范围

[English](VALIDATION.md) · [简体中文](VALIDATION.zh-CN.md) · [README](README.zh-CN.md)

## 实际完成

| 检查 | 结果 | 范围 |
| --- | --- | --- |
| 标准库测试 | 26/26通过 | 完整WAV解码、哈希、fixture隔离、时间越界、跨来源及同数量跨作品评论、帧篡改、路径逃逸/符号链接、缺听校授权/来源/审阅、缺本地模型初始化前拒绝、OCR中断帧不覆盖 |
| 技能quick_validate | 通过 | frontmatter、名称及未完成脚手架检测，不替代语义判断 |
| 合成示例 | 通过 | 2秒正弦波、32000采样完整解码；ASR/OCR/评论/审阅为显式fixture，默认验收拒绝 |
| 真实ASR，音频不分发 | 通过 | 5.67619秒英文系统语音AIFF、62音频帧完整解码；本地small模型、CPU int8单线程；1段0–5.5秒，与输入句一致 |
| 真实OCR | 通过 | 自画640×240、3秒静音文字视频、30帧完整解码；CPU单线程、本地det/cls/rec/字典、socket阻断；0、1、2秒三帧均为`LOCAL DEMO 123`，分数0.99517/0.99511/0.97972 |
| 检查点复用 | ASR/OCR：reused=true | 来源、模型/配置和产物有效才跳过模型，不根据文件存在盲跳 |
| 运行结束 | 检查时无Python测试任务 | 独立临时进程已结束，未启GPU、WSL和采集器 |

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 scripts/pipeline.py verify-media --work examples/self-made-demo
python3 scripts/pipeline.py validate --work examples/self-made-demo --allow-fixture
python3 scripts/pipeline.py read --work examples/real-ocr --section ocr
```

技能结构以Codex的skill-creator `quick_validate.py skill/distillation-workflow`核对，上游验证器不随包分发。

## 输入与输出

- ASR输入：“This is a local demonstration. We keep the source and verify every result.” 机器稿1段0–5.5秒，与输入一致，未将稿件改写为预期答案。源SHA256：`605ecbc43eb887e0950c71d2d72027f2e56155f60bfe86d79681840368dc5747`。系统语音和完整运行目录留在私人测试资料中，未依据[Apple适用条款](https://www.apple.com/legal/sla/)作可再分发结论。
- `examples/real-ocr/source.mp4`：自画白底黑字，使用系统Arial渲染但不捆绑字体。SHA256：`d1ddefe1359824d609139ea523b0a6ba03f84051250305d4e9fdfbfc56361b03`。保留三个原帧及真实输出。
- 真实样本没有伪造评论、审阅和笔记，不能通过完整知识交付门槛；仅验证媒体、推理和读取，不冒称内容已核。
- fixture只演示结构与门槛，真实任务不能使用`fixture=true`。

## 用自己的录音复现ASR

录一段有权使用的语音，再使用本地模型运行：

```sh
python3 scripts/pipeline.py ingest --media /path/to/your-own-recording.wav --id own-voice --source-url https://example.org/own-recording --output /path/to/new-voice-work
python3 scripts/pipeline.py asr --work /path/to/new-voice-work --model-dir /path/to/local-whisper-model --device cpu --compute-type int8 --language en
python3 scripts/pipeline.py read --work /path/to/new-voice-work --section transcript
```

自行记录实际内容、语种与预期文本，不复制未分发的系统语音二进制。

## 未验证或未包含

- 未做干净机器全套依赖安装；版本来自两个既有Windows环境，未验证macOS推理环境。
- 可选适配器未完成真实抖音采集、登录、限流及验证码测试。参数检查不等于真实平台验收。
- 未实现全账号清点/分页、批量评论和图文独立页数核对。
- 未评估中文长视频、噪声音频或复杂屏幕准确率；短样本不证明泛化质量。
- 语义判断、实际外部来源阅读及方法整合仍需模型或人工。程序验收不授予历史素材发布权。
- 完整传递依赖及模型许可取决于所选运行环境；MIT不表示外部组件可以无限制商用。

环境由使用者自行准备。这些是源码预览明确披露的边界，不宣称通用部署支持。
