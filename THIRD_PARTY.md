# Components, Sources, and Licensing

[English](THIRD_PARTY.md) · [简体中文](THIRD_PARTY.zh-CN.md) · [README](README.md)

No third-party source code, model weights, or historical captures are bundled. External installation does not remove upstream restrictions.

| Component | Version or purpose | License and verification scope |
| --- | --- | --- |
| MediaCrawler | Optional capture, commit `380b426000aac3d612837ed72c99808347dc94c9` | [NON-COMMERCIAL LEARNING LICENSE 1.1](https://github.com/NanmiCoder/MediaCrawler/blob/380b426000aac3d612837ed72c99808347dc94c9/LICENSE). Commercial use requires written permission; large-scale collection is restricted. It is not a permissively licensed dependency. The adapter has not been verified against a live login/capture session in this distribution. |
| faster-whisper | 1.2.1, offline ASR | [MIT](https://github.com/SYSTRAN/faster-whisper/blob/v1.2.1/LICENSE); [runtime and models](https://github.com/SYSTRAN/faster-whisper/tree/v1.2.1). Models and dependencies such as CTranslate2 retain their own terms. |
| RapidOCR | 3.9.2, sampled-frame OCR | [Apache-2.0](https://github.com/RapidAI/RapidOCR/blob/v3.9.2/LICENSE); [source and documentation](https://github.com/RapidAI/RapidOCR/tree/v3.9.2). Models and dependencies such as ONNX Runtime require separate review. |
| PyAV / FFmpeg | Complete media decoding | Not bundled. The actual FFmpeg build linked by a selected wheel and its redistribution conditions have not been fully reviewed. See [PyAV upstream](https://github.com/PyAV-Org/PyAV). A Python package name alone does not establish the full codec chain's licensing. |
| Pillow / ONNX Runtime | Image output / OCR inference | Not bundled. A complete package/model license inventory depends on the user's chosen environment. |

`requirements-media.txt` records PyAV 18.1.0, faster-whisper 1.2.1, CTranslate2 4.8.2, RapidOCR 3.9.2, ONNX Runtime 1.30.0, and Pillow 12.3.0 from two working Windows environments. It is not a complete clean-environment lock. See [actual CPU checks](VALIDATION.md).

## Original Code

The single-work capture adapter calls upstream APIs without copying MediaCrawler's implementation. It accepts external paths, a private browser profile, explicit scope and license parameters, and exits nonzero on failure.

The pipeline provides standalone input handling, deferred optional imports, complete source hashes, configuration checks, atomic records, and explicit fixture isolation. It contains no historical account data, private knowledge library, or personal authorization values.

## Project License

Original code is licensed under [MIT](LICENSE), with attribution to `moxingddyp`. The full license retains its standard English text; Chinese explanations are for convenience and do not replace it.

MIT does not override MediaCrawler's non-commercial restrictions or any runtime/model terms. No runtimes or model weights are distributed. Any future redistribution requires checking the applicable license and NOTICE obligations.
