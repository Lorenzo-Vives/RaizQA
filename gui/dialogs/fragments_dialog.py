from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QTextEdit
from PySide6.QtCore import Qt

# -------------------- DIALOGO DE VISUALIZACIÓN DE FRAGMENTOS --------------------
class CodeFragmentsDialog(QDialog):
    def __init__(self, code_name, fragments):
        super().__init__()
        self.setWindowTitle(f"Fragmentos del código: {code_name}")
        self.resize(700, 420)
        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        for frag in fragments:
            # mostrar preview para la lista
            preview = frag.get("text", "").strip().replace("\n", " ")
            if len(preview) > 200:
                preview = preview[:200] + "..."
            # incluir documento corto si viene
            doc = frag.get("document", "")
            display = f"{doc}  →  {preview}" if doc else preview
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, frag)
            self.list_widget.addItem(item)

        self.list_widget.itemSelectionChanged.connect(self.on_select)
        layout.addWidget(self.list_widget)

        self.viewer = QTextEdit()
        self.viewer.setReadOnly(True)
        self.viewer.setStyleSheet("background: white; font-size: 13px; padding: 8px;")
        self.viewer.setPlaceholderText("Selecciona un fragmento para ver el texto completo...")
        layout.addWidget(self.viewer)

        self.setLayout(layout)

    def on_select(self):
        items = self.list_widget.selectedItems()
        if not items:
            self.viewer.clear()
            return
        frag = items[0].data(Qt.UserRole)
        self.viewer.setPlainText(frag.get("text", ""))
