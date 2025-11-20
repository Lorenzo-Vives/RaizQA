from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTextEdit,
    QLabel,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt


class DiaryDialog(QDialog):
    """Editor simple para el diario de codificación del proyecto."""

    def __init__(self, initial_text="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Diario de codificación")
        self.resize(560, 420)

        layout = QVBoxLayout(self)
        description = QLabel(
            "Usa este espacio para registrar notas metodológicas y reflexiones sobre tu proceso de codificación."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(description)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Escribe tu diario aquí...")
        self.text_edit.setPlainText(initial_text or "")
        layout.addWidget(self.text_edit, 1)

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_text(self):
        return self.text_edit.toPlainText()
