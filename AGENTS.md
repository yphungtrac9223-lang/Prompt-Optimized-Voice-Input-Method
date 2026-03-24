# Repository Guidelines

## Project Structure
单文件桌面应用，入口为 `voice_input_gui.pyw`（约 1300 行）。配置存储在 `config.json`，图标为 `voice_input.ico`。`docs/` 目录存放市场调研和功能方案文档。

## Build & Run

```bash
pip install PySide6 PySide6-Fluent-Widgets sounddevice keyboard pyperclip numpy requests groq
python voice_input_gui.pyw      # 前台运行
pythonw voice_input_gui.pyw     # 无控制台窗口
python -m py_compile voice_input_gui.pyw  # 语法检查
```

## Coding Style
4 空格缩进，`snake_case` 函数/变量，`PascalCase` 类名，模块级常量大写。注释用中文，仅在逻辑不自明时添加。

## Core Features
1. **按住热键说话** — 松开后自动识别并粘贴到光标位置
2. **连续录音模式** — 短按开始/暂停/恢复，双击结束
3. **AI Prompt 模式** — 口语化开发指令自动整理为结构化 prompt
4. **项目词汇自动提取** — 扫描项目目录提取编程术语到词汇表
5. **识别结果预览确认** — 粘贴前可编辑和确认
6. **应用感知智能模式** — 根据前台窗口类型自动切换润色模式

## Testing
无自动化测试。修改后先 `py_compile` 语法检查，再手动冒烟测试：启动 → 设置 → 录音 → 识别 → 粘贴 → 托盘。

## Security
`config.json` 含 API Key，已在 `.gitignore` 中排除。不要提交真实密钥。
