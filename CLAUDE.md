# 语音输入法 - 项目说明

## 环境要求

- Python 3.10+
- Windows 10/11

## 依赖安装

```bash
pip install PySide6 PySide6-Fluent-Widgets sounddevice keyboard pyperclip numpy requests groq
```

## 启动方式

```bash
pythonw voice_input_gui.pyw
```

或直接双击 `voice_input_gui.pyw` 文件。

## 配置

首次运行会自动生成 `config.json`。需要在设置界面填入 API Key：

- 阿里云 Qwen3-ASR：到 https://bailian.console.aliyun.com/ 获取 API Key
- Groq Whisper：到 https://console.groq.com/ 获取免费 API Key

## 语法检查

```bash
python -m py_compile voice_input_gui.pyw
```
