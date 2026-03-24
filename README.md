# Prompt-Optimized Voice Input Method

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Windows 10/11](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6.svg)]()

**语音转 Prompt，专为 AI 编程设计的 Windows 语音输入工具。**

用 Claude Code 写代码时，想说的需求很复杂，但打字组织 prompt 太慢。这个工具让你按住热键说话，自动把语音整理成结构清晰的 prompt，直接粘贴到编辑器。

<!-- TODO: 录一个演示 GIF 放这里 -->
<!-- ![演示](assets/demo.gif) -->

---

## 功能

**AI Prompt 模式** — 你随口说的需求，自动整理成有结构的 prompt。不用自己组织语言。

> 你说：*"嗯那个帮我把用户列表改成分页的每页二十条再加个搜索"*
>
> 输出：*"请修改用户列表：1) 分页显示（每页20条） 2) 搜索功能"*

**项目词汇扫描** — 自动从你的项目中提取函数名、类名、库名，语音识别时不会把 `FastAPI` 认成"发似特啊屁哎"。

**预览确认** — 识别结果先显示，你确认后才粘贴。不会突然往编辑器里塞一段错误的文字。

**应用感知** — 自动检测当前窗口，在终端里用 Prompt 模式，在浏览器里用通用润色，不用手动切换。

**连续录音** — 短按开始，再按暂停，双击结束。适合描述复杂需求时边想边说。

**双 ASR 引擎** — 阿里云 Qwen3-ASR 和 Groq Whisper 可选，都不需要本地 GPU。

---

## 快速开始

### 1. 安装

```bash
pip install PySide6 PySide6-Fluent-Widgets sounddevice keyboard pyperclip numpy requests groq
```

### 2. 获取 API Key

| 引擎 | 获取链接 | 费用 |
|------|---------|------|
| 阿里云 Qwen3-ASR | [bailian.console.aliyun.com](https://bailian.console.aliyun.com/) | ¥0.013/分钟 |
| Groq Whisper | [console.groq.com](https://console.groq.com/) | 免费（有速率限制） |

### 3. 启动

```bash
pythonw voice_input_gui.pyw
```

在设置窗口粘贴 API Key，按住 **Caps Lock** 说话，松开即可。

---

## 配置

首次运行自动生成 `config.json`，参考 [`config.example.json`](config.example.json)：

| 配置项 | 可选值 | 说明 |
|--------|-------|------|
| `asr_provider` | `"aliyun"` / `"groq"` | ASR 引擎 |
| `hotkey` | `"caps lock"` / `"ctrl+alt+v"` 等 | 录音热键 |
| `recording_mode` | `"hold"` / `"toggle"` | 按住说话 / 连续录音 |
| `polish_mode` | `"off"` / `"polish"` / `"prompt"` | 不润色 / 通用润色 / AI Prompt |
| `smart_mode` | `true` / `false` | 根据窗口自动切换润色模式 |
| `confirm_before_paste` | `true` / `false` | 粘贴前预览确认 |

---

## 背景

市面上的语音输入工具大多面向日常聊天场景，识别结果是口语化的。用 AI 编程时，你需要的是结构化的 prompt，而不是"帮我写一个那个什么函数就是处理用户信息的那个"。这个项目就是为了解决这个问题。

---

## License

[MIT](LICENSE)
