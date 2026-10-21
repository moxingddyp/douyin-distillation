# 抖音蒸馏与转写工作流

[English](README.md) · [简体中文](README.zh-CN.md)

把指定视频或本地媒体整理为可追溯的笔记和方法库，而不只是生成一份转写稿。

采集或导入 → 完整性检查 → 语音转写与画面OCR → 内容和来源核查 → 逐条笔记 → 方法整合 → 交付检查。

## 提供什么

- 本地音视频导入、完整解码和SHA256校验。
- 使用本地faster-whisper模型进行语音转写。
- 使用本地RapidOCR模型进行视频抽帧和文字识别。
- 按时间范围读取机器文本和画面证据。
- 校验评论与作品身份、源文件和审阅记录。
- 用于Codex的蒸馏技能、笔记模板和方法整合模板。
- 可选的单作品MediaCrawler适配入口。

当前命令行工具面向单视频或本地媒体，不包含全账号分页采集、批量评论获取和图文页数自动验收。

内容理解、外部来源查证和方法提炼仍需由模型或人工完成。程序检查记录一致性，不自动证明结论正确。

## 已验证环境

核心示例和自动测试只需要Python 3.10及以上版本。

真实CPU转写和OCR在既有Windows环境中使用以下组件完成：

- PyAV 18.1.0。
- faster-whisper 1.2.1。
- CTranslate2 4.8.2。
- RapidOCR 3.9.2。
- ONNX Runtime 1.30.0。
- Pillow 12.3.0。

这些版本记录来自两个实际使用的环境，不是所有平台通用的完整依赖锁。使用者自行准备Python环境、模型和所需运行库。

## 快速查看示例

不安装模型也可以运行合成示例：

```sh
python3 scripts/pipeline.py demo --output ./demo-work
python3 scripts/pipeline.py verify-media --work ./demo-work
python3 scripts/pipeline.py read --work ./demo-work --section transcript
python3 scripts/pipeline.py validate --work ./demo-work --allow-fixture
```

输出目录需要尚不存在。

该示例使用自制正弦波、色块和明确标记的合成记录，不是真实转写或OCR结果。默认验收会拒绝合成记录，只有显式指定`--allow-fixture`才用于演示检查。

[examples/real-ocr/](examples/real-ocr/)另附自绘文字视频及真实OCR输出。

## 处理自己的媒体

准备可选依赖和本地模型后：

```sh
python3 scripts/pipeline.py ingest --media /path/to/input.mp4 --id work-001 --source-url https://example.org/source --output /path/to/new-work
python3 scripts/pipeline.py asr --work /path/to/new-work --model-dir /path/to/local-whisper-model --device cpu --compute-type int8 --language zh
python3 scripts/pipeline.py ocr --work /path/to/new-work --interval 15 --det /path/to/det.onnx --cls /path/to/cls.onnx --rec /path/to/rec.onnx --keys /path/to/keys.txt
```

程序不移动原件，不自动下载模型。已有任务目录拒绝覆盖；复用转写和OCR结果前，会检查来源、配置和产物。

缺少模型、登录失效或出现验证码时，应处理具体缺项，不反复重试或绕过验证。

## 从转写到蒸馏

机器稿和OCR是阅读导航，不是已经核实的知识。

逐条处理时，需要阅读机器文本、查看关键原帧、核对已取得的评论，并追踪重要主张的原始论文或官方资料。笔记区分原话、画面事实、外部核实、推断和建议。

跨作品整合时保留来源、适用条件和争议，不把同一来源的重复讲述计为多份独立证据。

## 测试与示例

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

已通过26项自动测试，并完成真实短样本CPU转写、OCR和检查点复用验证。

自绘3秒文字视频完整解码30帧，三个抽帧均识别出“LOCAL DEMO 123”。短样本结果不代表任意中文长视频、噪声音频或复杂画面的识别准确率。

## 采集、隐私与许可

MediaCrawler为可选外部依赖。所适配版本采用非商业学习许可证，其限制不会因本项目采用MIT而改变。

本仓库不包含浏览器登录状态、Cookie、令牌、私人采集资料、平台原视频、原评论、模型权重或历史知识库。

只处理你有权使用的资料。仅因内容可以公开访问，不代表可以重新分发。

自有代码采用[MIT许可证](LICENSE)。

作者：[moxingddyp](https://github.com/moxingddyp)。

## 文档入口

- [安装与模型](INSTALL.zh-CN.md)
- [执行与恢复](WORKFLOW.zh-CN.md)
- [组成与许可](THIRD_PARTY.zh-CN.md)
- [已验证范围](VALIDATION.zh-CN.md)
- [隐私与发布边界](PUBLICATION.zh-CN.md)
- [示例说明](examples/README.zh-CN.md)
- [单条笔记](templates/note.md)与[方法整合](templates/methods.md)
