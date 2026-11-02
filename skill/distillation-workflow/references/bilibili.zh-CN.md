# B站：指定单分P采集

[English](bilibili.md)

只处理用户指定链接和明确分P。短链先解析正式BV，按view元数据核标题、作者、aid、分P和CID；多P范围不明时先说明并询问。脚本每次只取一P，不自动清点账号。

执行机须有Python 3.10+、Playwright与已安装Google Chrome。用户先在官方站点交互登录专用Chrome profile，传入已有目录并关闭占用该profile的进程。不导出Cookie、不自动重建登录、不绕过验证码；登录、权限、限流失败停止，不换代理或身份规避。

```sh
python -m pip install -r requirements-capture.txt
python skill/distillation-workflow/scripts/bilibili_capture.py --bvid BV_IDENTIFIER --part 1 --browser-profile /path/to/your-private-profile --output /path/to/new-private-capture
```

BV_IDENTIFIER须替换真实12字符BV号，输出目录必须不存在。脚本确认登录、绑定BV/aid/P/CID，保留字幕JSON，下载音视频DASH分轨；选择不高于1080p的最高可得画质，同分辨率优先AVC。无适用流明确失败。不实现评论、弹幕和账号全量。

报告不保存Cookie或临时音视频/字幕链接，但含来源身份、作者元数据、文件路径和哈希；全部输出按私人过程资料保管。失败仅记异常类型，不输出签名URL。

下载后用PyAV完整解码各轨，检查时长、音轨、实际画质及SHA256。字幕原件保留，按平台标记区分自动字幕；非AI轨不直接当作人工核实。阅读全部文本，重要转折和疑点补看原帧，提供时间导航。字幕缺失或不足时使用明确配置的本地ASR/OCR，不自动下载模型或更换计算设备。

跨设备处理保留执行端原媒体与登录状态，仅回传授权文档、字幕与必要画面并核字节/哈希。完整仓库提供处理工具和审阅模板；独立Skill ZIP只含采集助手，不包含根目录处理pipeline。

验证依据：原始工作流一个指定教程已完成登录采集、1080p/AAC全长解码与自动字幕阅读。本次公开参数化版本完成离线CLI和回归检查，未新采平台样本，未验证多P端到端。
