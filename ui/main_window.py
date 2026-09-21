import asyncio
import json
import os
import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QTextEdit, QLineEdit, QPushButton, QHBoxLayout,
                             QMenu, QSystemTrayIcon, QApplication, QMessageBox,
                             QLabel, QStatusBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QIcon, QFont
from qasync import asyncSlot
from core.ollama_client import OllamaClient
from ui.settings_dialog import SettingsDialog

HISTORY_FILE = "chat_history.json"
SETTINGS_FILE = "app_settings.json"

class MainWindow(QMainWindow):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.settings = self.load_settings()
        self.client = OllamaClient(model=self.settings.get("model", "gemma3:1b"))
        self.messages: list[dict] = []  # تاریخچه به فرمت Ollama
        self.is_dark = False

        self.init_ui()
        self.init_tray()
        self.load_history()

        # گرم‌کردن مدل
        asyncio.ensure_future(self.warm_up_model())

        # اعمال تم اولیه
        self.apply_theme()

    # ---------- UI ----------
    def init_ui(self):
        self.setWindowTitle("Chat AI Desktop")
        self.setMinimumSize(700, 500)

        # آیکون
        icon_path = self.resource_path("resources/icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # نوار ابزار کوچک (دکمه تنظیمات، تم)
        toolbar = QHBoxLayout()
        self.settings_btn = QPushButton("⚙ تنظیمات")
        self.settings_btn.clicked.connect(self.open_settings)
        self.theme_btn = QPushButton("🌓 تغییر تم")
        self.theme_btn.clicked.connect(self.toggle_theme)
        toolbar.addWidget(self.settings_btn)
        toolbar.addWidget(self.theme_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # نمایش چت
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Tahoma", 10))
        layout.addWidget(self.chat_display)

        # ناحیه ورودی
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("پیام خود را بنویسید...")
        self.send_btn = QPushButton("ارسال")
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)

        # status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status_label = QLabel("آماده")
        self.status.addWidget(self.status_label)

        # اتصال سیگنال‌ها
        self.send_btn.clicked.connect(self.on_send)
        self.input_field.returnPressed.connect(self.on_send)

    # ---------- System Tray ----------
    def init_tray(self):
        icon_path = self.resource_path("resources/icon.ico")
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(
                self.style().StandardPixmap.SP_ComputerIcon))

        tray_menu = QMenu()
        show_action = QAction("نمایش", self)
        show_action.triggered.connect(self.show_window)
        quit_action = QAction("خروج", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()

    def show_window(self):
        self.showNormal()
        self.activateWindow()

    def quit_app(self):
        self.save_history()
        self.tray_icon.hide()
        QApplication.quit()

    # در صورت بستن پنجره، به جای خروج، minimize to tray شود
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Chat AI", "برنامه در پس‌زمینه به کار خود ادامه می‌دهد.",
            QSystemTrayIcon.MessageIcon.Information, 2000)

    # ---------- منطق چت ----------
    async def warm_up_model(self):
        self.status_label.setText("در حال آماده‌سازی مدل...")
        self.chat_display.append("⏳ در حال بارگذاری مدل...")
        await self.client.warm_up()
        self.chat_display.append(f"✅ مدل {self.client.model} آماده است.\n")
        self.status_label.setText("آماده")

    @asyncSlot()
    async def on_send(self):
        user_text = self.input_field.text().strip()
        if not user_text:
            return

        self.input_field.clear()
        self.input_field.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.status_label.setText("در حال پاسخگویی...")

        # نمایش پیام کاربر
        self.chat_display.append(f"<b>شما:</b> {user_text}")
        self.messages.append({"role": "user", "content": user_text})

        # اضافه کردن خط برای دستیار
        self.chat_display.append("<b>دستیار:</b> ")
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        full_response = ""
        try:
            options = {k: v for k, v in self.settings.items() 
                       if k in ("temperature", "top_k", "num_predict", "num_ctx", "num_gpu")}
            async for token in self.client.stream_chat(self.messages, options=options):
                full_response += token
                cursor.insertText(token)
                self.chat_display.setTextCursor(cursor)
                await asyncio.sleep(0)
        except Exception as e:
            full_response = f"خطا: {str(e)}"
            self.chat_display.append(full_response)

        self.messages.append({"role": "assistant", "content": full_response})
        self.chat_display.append("\n")  # خط جدید بعد از پاسخ

        # فعال‌سازی مجدد ورودی
        self.input_field.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.input_field.setFocus()
        self.status_label.setText("آماده")
        self.save_history()

    # ---------- تنظیمات ----------
    def open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec() == SettingsDialog.DialogCode.Accepted:
            new_settings = dlg.get_settings()
            # اگر مدل عوض شد، کلاینت جدید بسازیم و warm up کنیم
            if new_settings["model"] != self.settings.get("model"):
                self.client = OllamaClient(model=new_settings["model"])
                self.chat_display.append(f"🔄 تغییر مدل به {new_settings['model']} ...")
                self.save_settings(new_settings)
                self.settings = new_settings
                asyncio.ensure_future(self.warm_up_model())
            else:
                self.settings = new_settings
                self.save_settings(new_settings)

    # ---------- تاریخچه و تنظیمات روی دیسک ----------
    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    self.messages = json.load(f)
                # بازسازی نمایش (اختیاری)
                for msg in self.messages:
                    role = "شما" if msg["role"] == "user" else "دستیار"
                    self.chat_display.append(f"<b>{role}:</b> {msg['content']}")
                self.chat_display.append("--- تاریخچه بارگذاری شد ---\n")
            except:
                pass

    def save_history(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2)
        except:
            pass

    def load_settings(self) -> dict:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"model": "gemma3:1b", "temperature": 0.0, "top_k": 1,
                "num_predict": 256, "num_ctx": 2048, "num_gpu": 999}

    def save_settings(self, settings: dict):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

    # ---------- تم ----------
    def apply_theme(self):
        if self.is_dark:
            self.setStyleSheet("""
                QMainWindow, QDialog, QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                    background-color: #2b2b2b;
                    color: #eeeeee;
                }
                QPushButton {
                    background-color: #3c3c3c;
                    color: #eeeeee;
                    border: 1px solid #555;
                    padding: 5px;
                }
                QPushButton:hover { background-color: #505050; }
                QStatusBar { background: #3c3c3c; color: #eeeeee; }
            """)
        else:
            self.setStyleSheet("")

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self.apply_theme()

    # ---------- ابزار مسیر فایل‌ها (برای PyInstaller) ----------
    @staticmethod
    def resource_path(relative_path):
        """مسیر فایل‌های منابع را هم در حالت توسعه و هم در بسته PyInstaller برمی‌گرداند"""
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)