"""
VoPrompt - PySide6 Fluent 版本
基于阿里云 Qwen3-ASR / Groq Whisper API 的轻量级语音输入工具
架构：PySide6 + Fluent Widgets 原生窗口，系统托盘常驻
"""

import base64
import ctypes
import io
import json
import os
import re
import sys
import time
import wave
import threading
from pathlib import Path

import numpy as np
import requests
import sounddevice as sd
import keyboard
import pyperclip
from groq import Groq

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSystemTrayIcon, QMenu, QSizePolicy, QFileDialog,
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QPropertyAnimation, QPoint
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont, QFontMetrics

from qfluentwidgets import (
    FluentIcon as FIF,
    setTheme, Theme, setThemeColor,
    CardWidget, BodyLabel, SubtitleLabel, CaptionLabel,
    LineEdit, PasswordLineEdit, ComboBox, Slider, SwitchButton,
    PrimaryPushButton, TextEdit, PushButton,
)

# Windows 高 DPI 支持（必须在 QApplication 创建前设置）
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

# ─── 配置 ─────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULT_CONFIG = {
    "asr_provider": "aliyun",
    "api_key": "",
    "aliyun_key": "",
    "custom_vocab": "Claude Code, Python, Groq, Whisper, NiceGUI, API",
    "hotkey": "caps lock",
    "language": "zh",
    "sample_rate": 16000,
    "auto_paste": True,
    "confirm_before_paste": False,
    "mic_gain": 15,
    "polish_mode": "off",
    "recording_mode": "hold",
    "smart_mode": False,
    "smart_mode_rules": {
        "terminal": "prompt",
        "ide": "prompt",
        "browser": "polish",
        "default": "off",
    },
}

ASR_PROVIDERS = {"aliyun": "阿里云 Qwen3-ASR（推荐）", "groq": "Groq Whisper"}
LANG_OPTIONS = {"zh": "中文", "en": "English", "ja": "日本語", "ko": "한국어", "yue": "粤语"}

_POLISH_PROMPTS = {
    "polish": (
        "你是一个文本润色助手。用户会给你一段语音识别的原始文本，"
        "请你：1）修正明显的识别错误；2）优化标点符号；"
        "3）去除口语中的冗余词（如'嗯''那个'等）。"
        "只输出润色后的文本，不要解释，不要添加额外内容。"
        "如果原文已经很好，直接原样返回。"
    ),
    "prompt": (
        "你是一个 AI 编程 prompt 优化助手。用户会给你一段口语化的开发指令（通常是程序员口述的），"
        "请你将其整理为结构化、清晰的 AI prompt，要求：\n"
        "1）保留原始意图，不要添加用户没说的需求\n"
        "2）如果包含多个子任务，用编号列表组织\n"
        "3）修正语音识别中明显的术语错误（如 'react' 可能被识别为 '瑞爱科特'）\n"
        "4）去除口语填充词（嗯、那个、就是说）\n"
        "5）保持简洁，不要加套话（如'请帮我'开头不需要改动）\n"
        "只输出优化后的 prompt，不要解释。"
    ),
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            saved = json.load(f)
        # 旧版 ai_polish 布尔字段迁移为 polish_mode
        if "ai_polish" in saved:
            if saved["ai_polish"] and "polish_mode" not in saved:
                saved["polish_mode"] = "polish"
            del saved["ai_polish"]
        return {**DEFAULT_CONFIG, **saved}
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)




def detect_foreground_app() -> str:
    """检测当前前台窗口类型"""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()

        # 优先通过进程名判断
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if handle:
            buf = ctypes.create_unicode_buffer(260)
            size = ctypes.c_ulong(260)
            ctypes.windll.kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
            ctypes.windll.kernel32.CloseHandle(handle)
            exe = buf.value.lower().rsplit("\\", 1)[-1].rsplit("/", 1)[-1]

            terminal_exes = {
                "cmd.exe", "powershell.exe", "pwsh.exe", "windowsterminal.exe",
                "mintty.exe", "bash.exe", "wt.exe", "warp.exe",
                "alacritty.exe", "hyper.exe",
            }
            ide_exes = {
                "code.exe", "cursor.exe", "pycharm64.exe", "pycharm.exe",
                "idea64.exe", "webstorm64.exe", "sublime_text.exe",
                "devenv.exe",
            }
            browser_exes = {
                "chrome.exe", "firefox.exe", "msedge.exe", "brave.exe",
                "opera.exe", "vivaldi.exe", "arc.exe",
            }

            if exe in terminal_exes:
                return "terminal"
            if exe in ide_exes:
                return "ide"
            if exe in browser_exes:
                return "browser"

        # 进程名未匹配，回退到标题关键字
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.lower()

        terminal_keywords = ["windows terminal", "command prompt", "git bash"]
        ide_keywords = ["visual studio code", "- cursor", "pycharm", "intellij"]
        browser_keywords = ["- google chrome", "- firefox", "- edge", "- brave"]

        for kw in terminal_keywords:
            if kw in title:
                return "terminal"
        for kw in ide_keywords:
            if kw in title:
                return "ide"
        for kw in browser_keywords:
            if kw in title:
                return "browser"
        return "default"
    except Exception:
        return "default"


