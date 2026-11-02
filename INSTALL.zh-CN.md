# 安装与模型

[English](INSTALL.md) · [简体中文](INSTALL.zh-CN.md) · [README](README.zh-CN.md)

## Python与依赖

核心检查和合成示例只使用Python 3.10及以上版本的标准库。处理实际音视频时，在自己的虚拟环境中安装`requirements-media.txt`列出的依赖：

```sh
python3 -m venv .venv
# macOS/Linux
.venv/bin/python -m pip install -r requirements-media.txt
# Windows: .venv\Scripts\python.exe
```

记录的版本来自两个实际使用的Windows环境，不是跨平台完整依赖锁。环境由使用者自行准备。可选依赖缺失直接报错，不自动安装。PyAV解码不要求系统`ffmpeg`命令。

## 本地模型

ASR需要已经下载到本地的CTranslate2格式Whisper模型，目录中应包含`model.bin`。按上游faster-whisper说明取得模型并核对模型卡许可。程序使用`local_files_only=True`，不根据在线模型名称下载，不自动切换CPU和GPU。模型目录文件全部计入profile哈希；模型改变不能复用旧稿。

- CPU：`--device cpu --compute-type int8`，单线程。
- NVIDIA GPU：自行准备兼容的CTranslate2、CUDA和cuDNN，再显式选择`--device cuda --compute-type float16`。程序不安装驱动、不停止其他任务。
- 按媒体大小及抽帧间隔预留原件副本、解码、原帧和输出空间。

OCR需要本地检测、方向分类、识别模型及字符字典，即`det`、`cls`、`rec`和`keys`。程序先检查文件和哈希，再初始化模型；缺少资产直接报错，不隐式下载。CLI使用CPU单线程，并在初始化和推理期间阻止socket连接。

模型与字典由使用者自行取得并核许可。若识别ONNX模型内嵌`character`字典，可用`scripts/extract_onnx_dictionary.py --model ... --output ...`导出为私人本地文件；这不授予再分发许可。

## 可选采集

MediaCrawler为外部依赖，不随包分发。使用前读取[适配版本及限制](THIRD_PARTY.zh-CN.md)。

在自己的环境安装采集器，亲自登录Chrome专用资料目录。关闭使用该profile的浏览器后运行：

```sh
/path/to/collector-python scripts/capture_one.py --id NUMERIC_WORK_ID --output /path/to/new-capture --crawler-dir /path/to/MediaCrawler --browser-profile /path/to/private-profile --authorization-reference local-task-approval --accept-external-license
```

接受参数不等于平台授权或第三方书面商业许可。适配器仅处理指定作品detail，不清点账号、不批量获取评论、不启用代理池、stealth或验证码求解。登录失效、验证、限流或身份不符时停止。

采集输出可能含临时媒体URL，应留在私人过程目录。根据`status.json`中的`media_file_relative`选取媒体，再用`pipeline.py ingest`完整解码。采集完成不等于转写、OCR或蒸馏完成。

## 技能安装

将`skill/distillation-workflow`复制到个人Codex技能目录。发布包放在固定位置，首次使用时提供包根目录，让技能找到流程、脚本和模板。复制技能时不夹带工作资料或模型。

## 远程执行与恢复

可以将发布包与必要输入复制到自己的执行机。自行配置SSH别名；包内不预置主机、盘符或认证。保留SSH主机校验。

重连或重试前核对执行机、工作目录、原进程和日志。前台SSH断开不能确定远程任务是否仍在运行。

失败不推进成功检查点。核对源哈希、JSON可解析和时间范围，保留失败产物后换新目录重做。原件改变时创建新版本，不以旧ASR/OCR掩盖变化。

B站采集使用`requirements-capture.txt`与Skill内助手，按[profile及范围要求](skill/distillation-workflow/references/bilibili.zh-CN.md)配置；Chrome单独安装。独立Skill ZIP调用根目录处理工具时仍需本仓库。
