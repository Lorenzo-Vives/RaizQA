# -------------------- DIALOGO DE VISUALIZACIÓN DE FRAGMENTOS --------------------
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem,
    QTextEdit, QTreeWidget, QTreeWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt


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
            display = f"{doc} -> {preview}" if doc else preview
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


# -------------------- DIALOGO PARA VER TODOS LOS CÓDIGOS --------------------
class CodeViewerDialog(QDialog):
    """Visor más completo — si usas otro módulo en code_viewer, mantenlo; esta clase es auxiliar."""
    def __init__(self, codes):
        super().__init__()
        self.setWindowTitle("Visor de Códigos")
        self.resize(600, 420)

        layout = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Código", "n", "Memo"])
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.populate_tree(codes)
        layout.addWidget(self.tree)

    def populate_tree(self, codes):
        items_by_name = {}
        for c in codes:
            memo_mark = "" if c.get("memo") else ""
            item = QTreeWidgetItem([c["name"], str(c.get("count", 0)), memo_mark])
            items_by_name[c["name"]] = item
            if not c.get("parent"):
                self.tree.addTopLevelItem(item)
        for c in codes:
            parent_name = c.get("parent")
            if parent_name and parent_name in items_by_name:
                items_by_name[parent_name].addChild(items_by_name[c["name"]])
