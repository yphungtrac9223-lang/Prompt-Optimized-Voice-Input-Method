# Prompt-Optimized Voice Input Method

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Windows 10/11](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6.svg)]()

**Free and open-source voice input tool optimized for AI coding — speak naturally, get structured prompts.**

> A lightweight alternative to [Wispr Flow](https://wispr.com/) ($144/yr) and [SuperWhisper](https://superwhisper.com/) (macOS only), built for Windows developers who use Claude Code, Cursor, and other AI coding tools.

<!-- TODO: 录一个在 Claude Code 中使用的 GIF 放这里 -->
<!-- ![Demo](docs/demo.gif) -->

---

## Why This Tool?

Every day, developers type thousands of words to AI assistants. Voice input should be faster — but existing tools don't understand code.

|  | **This Project** | Wispr Flow | SuperWhisper | Handy |
|--|-----------------|------------|--------------|-------|
| Price | **Free** | $144/yr | $60/yr | Free |
| Platform | **Windows** | Mac (Win beta) | Mac only | Cross-platform |
| AI Prompt Mode | **Yes** | No | No | No |
| Chinese ASR | **Optimized** | Basic | Basic | Basic |
| Project Vocab Scan | **Yes** | No | No | No |
| App-aware Mode | **Yes** | Yes | No | No |
| Open Source | **Yes** | No | No | Yes |

---

## Features

### Core
- **Hold-to-talk** — Hold Caps Lock (customizable), speak, release to auto-paste
- **Continuous recording** — Tap to start/pause/resume, double-tap to finish — ideal for long prompts
- **Dual ASR engines** — Alibaba Qwen3-ASR (best for Chinese) / Groq Whisper (free tier)
- **Multi-language** — Chinese, English, Japanese, Korean, Cantonese

### AI Coding Enhancement
- **AI Prompt Mode** — Automatically restructures spoken instructions into clean, structured AI prompts
  - Input: *"嗯那个帮我把用户列表改成分页的每页二十条再加个搜索功能还有排序"*
  - Output: *"请修改用户列表：1) 分页（每页20条）2) 搜索功能 3) 排序功能"*
- **Project Vocabulary Scan** — Imports library names, class names, and function names from your codebase to improve recognition accuracy
- **Preview & Edit** — Review and edit transcription before pasting — no more wrong text sent to AI
- **App-aware Smart Mode** — Automatically switches polish mode based on foreground window:
  - Terminal (Claude Code, cmd) → AI Prompt mode
  - IDE (VS Code, Cursor) → AI Prompt mode
  - Browser (Chrome, Edge) → General polish
  - Other apps → Raw transcription

---

## Quick Start

### 1. Install

```bash
pip install PySide6 PySide6-Fluent-Widgets sounddevice keyboard pyperclip numpy requests groq
```

### 2. Get an API Key (choose one)

| Engine | Link | Cost |
|--------|------|------|
| **Alibaba Qwen3-ASR** (recommended for Chinese) | [bailian.console.aliyun.com](https://bailian.console.aliyun.com/) | ¥0.013/min |
| **Groq Whisper** (free) | [console.groq.com](https://console.groq.com/) | Free (rate limited) |

### 3. Run

```bash
pythonw voice_input_gui.pyw
```

Paste your API key in the settings window, hold **Caps Lock**, speak, and release.

---

## Configuration

First run auto-generates `config.json`. See [`config.example.json`](config.example.json) for all options:

```jsonc
{
  "asr_provider": "aliyun",       // "aliyun" or "groq"
  "hotkey": "caps lock",          // any key or combo like "ctrl+alt+v"
  "recording_mode": "hold",       // "hold" (hold-to-talk) or "toggle" (tap to start/stop)
  "polish_mode": "prompt",        // "off", "polish" (fix errors), "prompt" (restructure)
  "smart_mode": true,             // auto-switch polish mode by foreground app
  "confirm_before_paste": false   // preview before pasting
}
```

---

## How It Works

```
Hold hotkey → Record audio → ASR (cloud) → [AI Polish/Prompt] → Paste to cursor
                                                    ↑
                                          Smart Mode detects
                                          foreground app type
```

The AI Prompt mode passes your transcription through an LLM (Groq LLaMA 3.3 or Alibaba Qwen) with a system prompt that restructures spoken instructions into clean, numbered prompts — without adding anything you didn't say.

---

## FAQ

**Q: Is my audio stored anywhere?**
A: No. Audio is processed in memory only, sent to the ASR API for recognition, then discarded. No logs, no recordings. The code is open source — audit it yourself.

**Q: Does it work on macOS / Linux?**
A: Currently Windows only. The hotkey system and window detection use Windows APIs. PRs for cross-platform support are welcome.

**Q: Can I use it offline?**
A: Not yet. Cloud ASR gives much better accuracy and requires no GPU. Local model support (via faster-whisper) is planned for a future release.

**Q: What if the AI Prompt mode changes my intent?**
A: The system prompt explicitly instructs the LLM to preserve your original intent and not add requirements you didn't mention. You can also enable "Preview before paste" to review and edit before sending.

**Q: Caps Lock keeps toggling when I use it as hotkey?**
A: The app automatically suppresses Caps Lock toggle — your keyboard state won't change.

---

## Tech Stack

| Component | Library |
|-----------|---------|
| UI | PySide6 + [QFluentWidgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) |
| Audio | sounddevice |
| Hotkey | keyboard |
| Clipboard | pyperclip |
| ASR | Alibaba Qwen3-ASR / Groq Whisper |
| AI Polish | Groq LLaMA 3.3 / Alibaba Qwen-Plus |

---

## Contributing

Contributions welcome! Especially:
- Bug reports and feature requests via [Issues](https://github.com/yphungtrac9223-lang/Prompt-Optimized-Voice-Input-Method/issues)
- Cross-platform support (macOS, Linux)
- Local model integration (faster-whisper)
- UI/UX improvements

---

## License

[MIT](LICENSE) — free for personal and commercial use.