def extract_vocab_from_project(project_dir: str) -> list[str]:
    """扫描项目目录，提取编程术语"""
    vocab = set()
    project = Path(project_dir)

    SKIP_DIRS = {"node_modules", ".venv", "venv", ".git", "__pycache__", "dist", "build", ".tox", ".mypy_cache", ".pytest_cache", "env", ".env"}

    def _iter_files(root: Path, pattern: str):
        """递归查找文件，跳过不需要的目录"""
        for item in root.iterdir():
            if item.is_dir():
                if item.name not in SKIP_DIRS:
                    yield from _iter_files(item, pattern)
            elif item.match(pattern):
                yield item

    # requirements.txt
    req = project / "requirements.txt"
    if req.exists():
        for line in req.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                name = re.split(r"[>=<!\[\]]", line)[0].strip()
                if name:
                    vocab.add(name)

    # package.json
    pkg = project / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            for key in ("dependencies", "devDependencies"):
                if key in data:
                    vocab.update(data[key].keys())
        except Exception:
            pass

    # pyproject.toml
    pyproj = project / "pyproject.toml"
    if pyproj.exists():
        try:
            text = pyproj.read_text(encoding="utf-8")
            for m in re.finditer(r'"([A-Za-z][\w.-]*)(?:[>=<].*?)?"', text):
                vocab.add(m.group(1))
        except Exception:
            pass

    # Python import 语句
    for ext in ("*.py", "*.pyw"):
        for f in _iter_files(project, ext):
            try:
                c = f.read_text(encoding="utf-8", errors="ignore")
                for m in re.finditer(r"(?:from|import)\s+([\w.]+)", c):
                    parts = m.group(1).split(".")
                    vocab.update(parts)
            except Exception:
                continue

    # JavaScript/TypeScript import 语句
    for ext in ("*.js", "*.ts", "*.jsx", "*.tsx"):
        for f in _iter_files(project, ext):
            try:
                c = f.read_text(encoding="utf-8", errors="ignore")
                for m in re.finditer(r"""(?:from|require\()\s*['"]([^'"]+)['"]""", c):
                    pkg_name = m.group(1)
                    if not pkg_name.startswith("."):
                        name = pkg_name.split("/")[0]
                        if name.startswith("@"):
                            name = pkg_name.split("/")[0] + "/" + pkg_name.split("/")[1] if len(pkg_name.split("/")) > 1 else name
                        vocab.add(name)
            except Exception:
                continue

    # 过滤太短的和 Python 内置模块
    builtins_skip = {
        "os", "sys", "re", "io", "json", "time", "math",
        "copy", "typing", "abc", "ast", "csv", "http",
        "xml", "html", "ssl", "url", "log",
    }
    return sorted(
        v for v in vocab
        if len(v) > 2 and v not in builtins_skip and not v.startswith("_")
    )

# ─── 跨线程信号桥 ────────────────────────────────────

class SignalBridge(QObject):
    status_changed = Signal(str, str)    # text, color
    result_changed = Signal(str)         # text
    overlay_show = Signal(str)           # state
    overlay_hide = Signal(int)           # delay_ms
    preview_show = Signal(str)           # 显示预览窗


# ─── 录音器 ───────────────────────────────────────────

class AudioRecorder:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.recording = False
        self.frames: list[np.ndarray] = []
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            self.frames = []
            self.recording = True
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            callback=self._callback,
        )
        self.stream.start()

    def _callback(self, indata, frames, time_info, status):
        with self._lock:
            if self.recording:
                self.frames.append(indata.copy())

    def pause(self) -> None:
        with self._lock:
            self.recording = False

    def resume(self) -> None:
        with self._lock:
            self.recording = True

    def stop(self, gain: float = 1.0) -> bytes:
        with self._lock:
            self.recording = False
            frames_copy = list(self.frames)
            self.frames = []
        if not hasattr(self, "stream"):
            return b""
        self.stream.stop()
        self.stream.close()
        if not frames_copy:
            return b""
        audio_data = np.concatenate(frames_copy, axis=0)
        if gain > 1.0:
            amplified = audio_data.astype(np.float32) * gain
            amplified = np.clip(amplified, -32768, 32767)
            audio_data = amplified.astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())
        return buf.getvalue()


# ─── 状态浮窗 ─────────────────────────────────────────

