# 第三方组成、来源与许可

[English](THIRD_PARTY.md) · [简体中文](THIRD_PARTY.zh-CN.md) · [README](README.zh-CN.md)

不捆绑第三方源码、模型权重或历史采集资料。外置安装不消除上游限制。

| 组件 | 版本或用途 | 许可与核查范围 |
| --- | --- | --- |
| MediaCrawler | 可选采集，commit `380b426000aac3d612837ed72c99808347dc94c9` | [NON-COMMERCIAL LEARNING LICENSE 1.1](https://github.com/NanmiCoder/MediaCrawler/blob/380b426000aac3d612837ed72c99808347dc94c9/LICENSE)。商业用途需书面同意，大规模采集受限制，不是宽松许可依赖。此发布副本尚未完成真实登录和采集验收。 |
| faster-whisper | 1.2.1，离线ASR | [MIT](https://github.com/SYSTRAN/faster-whisper/blob/v1.2.1/LICENSE)；[运行与模型](https://github.com/SYSTRAN/faster-whisper/tree/v1.2.1)。模型及CTranslate2等依赖遵循各自条款。 |
| RapidOCR | 3.9.2，抽帧OCR | [Apache-2.0](https://github.com/RapidAI/RapidOCR/blob/v3.9.2/LICENSE)；[源码与说明](https://github.com/RapidAI/RapidOCR/tree/v3.9.2)。模型及ONNX Runtime等依赖需单独核查。 |
| PyAV / FFmpeg | 完整媒体解码 | 未捆绑。所选wheel实际链接的FFmpeg构建及再分发条件尚未完整核清，见[上游](https://github.com/PyAV-Org/PyAV)。不能仅凭Python包名认定整条编解码链许可已完成。 |
| Pillow / ONNX Runtime | 图像输出/OCR推理 | 未捆绑。完整逐包和模型许可清单取决于使用者选定环境。 |

`requirements-media.txt`记录两个实际Windows环境中的PyAV 18.1.0、faster-whisper 1.2.1、CTranslate2 4.8.2、RapidOCR 3.9.2、ONNX Runtime 1.30.0、Pillow 12.3.0，不是新环境完整锁文件。见[实际CPU检查](VALIDATION.zh-CN.md)。

## 自有代码

单作品采集适配器调用上游API，不复制MediaCrawler实现。它接受外部路径、私人浏览器profile、明确范围和许可参数；失败以非零状态退出。

处理流水线提供独立输入、延迟导入可选依赖、完整源哈希、配置检查、原子记录和显式fixture隔离。不含历史账号数据、私人知识库或个人授权值。

## 项目许可证

自有代码采用[MIT](LICENSE)，作者署名`moxingddyp`。许可证全文保留标准英文；中文说明帮助理解，不替代正文。

MIT不覆盖MediaCrawler非商业限制，也不覆盖运行库或模型条款。运行库及模型权重不随包分发。未来增加再分发时，需核对应许可与NOTICE义务。
