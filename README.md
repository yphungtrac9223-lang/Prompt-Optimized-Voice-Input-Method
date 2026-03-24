# 语音输入法

面向 AI 编程的语音输入工具 — 说人话，出 prompt。

基于云端 ASR 的轻量级 Windows 语音输入工具。按住热键说话，松开即出文字，自动粘贴到当前光标位置。专为程序员与 AI 编程场景设计。

## 功能

### 基础能力
- **按住说话，松开出字** — 默认热键 Caps Lock，可自定义
- **连续录音模式** — 短按开始/暂停/恢复，双击结束，适合口述复杂 prompt
- **双 ASR 引擎** — 阿里云 Qwen3-ASR（推荐）/ Groq Whisper，无需本地 GPU
- **自动粘贴** — 识别结果自动粘贴到当前焦点窗口
- **多语言** — 中文、英文、日语、韩语、粤语
- **系统托盘常驻** — 关闭窗口最小化到托盘

### AI 编程增强
- **AI Prompt 模式** — 口语化开发指令自动整理为结构化 AI prompt
- **通用润色** — 自动修正识别错误、优化标点、去除口语冗余词
- **项目词汇自动提取** — 扫描项目目录，自动提取库名/类名/函数名到词汇表，提升术语识别率
- **识别结果预览** — 粘贴前可预览、编辑、确认，避免误发
- **应用感知智能模式** — 根据当前窗口自动切换润色模式（终端→Prompt 模式，浏览器→通用润色）

## ASR 引擎对比

| 引擎 | 中文准确率 | 价格 | 特点 |
|---|---|---|---|
| **阿里云 Qwen3-ASR-Flash** | ~97% | ¥0.013/分钟 | 中文最强，支持 ITN |
| **Groq Whisper Large v3** | ~90% | 免费（有速率限制） | 速度极快，英文好，支持自定义词汇表 |

## 快速开始

```bash
# 安装依赖
pip install PySide6 PySide6-Fluent-Widgets sounddevice keyboard pyperclip numpy requests groq

# 启动
pythonw voice_input_gui.pyw
```

1. 在设置界面选择 ASR 引擎并填入对应 API Key
2. 按住热键（默认 Caps Lock）说话，松开后自动识别并粘贴

### API Key 获取

- **阿里云**：[百炼平台](https://bailian.console.aliyun.com/) 注册后获取
- **Groq**：[GroqCloud](https://console.groq.com/) 注册后获取免费 Key

## 技术栈

- **UI**：PySide6 + QFluentWidgets（Fluent Design）
- **录音**：sounddevice
- **热键**：keyboard
- **剪贴板**：pyperclip
- **AI 润色**：Groq LLaMA / 阿里云 Qwen