class OverlayBubble(QWidget):
    """录音/识别时屏幕底部弹出的圆角状态气泡"""

    _STATES = {
        "recording": ("#EF4444", "white", "●  录音中"),
        "recognizing": ("#F59E0B", "white", "⏳  识别中"),
        "polishing": ("#3B82F6", "white", "✨  AI 润色中"),
        "prompting": ("#8B5CF6", "white", "🤖  Prompt 优化中"),
        "done": ("#22C55E", "white", "✅  已粘贴"),
        "error": ("#EF4444", "white", "✖  识别失败"),
        "paused": ("#6B7280", "white", "⏸  已暂停，再按继续"),
    }
    _BOTTOM_MARGIN = 80

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._label = QLabel("", self)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        self._label.setStyleSheet(
            "color: white; padding: 8px 24px; border-radius: 18px; background: #333;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def show_state(self, state: str) -> None:
        bg, fg, text = self._STATES.get(state, ("#333", "white", state))
        self._label.setText(text)
        self._label.setStyleSheet(
            f"color: {fg}; padding: 8px 24px; border-radius: 18px; background: {bg};"
        )
        self._hide_timer.stop()
        self.adjustSize()
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - self.height() - self._BOTTOM_MARGIN
        self.move(x, y)
        self.show()
        self.raise_()

    def hide_delayed(self, delay_ms: int = 0) -> None:
        if delay_ms > 0:
            self._hide_timer.start(delay_ms)
        else:
            self.hide()


# ─── 预览弹窗 ─────────────────────────────────────────

class PreviewPopup(QWidget):
    """识别结果预览弹窗，确认后再粘贴"""
    confirmed = Signal(str)
    cancelled = Signal()

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(500)

        container = CardWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        layout.addWidget(CaptionLabel("识别结果预览（可编辑）"))

        self._text_edit = TextEdit(self)
        self._text_edit.setFixedHeight(80)
        self._text_edit.setPlaceholderText("识别结果...")
        layout.addWidget(self._text_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._confirm_btn = PrimaryPushButton("粘贴 (Enter)", self)
        self._cancel_btn = PushButton("取消 (Esc)", self)
        btn_row.addWidget(self._confirm_btn)
        btn_row.addWidget(self._cancel_btn)
        layout.addLayout(btn_row)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

        self._confirm_btn.clicked.connect(self._on_confirm)
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._text_edit.installEventFilter(self)

    def show_text(self, text: str):
        self._text_edit.setPlainText(text)
        self.adjustSize()
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - self.height() - 120
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        self._text_edit.setFocus()

    def eventFilter(self, obj, event):
        if obj is self._text_edit and event.type() == event.Type.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
                self._on_confirm()
                return True
            elif event.key() == Qt.Key_Escape:
                self._on_cancel()
                return True
        return super().eventFilter(obj, event)

    def _on_confirm(self):
        text = self._text_edit.toPlainText().strip()
        self.hide()
        if text:
            # 先 hide 再 emit，确保焦点回到目标窗口后再粘贴
            QTimer.singleShot(100, lambda: self.confirmed.emit(text))

    def _on_cancel(self):
        self.hide()
        self.cancelled.emit()


# ─── 设置窗口 ─────────────────────────────────────────

class SettingsWindow(QWidget):
    _vocab_scanned = Signal(list)

    def __init__(self, config: dict, on_save):
        super().__init__()
        self.config = config
        self._on_save = on_save
        self._vocab_scanned.connect(self._on_vocab_scanned)
        self.setWindowTitle("VoPrompt")
        self.setFixedWidth(460)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)
        self._build_ui()
        self._load_from_config()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        # 标题
        title = SubtitleLabel("VoPrompt")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        # 状态卡片
        self._status_card = CardWidget(self)
        status_layout = QHBoxLayout(self._status_card)
        status_layout.setContentsMargins(16, 12, 16, 12)
        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet("color: #9CA3AF; font-size: 18px;")
        self._status_label = BodyLabel("就绪")
        self._status_label.setStyleSheet("color: #16A34A;")
        status_layout.addWidget(self._status_dot)
        status_layout.addWidget(self._status_label, 1)
        root.addWidget(self._status_card)

        # 识别结果
        result_card = CardWidget(self)
        result_layout = QVBoxLayout(result_card)
        result_layout.setContentsMargins(16, 12, 16, 12)
        result_layout.addWidget(CaptionLabel("识别结果"))
        self._result_area = TextEdit(self)
        self._result_area.setReadOnly(True)
        self._result_area.setFixedHeight(80)
        self._result_area.setPlaceholderText("按住热键说话，识别结果显示在这里...")
        result_layout.addWidget(self._result_area)
        root.addWidget(result_card)

        # 设置卡片
        settings_card = CardWidget(self)
        s = QVBoxLayout(settings_card)
        s.setContentsMargins(16, 12, 16, 16)
        s.setSpacing(10)
        s.addWidget(CaptionLabel("设置"))

        # 识别服务
        s.addWidget(BodyLabel("识别服务"))
        self._provider_combo = ComboBox(self)
        for key, label in ASR_PROVIDERS.items():
            self._provider_combo.addItem(label, userData=key)
        self._provider_combo.currentIndexChanged.connect(self._on_provider_change)
        s.addWidget(self._provider_combo)

        # 阿里云 API Key
        self._aliyun_key_label = BodyLabel("阿里云百炼 API Key")
        s.addWidget(self._aliyun_key_label)
        self._aliyun_key_input = PasswordLineEdit(self)
        self._aliyun_key_input.setPlaceholderText("sk-...")
        s.addWidget(self._aliyun_key_input)

        # Groq API Key
        self._groq_key_label = BodyLabel("Groq API Key")
        s.addWidget(self._groq_key_label)
        self._groq_key_input = PasswordLineEdit(self)
        self._groq_key_input.setPlaceholderText("gsk_...")
        s.addWidget(self._groq_key_input)

        # 自定义词汇表
        s.addWidget(BodyLabel("自定义词汇表（逗号分隔）"))
        self._vocab_input = LineEdit(self)
        self._vocab_input.setPlaceholderText("Claude Code, Python, ...")
        s.addWidget(self._vocab_input)

        self._import_vocab_btn = PushButton("从项目导入词汇", self)
        self._import_vocab_btn.clicked.connect(self._import_vocab)
        s.addWidget(self._import_vocab_btn)


        # 快捷键 + 录音模式 + 语言
        row1 = QHBoxLayout()
        col_hotkey = QVBoxLayout()
        col_hotkey.addWidget(BodyLabel("快捷键"))
        self._hotkey_input = LineEdit(self)
        col_hotkey.addWidget(self._hotkey_input)
        row1.addLayout(col_hotkey)

        col_rec_mode = QVBoxLayout()
        col_rec_mode.addWidget(BodyLabel("录音模式"))
        self._rec_mode_combo = ComboBox(self)
        self._rec_mode_combo.addItem("按住说话", userData="hold")
        self._rec_mode_combo.addItem("连续录音", userData="toggle")
        col_rec_mode.addWidget(self._rec_mode_combo)
        row1.addLayout(col_rec_mode)

        col_lang = QVBoxLayout()
        col_lang.addWidget(BodyLabel("识别语言"))
        self._lang_combo = ComboBox(self)
        for key, label in LANG_OPTIONS.items():
            self._lang_combo.addItem(label, userData=key)
        col_lang.addWidget(self._lang_combo)
        row1.addLayout(col_lang)
        s.addLayout(row1)

        # 麦克风增益
        gain_row = QHBoxLayout()
        gain_row.addWidget(BodyLabel("麦克风增益"))
        self._gain_slider = Slider(Qt.Horizontal, self)
        self._gain_slider.setRange(1, 30)
        self._gain_slider.setFixedWidth(200)
        gain_row.addWidget(self._gain_slider)
        self._gain_label = BodyLabel("15x")
        self._gain_label.setFixedWidth(40)
        self._gain_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        gain_row.addWidget(self._gain_label)
        self._gain_slider.valueChanged.connect(
            lambda v: self._gain_label.setText(f"{v}x")
        )
        s.addLayout(gain_row)

        # 开关
        paste_row = QHBoxLayout()
        paste_row.addWidget(BodyLabel("识别后自动粘贴"))
        paste_row.addStretch()
        self._auto_paste_switch = SwitchButton(self)
        self._auto_paste_switch.checkedChanged.connect(self._on_auto_paste_change)
        paste_row.addWidget(self._auto_paste_switch)
        s.addLayout(paste_row)

        confirm_row = QHBoxLayout()
        confirm_row.addWidget(BodyLabel("粘贴前预览确认"))
        confirm_row.addStretch()
        self._confirm_switch = SwitchButton(self)
        confirm_row.addWidget(self._confirm_switch)
        s.addLayout(confirm_row)

        s.addWidget(BodyLabel("润色模式"))
        self._polish_combo = ComboBox(self)
        self._polish_combo.addItem("不润色", userData="off")
        self._polish_combo.addItem("通用润色（纠错、优化标点）", userData="polish")
        self._polish_combo.addItem("AI Prompt 模式（口语→结构化指令）", userData="prompt")
        s.addWidget(self._polish_combo)

        # 智能模式
        smart_row = QHBoxLayout()
        smart_row.addWidget(BodyLabel("智能模式（根据窗口自动切换）"))
        smart_row.addStretch()
        self._smart_switch = SwitchButton(self)
        self._smart_switch.checkedChanged.connect(self._on_smart_mode_change)
        smart_row.addWidget(self._smart_switch)
        s.addLayout(smart_row)

        # 智能模式规则
        self._smart_rules_widget = QWidget(self)
        rules_layout = QVBoxLayout(self._smart_rules_widget)
        rules_layout.setContentsMargins(0, 0, 0, 0)
        rules_layout.setSpacing(6)

        _mode_options = [("off", "不润色"), ("polish", "通用润色"), ("prompt", "AI Prompt")]

        self._rule_combos = {}
        for rule_key, rule_label in [
            ("terminal", "终端/命令行"),
            ("ide", "IDE/编辑器"),
            ("browser", "浏览器"),
            ("default", "其他应用"),
        ]:
            row = QHBoxLayout()
            row.addWidget(CaptionLabel(f"  {rule_label}"))
            row.addStretch()
            combo = ComboBox(self)
            combo.setFixedWidth(140)
            for mode_key, mode_label in _mode_options:
                combo.addItem(mode_label, userData=mode_key)
            row.addWidget(combo)
            rules_layout.addLayout(row)
            self._rule_combos[rule_key] = combo

        s.addWidget(self._smart_rules_widget)

        # 保存按钮
        self._save_btn = PrimaryPushButton(FIF.SAVE, "保存设置", self)
        self._save_btn.clicked.connect(self._save)
        s.addWidget(self._save_btn)

        root.addWidget(settings_card)

        hint = CaptionLabel("关闭窗口后程序在系统托盘继续运行")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #9CA3AF;")
        root.addWidget(hint)

    def _load_from_config(self):
        # 识别服务
        provider = self.config.get("asr_provider", "aliyun")
        for i in range(self._provider_combo.count()):
            if self._provider_combo.itemData(i) == provider:
                self._provider_combo.setCurrentIndex(i)
                break

        self._aliyun_key_input.setText(self.config.get("aliyun_key", ""))
        self._groq_key_input.setText(self.config.get("api_key", ""))
        self._vocab_input.setText(self.config.get("custom_vocab", ""))
        self._hotkey_input.setText(self.config.get("hotkey", "caps lock"))

        lang = self.config.get("language", "zh")
        for i in range(self._lang_combo.count()):
            if self._lang_combo.itemData(i) == lang:
                self._lang_combo.setCurrentIndex(i)
                break

        rec_mode = self.config.get("recording_mode", "hold")
        for i in range(self._rec_mode_combo.count()):
            if self._rec_mode_combo.itemData(i) == rec_mode:
                self._rec_mode_combo.setCurrentIndex(i)
                break

        self._gain_slider.setValue(self.config.get("mic_gain", 15))
        self._gain_label.setText(f"{self.config.get('mic_gain', 15)}x")
        self._auto_paste_switch.setChecked(self.config.get("auto_paste", True))
        self._confirm_switch.setChecked(self.config.get("confirm_before_paste", False))
        self._confirm_switch.setVisible(self.config.get("auto_paste", True))
        polish_mode = self.config.get("polish_mode", "off")
        for i in range(self._polish_combo.count()):
            if self._polish_combo.itemData(i) == polish_mode:
                self._polish_combo.setCurrentIndex(i)
                break
        self._smart_switch.setChecked(self.config.get("smart_mode", False))
        self._smart_rules_widget.setVisible(self.config.get("smart_mode", False))
        self._polish_combo.setEnabled(not self.config.get("smart_mode", False))
        rules = self.config.get("smart_mode_rules", {})
        for rule_key, combo in self._rule_combos.items():
            mode = rules.get(rule_key, "off")
            for i in range(combo.count()):
                if combo.itemData(i) == mode:
                    combo.setCurrentIndex(i)
                    break
        self._on_provider_change()


    def _import_vocab(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择项目目录")
        if not dir_path:
            return
        self._import_vocab_btn.setEnabled(False)
        self._import_vocab_btn.setText("扫描中...")

        def _scan():
            new_terms = extract_vocab_from_project(dir_path)
            self._vocab_scanned.emit(new_terms)

        threading.Thread(target=_scan, daemon=True).start()

    def _on_vocab_scanned(self, new_terms: list[str]):
        self._import_vocab_btn.setEnabled(True)
        self._import_vocab_btn.setText("从项目导入词汇")
        if not new_terms:
            return
        existing = [
            v.strip() for v in self._vocab_input.text().split(",") if v.strip()
        ]
        merged = sorted(set(existing + new_terms), key=str.lower)
        self._vocab_input.setText(", ".join(merged))

    def _on_auto_paste_change(self, checked):
        self._confirm_switch.setVisible(checked)

    def _on_smart_mode_change(self, checked):
        self._smart_rules_widget.setVisible(checked)
        self._polish_combo.setEnabled(not checked)

    def _on_provider_change(self):
        is_aliyun = self._provider_combo.currentData() == "aliyun"
        self._aliyun_key_label.setVisible(is_aliyun)
        self._aliyun_key_input.setVisible(is_aliyun)
        self._groq_key_label.setVisible(not is_aliyun)
        self._groq_key_input.setVisible(not is_aliyun)

    def _save(self):
        self._on_save()

    def sync_to_config(self):
        self.config["asr_provider"] = self._provider_combo.currentData()
        self.config["aliyun_key"] = self._aliyun_key_input.text().strip()
        self.config["api_key"] = self._groq_key_input.text().strip()
        self.config["custom_vocab"] = self._vocab_input.text().strip()
        self.config["hotkey"] = self._hotkey_input.text().strip()
        self.config["language"] = self._lang_combo.currentData()
        self.config["mic_gain"] = self._gain_slider.value()
        self.config["auto_paste"] = self._auto_paste_switch.isChecked()
        self.config["confirm_before_paste"] = self._confirm_switch.isChecked()
        self.config["recording_mode"] = self._rec_mode_combo.currentData()
        self.config["polish_mode"] = self._polish_combo.currentData()
        self.config["smart_mode"] = self._smart_switch.isChecked()
        self.config["smart_mode_rules"] = {
            key: combo.currentData()
            for key, combo in self._rule_combos.items()
        }

    def update_status(self, text: str, color: str):
        color_map = {
            "green": "#16A34A", "red": "#EF4444", "amber": "#F59E0B",
            "blue": "#3B82F6", "gray": "#9CA3AF",
        }
        hex_color = color_map.get(color, color)
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {hex_color};")
        dot_color = hex_color if color != "gray" else "#9CA3AF"
        self._status_dot.setStyleSheet(f"color: {dot_color}; font-size: 18px;")

    def update_result(self, text: str):
        self._result_area.setPlainText(text)

    def closeEvent(self, event):
        self.hide()
        event.ignore()


# ─── 主应用 ───────────────────────────────────────────

class VoiceInputApp:
    def __init__(self, qt_app: QApplication):
        self.qt_app = qt_app
        self.config = load_config()
        self.recorder = AudioRecorder(self.config["sample_rate"])
        self.is_recording = False
        self.hotkey_registered = False
        self._suppressing = False
        self._lock = threading.Lock()
        self._toggle_state = "idle"
        self._last_press_time = 0.0

        # 信号桥
        self.signals = SignalBridge()
        self.signals.status_changed.connect(self._on_status_changed)
        self.signals.result_changed.connect(self._on_result_changed)
        self.signals.overlay_show.connect(self._on_overlay_show)
        self.signals.overlay_hide.connect(self._on_overlay_hide)

        # UI 组件
        self.overlay = OverlayBubble()
        self.preview = PreviewPopup()
        self.signals.preview_show.connect(self._on_preview_show)
        self.preview.confirmed.connect(self._on_preview_confirmed)
        self.preview.cancelled.connect(self._on_preview_cancelled)
        self.window = SettingsWindow(self.config, self._save_settings)
        self._setup_tray()

    # ─── 信号槽 ──────────────────────────────────────

    def _on_status_changed(self, text: str, color: str):
        self.window.update_status(text, color)

    def _on_result_changed(self, text: str):
        self.window.update_result(text)

    def _on_overlay_show(self, state: str):
        self.overlay.show_state(state)

    def _on_overlay_hide(self, delay_ms: int):
        self.overlay.hide_delayed(delay_ms)

    def _on_preview_show(self, text: str):
        self.preview.show_text(text)

    def _on_preview_confirmed(self, text: str):
        self._paste_text(text)
        self.signals.status_changed.emit("识别完成", "green")
        self.signals.overlay_show.emit("done")
        self.signals.overlay_hide.emit(1500)
        QTimer.singleShot(
            2000,
            lambda: self.signals.status_changed.emit(
                f"就绪 — 按住 {self.config['hotkey']} 开始说话", "green"
            ),
        )

    def _on_preview_cancelled(self):
        self.signals.status_changed.emit(
            f"就绪 — 按住 {self.config['hotkey']} 开始说话", "green"
        )
        self.signals.overlay_hide.emit(0)

    def _restore_ready_status(self):
        """延时恢复就绪状态"""
        self.signals.status_changed.emit("识别完成", "green")
        self.signals.overlay_show.emit("done")
        self.signals.overlay_hide.emit(1500)
        time.sleep(2.0)
        self.signals.status_changed.emit(
            f"就绪 — 按住 {self.config['hotkey']} 开始说话", "green"
        )

    # ─── 系统托盘 ────────────────────────────────────

    def _create_tray_icon(self) -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("#4CAF50"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("white"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(8, 8, 48, 48)
        painter.setBrush(QColor("#4CAF50"))
        painter.drawRect(24, 16, 16, 24)
        painter.drawEllipse(26, 42, 12, 6)
        painter.end()
        return QIcon(pixmap)

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self._create_tray_icon(), self.qt_app)
        self.tray.setToolTip("VoPrompt")

        menu = QMenu()
        show_action = QAction("打开设置", menu)
        show_action.triggered.connect(self._show_window)
        menu.addAction(show_action)
        menu.addSeparator()
        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self._show_window()

    def _show_window(self):
        self.window.setVisible(True)
        if self.window.isMinimized():
            self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    # ─── 设置 ────────────────────────────────────────

    def _save_settings(self):
        old_hotkey = self.config["hotkey"]
        self.window.sync_to_config()
        save_config(self.config)
        if old_hotkey != self.config["hotkey"]:
            self._register_hotkey()
        self.signals.status_changed.emit("设置已保存", "blue")
        QTimer.singleShot(
            2000,
            lambda: self.signals.status_changed.emit(
                f"就绪 — 按住 {self.config['hotkey']} 开始说话", "green"
            ),
        )

    # ─── 热键 ────────────────────────────────────────

    def _register_hotkey(self) -> None:
        if self.hotkey_registered:
            keyboard.unhook_all()
            self.hotkey_registered = False

        hotkey = self.config["hotkey"]
        try:
            keyboard.on_press_key(
                hotkey.split("+")[-1],
                self._on_hotkey_press,
                suppress=False,
            )
            keyboard.on_release_key(
                hotkey.split("+")[-1],
                self._on_hotkey_release,
                suppress=False,
            )
            self.hotkey_registered = True
        except Exception as e:
            self.signals.status_changed.emit(f"热键注册失败: {e}", "red")

    def _check_modifiers(self) -> bool:
        parts = self.config["hotkey"].split("+")
        if len(parts) == 1:
            return True
        for mod in parts[:-1]:
            if not keyboard.is_pressed(mod):
                return False
        return True

    def _ensure_caps_lock_off(self) -> None:
        if ctypes.windll.user32.GetKeyState(0x14) & 1:
            self._suppressing = True
            keyboard.send("caps lock")
            time.sleep(0.05)
            self._suppressing = False

    def _on_hotkey_press(self, event) -> None:
        if self._suppressing:
            return
        if not self._check_modifiers():
            return

        if self.config.get("recording_mode", "hold") == "toggle":
            self._on_toggle_press()
            return

        # 原有 hold 模式逻辑
        provider = self.config.get("asr_provider", "aliyun")
        if provider == "aliyun":
            key = self.config.get("aliyun_key", "")
        else:
            key = self.config.get("api_key", "")
        if not key:
            self.signals.status_changed.emit("请先设置 API Key", "red")
            return

        with self._lock:
            if self.is_recording:
                return
            self.is_recording = True
            try:
                self.recorder.start()
            except Exception as e:
                self.is_recording = False
                self.signals.status_changed.emit(f"录音失败: {e}", "red")
                self.signals.overlay_hide.emit(0)
                return

        self.signals.status_changed.emit("录音中...", "red")
        self.signals.overlay_show.emit("recording")
        self._ensure_caps_lock_off()

    def _on_hotkey_release(self, event) -> None:
        if self._suppressing:
            return
        if self.config.get("recording_mode", "hold") == "toggle":
            return

        with self._lock:
            if not self.is_recording:
                return
            self.is_recording = False

        self.signals.status_changed.emit("识别中...", "amber")
        self.signals.overlay_show.emit("recognizing")
        threading.Thread(target=self._process_audio, daemon=True).start()

    def _on_toggle_press(self) -> None:
        with self._lock:
            now = time.time()
            if now - self._last_press_time < 0.3 and self._toggle_state in ("recording", "paused"):
                self._last_press_time = 0.0
                self._toggle_state = "processing"
                self.signals.status_changed.emit("识别中...", "amber")
                self.signals.overlay_show.emit("recognizing")
                self._ensure_caps_lock_off()
                threading.Thread(target=self._process_audio, daemon=True).start()
                return
            self._last_press_time = now
            current_state = self._toggle_state

        if current_state == "processing":
            return

        threading.Timer(0.35, self._handle_single_toggle, args=[now]).start()

    def _handle_single_toggle(self, press_time: float) -> None:
        with self._lock:
            if self._last_press_time != press_time:
                return
            state = self._toggle_state

        if state == "idle":
            provider = self.config.get("asr_provider", "aliyun")
            key = self.config.get("aliyun_key", "") if provider == "aliyun" else self.config.get("api_key", "")
            if not key:
                self.signals.status_changed.emit("请先设置 API Key", "red")
                return
            with self._lock:
                if self._toggle_state != "idle":
                    return
                self._toggle_state = "recording"
            self.signals.status_changed.emit("录音中... (再按暂停，双击结束)", "red")
            self.signals.overlay_show.emit("recording")
            try:
                self.recorder.start()
                self._ensure_caps_lock_off()
            except Exception as e:
                with self._lock:
                    self._toggle_state = "idle"
                self.signals.status_changed.emit(f"录音失败: {e}", "red")
                self.signals.overlay_hide.emit(0)
        elif state == "recording":
            with self._lock:
                self._toggle_state = "paused"
            self.recorder.pause()
            self.signals.status_changed.emit("已暂停 (再按继续，双击结束)", "gray")
            self.signals.overlay_show.emit("paused")
            self._ensure_caps_lock_off()
        elif state == "paused":
            with self._lock:
                self._toggle_state = "recording"
            self.recorder.resume()
            self.signals.status_changed.emit("录音中... (再按暂停，双击结束)", "red")
            self.signals.overlay_show.emit("recording")
            self._ensure_caps_lock_off()

    # ─── 识别 ────────────────────────────────────────

    @staticmethod
    def _check_audio_level(wav_data: bytes) -> float:
        buf = io.BytesIO(wav_data)
        with wave.open(buf, "rb") as wf:
            raw = wf.readframes(wf.getnframes())
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
        if len(samples) == 0:
            return 0.0
        return float(np.sqrt(np.mean(samples ** 2)))

    def _process_audio(self) -> None:
        try:
            gain = self.config.get("mic_gain", 15)
            wav_data = self.recorder.stop(gain=gain)
            if not wav_data:
                self.signals.status_changed.emit("未录到声音", "amber")
                self.signals.overlay_hide.emit(0)
                return

            rms = self._check_audio_level(wav_data)
            if rms < 50:
                self.signals.status_changed.emit("未检测到语音，请检查麦克风", "amber")
                self.signals.overlay_hide.emit(0)
                return

            provider = self.config.get("asr_provider", "aliyun")
            if provider == "aliyun":
                text = self._call_aliyun_api(wav_data)
            else:
                text = self._call_groq_api(wav_data)

            if self.config.get("smart_mode", False):
                app_type = detect_foreground_app()
                rules = self.config.get("smart_mode_rules", {})
                polish_mode = rules.get(app_type, rules.get("default", "off"))
            else:
                polish_mode = self.config.get("polish_mode", "off")
            if text and polish_mode != "off":
                if polish_mode == "prompt":
                    self.signals.status_changed.emit("Prompt 优化中...", "blue")
                    self.signals.overlay_show.emit("prompting")
                else:
                    self.signals.status_changed.emit("AI 润色中...", "blue")
                    self.signals.overlay_show.emit("polishing")
                text = self._polish_text(text, mode=polish_mode)

            if text:
                self.signals.result_changed.emit(text)
                if self.config.get("confirm_before_paste", False) and self.config["auto_paste"]:
                    self.signals.preview_show.emit(text)
                else:
                    if self.config["auto_paste"]:
                        self._paste_text(text)
                    self._restore_ready_status()
            else:
                self.signals.status_changed.emit("未识别到内容", "amber")
                self.signals.overlay_hide.emit(0)

        except Exception as e:
            err_msg = str(e)
            self.signals.status_changed.emit(f"错误: {err_msg[:50]}", "red")
            self.signals.result_changed.emit(f"错误详情:\n{err_msg}")
            self.signals.overlay_show.emit("error")
            self.signals.overlay_hide.emit(2000)
        finally:
            with self._lock:
                if self._toggle_state == "processing":
                    self._toggle_state = "idle"

    def _paste_text(self, text: str) -> None:
        old_clipboard = ""
        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            pass

        pyperclip.copy(text)
        keyboard.send("ctrl+v")
        time.sleep(0.15)

        try:
            pyperclip.copy(old_clipboard)
        except Exception:
            pass

    # ─── API 调用 ────────────────────────────────────

    def _build_whisper_prompt(self) -> str:
        vocab = self.config.get("custom_vocab", "").strip()
        base = "以下是普通话语音，请添加标点符号。"
        if vocab:
            return f"{base}包含以下术语：{vocab}。"
        return base

    def _call_aliyun_api(self, wav_data: bytes) -> str:
        audio_b64 = base64.b64encode(wav_data).decode()
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": f"data:audio/wav;base64,{audio_b64}",
                            "format": "wav",
                        },
                    },
                ],
            },
        ]
        response = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config['aliyun_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": "qwen3-asr-flash",
                "messages": messages,
                "asr_options": {"enable_itn": True},
            },
            timeout=30,
        )
        data = response.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"].strip()
        error = data.get("error", {})
        raise RuntimeError(error.get("message", str(data)))

    def _call_groq_api(self, wav_data: bytes) -> str:
        client = Groq(api_key=self.config["api_key"])
        audio_file = io.BytesIO(wav_data)
        audio_file.name = "recording.wav"

        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            language=self.config["language"],
            response_format="verbose_json",
            temperature=0.0,
            prompt=self._build_whisper_prompt(),
        )

        if hasattr(transcription, "segments") and transcription.segments:
            valid_parts = []
            for seg in transcription.segments:
                prob = seg.get("no_speech_prob", 0) if isinstance(seg, dict) else getattr(seg, "no_speech_prob", 0)
                text = seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")
                if prob < 0.7:
                    valid_parts.append(text)
            return "".join(valid_parts).strip()

        result = transcription.text if hasattr(transcription, "text") else str(transcription)
        return result.strip()

    def _polish_text(self, text: str, mode: str = "polish") -> str:
        system_prompt = _POLISH_PROMPTS.get(mode, _POLISH_PROMPTS["polish"])
        try:
            groq_key = self.config.get("api_key", "")
            aliyun_key = self.config.get("aliyun_key", "")
            if groq_key:
                client = Groq(api_key=groq_key)
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text},
                    ],
                    temperature=0.3,
                    max_tokens=2048,
                )
                polished = response.choices[0].message.content.strip()
                return polished if polished else text
            elif aliyun_key:
                response = requests.post(
                    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {aliyun_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "qwen-plus",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 2048,
                    },
                    timeout=30,
                )
                data = response.json()
                if "choices" in data:
                    polished = data["choices"][0]["message"]["content"].strip()
                    return polished if polished else text
                return text
            else:
                return text
        except Exception:
            return text

    # ─── 生命周期 ────────────────────────────────────

    def _quit(self):
        self.window.sync_to_config()
        save_config(self.config)
        keyboard.unhook_all()
        self.tray.hide()
        self.qt_app.quit()

    def start(self):
        self._register_hotkey()
        self.signals.status_changed.emit(
            f"就绪 — 按住 {self.config['hotkey']} 开始说话", "green"
        )

        self._show_window()


# ─── 启动 ─────────────────────────────────────────────

if __name__ == "__main__":
    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)

    setTheme(Theme.AUTO)
    setThemeColor("#4CAF50")

    voice_app = VoiceInputApp(qt_app)
    voice_app.start()

    sys.exit(qt_app.exec())
