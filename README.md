# Prompt-Optimized Voice Input Method

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Windows 10/11](https://img.shields.io/badge/平台-Windows%2010%2F11-0078D6.svg)]()

**面向 AI 编程的语音输入工具 — 说人话，出 prompt。**

> 免费开源的 [Wispr Flow](https://wispr.com/)（$144/年）和 [SuperWhisper](https://superwhisper.com/)（仅 macOS）替代品，专为使用 Claude Code、Cursor 等 AI 编程工具的 Windows 开发者设计。

<!-- TODO: 录一个在 Claude Code 中使用的 GIF 放这里 -->
<!-- ![演示](docs/demo.gif) -->

---

## 为什么选这个工具？

每天给 AI 敲几千字太累了。语音输入本该更快——但现有工具听不懂代码。

|  | **本项目** | Wispr Flow | SuperWhisper | Handy |
|--|-----------|------------|--------------|-------|
| 价格 | **免费** | $144/年 | $60/年 | 免费 |
| 平台 | **Windows** | Mac 为主 | 仅 Mac | 全平台 |
| AI Prompt 模式 | **有** | 无 | 无 | 无 |
| 中文识别优化 | **有（Qwen3-ASR）** | 一般 | 一般 | 一般 |
| 项目词汇扫描 | **有** | 无 | 无 | 无 |
| 应用感知模式 | **有** | 有 | 无 | 无 |
| 需要 GPU | **不需要** | 不需要 | 需要 | 需要 |
| 开源 | **是** | 否 | 否 | 是 |

---

## 核心功能

### 基础能力
- **按住说话，松开出字** — 默认热键 Caps Lock，可自定义
- **连续录音模式** — 短按开始/暂停/恢复，双击结束，适合口述长 prompt
- **双 ASR 引擎** — 阿里云 Qwen3-ASR（中文最强）/ Groq Whisper（免费）
- **自动粘贴** — 识别后自动粘贴到当前光标位置
- **多语言** — 中文、英文、日语、韩语、粤语

### AI 编程增强

**AI Prompt 模式** — 口语自动整理为结构化 prompt：

> 你说：*"嗯那个帮我把用户列表改成分页的每页二十条再加个搜索功能还有排序"*
>
> 输出：*"请修改用户列表：1) 分页显示（每页20条） 2) 搜索功能 3) 排序功能"*

**项目词汇扫描** — 一键扫描项目目录，自动提取库名、类名、函数名到词汇表，让 ASR 正确识别 `PySide6`、`FastAPI`、`useState` 这些术语。

**预览确认** — 粘贴前可预览、编辑，避免识别错误直接发给 AI。

**应用感知智能模式** — 根据当前窗口自动切换润色策略：

| 当前窗口 | 自动使用 |
|---------|---------|
| 终端（Claude Code、cmd） | AI Prompt 模式 |
| IDE（VS Code、Cursor） | AI Prompt 模式 |
| 浏览器（Chrome、Edge） | 通用润色 |
| 其他应用 | 不润色 |

---

## 快速开始

### 1. 安装依赖

```bash
pip install PySide6 PySide6-Fluent-Widgets sounddevice keyboard pyperclip numpy requests groq
```

### 2. 获取 API Key（二选一）

| 引擎 | 链接 | 费用 | 推荐场景 |
|------|------|------|---------|
| **阿里云 Qwen3-ASR** | [bailian.console.aliyun.com](https://bailian.console.aliyun.com/) | ¥0.013/分钟 | 中文为主，准确率最高 |
| **Groq Whisper** | [console.groq.com](https://console.groq.com/) | 免费（有速率限制） | 零成本体验，英文好 |

### 3. 启动

```bash
pythonw voice_input_gui.pyw
```

在设置窗口粘贴 API Key，按住 **Caps Lock** 说话，松开即出文字。

---

## 配置说明

首次运行自动生成 `config.json`，也可以参考 [`config.example.json`](config.example.json)：

| 配置项 | 可选值 | 说明 |
|--------|-------|------|
| `asr_provider` | `"aliyun"` / `"groq"` | ASR 引擎 |
| `hotkey` | `"caps lock"` / `"ctrl+alt+v"` 等 | 录音热键 |
| `recording_mode` | `"hold"` / `"toggle"` | 按住说话 / 连续录音 |
| `polish_mode` | `"off"` / `"polish"` / `"prompt"` | 不润色 / 通用润色 / AI Prompt |
| `smart_mode` | `true` / `false` | 根据窗口自动切换润色模式 |
| `confirm_before_paste` | `true` / `false` | 粘贴前预览确认 |

---

## 工作原理

```
按住热键 → 录音 → ASR 云端识别 → [AI 润色/Prompt 优化] → 粘贴到光标
                                          ↑
                                   智能模式自动检测
                                   当前窗口类型决定
```

AI Prompt 模式会将你的语音文本发给 LLM（Groq LLaMA 3.3 或阿里云 Qwen），用专门的 system prompt 将口语指令整理为结构化 prompt——不会添加你没说的内容。

---

## 常见问题

**Q: 我的录音会被保存吗？**

不会。音频仅在内存中处理，发送给 ASR API 识别后立即丢弃。不存日志，不存录音。代码完全开源，可自行审计。

**Q: 支持 macOS / Linux 吗？**

目前仅支持 Windows 10/11（热键监听和窗口检测使用了 Windows API）。欢迎提交跨平台 PR。

**Q: 可以离线使用吗？**

暂不支持。云端 ASR 准确率远高于本地模型且无需 GPU。后续计划集成 faster-whisper 作为离线备选。

**Q: AI Prompt 模式会不会改变我的意思？**

不会。system prompt 明确要求 LLM 保留原始意图、不添加用户未提及的需求。同时你可以开启"粘贴前预览确认"来检查和编辑。

**Q: Caps Lock 当热键会不会一直切换大小写？**

不会。程序会自动抑制 Caps Lock 的大小写切换，你的键盘状态不受影响。

---

## 技术栈

| 组件 | 技术 |
|------|------|
| UI | PySide6 + [QFluentWidgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) |
| 录音 | sounddevice |
| 热键 | keyboard |
| 剪贴板 | pyperclip |
| ASR | 阿里云 Qwen3-ASR / Groq Whisper |
| AI 润色 | Groq LLaMA 3.3 / 阿里云 Qwen-Plus |

---

## 参与贡献

欢迎任何形式的贡献：

- 🐛 [提交 Bug](https://github.com/yphungtrac9223-lang/Prompt-Optimized-Voice-Input-Method/issues)
- 💡 功能建议
- 🖥️ macOS / Linux 适配
- 🎙️ 本地模型集成（faster-whisper）

---

## 许可证

[MIT](LICENSE) — 自由使用，包括商业用途。
