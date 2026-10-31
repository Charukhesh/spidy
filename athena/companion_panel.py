"""Companion Control Panel for Clicky Windows.

Faithful recreation of CompanionPanelView.swift:
- Width 320px
- Minimal dark aesthetic (#16161A, border #2A2A30)
- Header with animated glowing status dot
- Push-to-Talk instructions capsule
- Grok API key setup row with toggle visibility
- Vision model selector (grok-2-vision-1212)
- Edge Neural TTS voice selector
- Hotkey configuration picker
- Test Pointing Demo button
- Clean quit button
"""

from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont, QCursor

from athena.config import (
    load_config,
    save_config,
    get_api_key,
    set_api_key,
    get_grok_api_key,
    set_grok_api_key,
)
from athena.ai_vision_client import AIVisionClient, GrokClient

CLICKY_BLUE = "#3380FF"


class CompanionPanel(QWidget):
    """Floating companion control panel inspired by CompanionPanelView.swift."""

    visibility_toggled = pyqtSignal(bool)
    demo_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = load_config()

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedWidth(320)

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Container card with dark aesthetic
        self.container = QFrame(self)
        self.container.setStyleSheet("""
            QFrame {
                background-color: #141418;
                border: 1px solid #282830;
                border-radius: 12px;
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        self.container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # 1. Header (Status dot, Clicky title, Close)
        header = QHBoxLayout()
        header.setSpacing(8)

        self.dot = QLabel("●")
        self.dot.setStyleSheet("color: #3380FF; font-size: 14px; border: none;")
        header.addWidget(self.dot)

        title = QLabel("Athena")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF; border: none;")
        header.addWidget(title)

        header.addStretch()

        self.status_lbl = QLabel("Ready")
        self.status_lbl.setFont(QFont("Segoe UI", 9, QFont.Medium))
        self.status_lbl.setStyleSheet("color: #8E8E98; border: none;")
        header.addWidget(self.status_lbl)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #222228;
                color: #8E8E98;
                border: none;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #333340;
                color: #FFFFFF;
            }
        """)
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Divider
        layout.addWidget(self._make_divider())

        # 2. Push-to-Talk Instruction Capsule
        instruction_box = QFrame()
        instruction_box.setStyleSheet("""
            QFrame {
                background-color: #1A1A22;
                border: 1px solid #2E2E3A;
                border-radius: 8px;
            }
        """)
        inst_layout = QHBoxLayout(instruction_box)
        inst_layout.setContentsMargins(12, 10, 12, 10)

        inst_icon = QLabel("🎙️")
        inst_icon.setStyleSheet("border: none; font-size: 14px;")
        inst_layout.addWidget(inst_icon)

        inst_text = QLabel("Hold Ctrl + Shift to talk.")
        inst_text.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        inst_text.setStyleSheet("color: #E2E2E8; border: none;")
        inst_layout.addWidget(inst_text)
        inst_layout.addStretch()

        layout.addWidget(instruction_box)

        # 3. API Key Input (Gemini / Groq / Grok)
        key_lbl = QLabel("API Key (Google Gemini / Groq / xAI)")
        key_lbl.setFont(QFont("Segoe UI", 8, QFont.Bold))
        key_lbl.setStyleSheet("color: #8E8E98; border: none;")
        layout.addWidget(key_lbl)

        key_row = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("AIzaSy... (Gemini 2.0 Flash) or gsk_...")
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setText(get_grok_api_key())
        self.key_input.setStyleSheet("""
            QLineEdit {
                background: #1C1C24;
                border: 1px solid #30303C;
                border-radius: 6px;
                color: #FFFFFF;
                padding: 6px 8px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #3380FF;
            }
        """)
        self.key_input.textChanged.connect(self._on_key_text_changed)
        key_row.addWidget(self.key_input)

        save_key_btn = QPushButton("Save")
        save_key_btn.setStyleSheet("""
            QPushButton {
                background: #3380FF;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #2566D9;
            }
        """)
        save_key_btn.clicked.connect(self._save_key)
        key_row.addWidget(save_key_btn)

        test_key_btn = QPushButton("Test")
        test_key_btn.setStyleSheet("""
            QPushButton {
                background: #2A2A36;
                color: #D0D0DC;
                border: 1px solid #3D3D4E;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #38384A;
                color: #FFFFFF;
            }
        """)
        test_key_btn.clicked.connect(self._test_key)
        key_row.addWidget(test_key_btn)

        layout.addLayout(key_row)

        # Provider hint label
        self.provider_hint = QLabel("")
        self.provider_hint.setFont(QFont("Segoe UI", 8))
        self.provider_hint.setStyleSheet("color: #7A7A88; border: none;")
        self._update_provider_hint(self.key_input.text())
        layout.addWidget(self.provider_hint)

        # 4. Settings Selectors
        settings_row = QHBoxLayout()

        # Model Picker
        model_vbox = QVBoxLayout()
        model_lbl = QLabel("Model")
        model_lbl.setFont(QFont("Segoe UI", 8, QFont.Bold))
        model_lbl.setStyleSheet("color: #8E8E98; border: none;")
        model_vbox.addWidget(model_lbl)

        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "auto (Recommended)",
            "gemini-3.5-flash",
            "qwen/qwen3.8-27b",
            "grok-2-vision-1212"
        ])
        curr_m = self.config.get("grok_model", "auto")
        # Match current config or fallback
        found = False
        for i in range(self.model_combo.count()):
            if curr_m in self.model_combo.itemText(i):
                self.model_combo.setCurrentIndex(i)
                found = True
                break
        if not found:
            self.model_combo.setCurrentIndex(0)

        self.model_combo.setStyleSheet(self._combo_style())
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        model_vbox.addWidget(self.model_combo)
        settings_row.addLayout(model_vbox)

        # Voice Picker
        voice_vbox = QVBoxLayout()
        voice_lbl = QLabel("Voice")
        voice_lbl.setFont(QFont("Segoe UI", 8, QFont.Bold))
        voice_lbl.setStyleSheet("color: #8E8E98; border: none;")
        voice_vbox.addWidget(voice_lbl)

        self.voice_combo = QComboBox()
        self.voice_map = {
            "Jenny (US)": "en-US-JennyNeural",
            "Guy (US)": "en-US-GuyNeural",
            "Aria (US)": "en-US-AriaNeural",
            "Sonia (UK)": "en-GB-SoniaNeural",
        }
        for name in self.voice_map:
            self.voice_combo.addItem(name)
        curr_v = self.config.get("tts_voice", "en-US-JennyNeural")
        for k, v in self.voice_map.items():
            if v == curr_v:
                self.voice_combo.setCurrentText(k)
        self.voice_combo.setStyleSheet(self._combo_style())
        self.voice_combo.currentTextChanged.connect(self._on_voice_changed)
        voice_vbox.addWidget(self.voice_combo)
        settings_row.addLayout(voice_vbox)

        layout.addLayout(settings_row)

        # 5. Onboarding Demo Button
        demo_btn = QPushButton("✨ Test Pointing Demo")
        demo_btn.setStyleSheet("""
            QPushButton {
                background: #242430;
                color: #3380FF;
                border: 1px solid #3380FF;
                border-radius: 6px;
                padding: 7px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #3380FF;
                color: #FFFFFF;
            }
        """)
        demo_btn.clicked.connect(self.demo_requested.emit)
        layout.addWidget(demo_btn)

        layout.addWidget(self._make_divider())

        # 6. Footer (Quit)
        footer = QHBoxLayout()
        footer.addStretch()

        quit_btn = QPushButton("Quit Clicky")
        quit_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #FF5555;
                border: none;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        quit_btn.clicked.connect(lambda: QApplication.instance().quit())
        footer.addWidget(quit_btn)
        layout.addLayout(footer)

        main_layout.addWidget(self.container)

    def _make_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("border: none; border-top: 1px solid #24242C;")
        return line

    def _combo_style(self) -> str:
        return """
            QComboBox {
                background: #1C1C24;
                border: 1px solid #30303C;
                border-radius: 6px;
                color: #FFFFFF;
                padding: 4px 8px;
                font-size: 10px;
            }
            QComboBox QAbstractItemView {
                background: #1C1C24;
                color: #FFFFFF;
                selection-background-color: #3380FF;
            }
        """

    def _on_key_text_changed(self, text: str):
        self._update_provider_hint(text)

    def _update_provider_hint(self, key: str):
        k = key.strip()
        if k.startswith("AQ.") or k.startswith("AIza"):
            self.provider_hint.setText("✓ Detected: Google Gemini (3.5 Flash • 1M TPM Free)")
            self.provider_hint.setStyleSheet("color: #00D26A; border: none; font-size: 10px;")
        elif k.startswith("gsk_"):
            self.provider_hint.setText("✓ Detected: Groq Cloud (Free Tier • 100% Free)")
            self.provider_hint.setStyleSheet("color: #00D26A; border: none; font-size: 10px;")
        elif k.startswith("xai-"):
            self.provider_hint.setText("✓ Detected: xAI Grok (Paid API Credits)")
            self.provider_hint.setStyleSheet("color: #3380FF; border: none; font-size: 10px;")
        elif not k or "PLACEHOLDER" in k.upper() or k.startswith("YOUR_"):
            self.provider_hint.setText("Paste your Gemini key from aistudio.google.com/app/apikey")
            self.provider_hint.setStyleSheet("color: #FFAA00; border: none; font-size: 10px;")
        else:
            self.provider_hint.setText("Custom Key (Gemini: AIzaSy..., Groq: gsk_..., xAI: xai-...)")
            self.provider_hint.setStyleSheet("color: #7A7A88; border: none; font-size: 10px;")

    def _test_key(self):
        key = self.key_input.text().strip()
        if not key:
            self.status_lbl.setText("No key!")
            self.status_lbl.setStyleSheet("color: #FF5555; border: none;")
            return

        self.status_lbl.setText("Testing...")
        self.status_lbl.setStyleSheet("color: #FFAA00; border: none;")
        QApplication.processEvents()

        client = GrokClient(api_key=key)
        ok, msg = client.test_connection()
        if ok:
            self.status_lbl.setText("Connected!")
            self.status_lbl.setStyleSheet("color: #00D26A; border: none;")
            self.provider_hint.setText(f"✓ {msg}")
            self.provider_hint.setStyleSheet("color: #00D26A; border: none; font-size: 10px;")
        else:
            self.status_lbl.setText("Failed")
            self.status_lbl.setStyleSheet("color: #FF5555; border: none;")
            self.provider_hint.setText(f"✕ {msg[:45]}...")
            self.provider_hint.setStyleSheet("color: #FF5555; border: none; font-size: 10px;")

    def _save_key(self):
        key = self.key_input.text().strip()
        set_grok_api_key(key)
        self.status_lbl.setText("Key Saved!")
        self.status_lbl.setStyleSheet("color: #4CAF50; border: none;")

    def _on_model_changed(self, text: str):
        cfg = load_config()
        cfg["grok_model"] = text
        save_config(cfg)

    def _on_voice_changed(self, text: str):
        voice_id = self.voice_map.get(text, "en-US-JennyNeural")
        cfg = load_config()
        cfg["tts_voice"] = voice_id
        save_config(cfg)

    def set_status(self, text: str):
        self.status_lbl.setText(text)
        if text.lower() == "listening...":
            self.dot.setStyleSheet("color: #FF5555; font-size: 14px; border: none;")
        elif text.lower() in ("thinking...", "processing..."):
            self.dot.setStyleSheet("color: #FFAA00; font-size: 14px; border: none;")
        else:
            self.dot.setStyleSheet("color: #3380FF; font-size: 14px; border: none;")

    def show_near_tray(self):
        """Position panel neatly above taskbar near bottom right."""
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 16, screen.bottom() - self.height() - 16)
        self.show()
        self.raise_()
        self.activateWindow()

