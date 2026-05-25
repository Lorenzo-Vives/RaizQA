from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QDialogButtonBox, QButtonGroup
)
from PySide6.QtCore import Qt

class NewCodeDialog(QDialog):
    """
    Diálogo unificado para crear un código nuevo (Nombre, Color y Memo).
    Inspirado en el flujo de trabajo de MaxQDA.
    """
    def __init__(self, palette, default_name="", default_color=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo código")
        self.resize(450, 380)
        
        self.palette = palette
        # Si no se provee un color por defecto, usamos el primero de la paleta
        self.selected_color = default_color or palette[0][1]
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # 1. Nombre del código
        layout.addWidget(QLabel("Nombre del código:"))
        self.name_input = QLineEdit(default_name)
        self.name_input.setPlaceholderText("Ej. Comportamiento atípico")
        layout.addWidget(self.name_input)
        
        # 2. Paleta de colores
        layout.addWidget(QLabel("Color:"))
        color_layout = QHBoxLayout()
        color_layout.setSpacing(8)
        self.color_group = QButtonGroup(self)
        
        for idx, (label_name, hex_color) in enumerate(palette):
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setToolTip(label_name)
            
            # Estilo de círculo de color (al seleccionarse se le pone un borde oscuro)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_color};
                    border: 2px solid transparent;
                    border-radius: 12px;
                }}
                QPushButton:checked {{
                    border: 2px solid #333333;
                }}
                QPushButton:hover {{
                    border: 2px solid #888888;
                }}
            """)
            btn.setProperty("hex_color", hex_color)
            
            self.color_group.addButton(btn, idx)
            color_layout.addWidget(btn)
            
            # Seleccionar por defecto el color sugerido
            if hex_color == self.selected_color:
                btn.setChecked(True)
                
        self.color_group.buttonClicked.connect(self._on_color_selected)
        color_layout.addStretch()
        layout.addLayout(color_layout)
        
        # 3. Memo (Opcional)
        layout.addWidget(QLabel("Memo del código:"))
        self.memo_input = QTextEdit()
        self.memo_input.setPlaceholderText("Escribe aquí notas o la definición metodológica de este código...")
        layout.addWidget(self.memo_input)
        
        # 4. Botones de acción
        self.btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)
        
        # Cambiar el texto de los botones por defecto al español
        self.btn_box.button(QDialogButtonBox.Ok).setText("Crear código")
        self.btn_box.button(QDialogButtonBox.Cancel).setText("Cancelar")
        
        layout.addWidget(self.btn_box)

    def _on_color_selected(self, btn):
        self.selected_color = btn.property("hex_color")

    def get_data(self):
        """Devuelve una tupla con (nombre, color_hexadecimal, memo)"""
        return self.name_input.text().strip(), self.selected_color, self.memo_input.toPlainText().strip()