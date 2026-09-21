from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, 
                             QComboBox, QDoubleSpinBox, QSpinBox, 
                             QPushButton, QHBoxLayout, QMessageBox)
from PyQt6.QtCore import Qt
from qasync import asyncSlot
from core.ollama_client import OllamaClient

class SettingsDialog(QDialog):
    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تنظیمات")
        self.setModal(True)
        self.settings = current_settings.copy()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        form.addRow("مدل:", self.model_combo)

        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(self.settings.get("temperature", 0.0))
        form.addRow("دما (Temperature):", self.temp_spin)

        self.topk_spin = QSpinBox()
        self.topk_spin.setRange(1, 100)
        self.topk_spin.setValue(self.settings.get("top_k", 1))
        form.addRow("Top-K:", self.topk_spin)

        self.npred_spin = QSpinBox()
        self.npred_spin.setRange(1, 4096)
        self.npred_spin.setValue(self.settings.get("num_predict", 256))
        form.addRow("حداکثر توکن خروجی:", self.npred_spin)

        self.ctx_spin = QSpinBox()
        self.ctx_spin.setRange(512, 32768)
        self.ctx_spin.setValue(self.settings.get("num_ctx", 2048))
        form.addRow("پنجره متن (Context):", self.ctx_spin)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.fetch_btn = QPushButton("دریافت مدل‌های نصب‌شده")
        self.fetch_btn.clicked.connect(self.fetch_models)
        btn_layout.addWidget(self.fetch_btn)

        self.ok_btn = QPushButton("تأیید")
        self.ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("لغو")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        current_model = self.settings.get("model", "gemma3:1b")
        self.model_combo.addItem(current_model)
        self.model_combo.setCurrentText(current_model)
        self.fetch_models()

    @asyncSlot()
    async def fetch_models(self):
        try:
            models = await OllamaClient.list_models()
            self.model_combo.clear()
            self.model_combo.addItems(models)
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"دریافت مدل‌ها ممکن نشد:\n{str(e)}")

    def get_settings(self) -> dict:
        return {
            "model": self.model_combo.currentText(),
            "temperature": self.temp_spin.value(),
            "top_k": self.topk_spin.value(),
            "num_predict": self.npred_spin.value(),
            "num_ctx": self.ctx_spin.value(),
            "num_gpu": 999
        }
