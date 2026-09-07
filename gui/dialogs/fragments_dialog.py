from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QMenu,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal

# -------------------- DIALOGO DE VISUALIZACIÓN DE FRAGMENTOS --------------------
class CodeFragmentsDialog(QDialog):
    fragment_delete_requested = Signal(str, str, int)

    def __init__(self, code_name, fragments, parent=None):
        super().__init__(parent)
        self.code_name = code_name
        self.setWindowTitle(f"Fragmentos del código: {code_name}")
        self.resize(700, 420)
        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        for frag in fragments:
            # mostrar preview para la lista
            preview = (frag.get("comment") or frag.get("text") or "").strip().replace("\n", " ")
            if not preview and frag.get("type") == "image":
                rect = frag.get("rect") or {}
                if rect:
                    preview = f"(Zona {rect.get('x', 0)},{rect.get('y', 0)} {rect.get('w', 0)}x{rect.get('h', 0)})"
                else:
                    preview = "(Imagen)"
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

    @staticmethod
    def _preview(fragment, limit=200):
        preview = (fragment.get("comment") or fragment.get("text") or "").strip().replace("\n", " ")
        if not preview and fragment.get("type") == "image":
            rect = fragment.get("rect") or {}
            if rect:
                preview = f"(Zona {rect.get('x', 0)},{rect.get('y', 0)} {rect.get('w', 0)}x{rect.get('h', 0)})"
            else:
                preview = "(Imagen)"
        if len(preview) > limit:
            preview = preview[:limit] + "..."
        return preview

    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if item is None:
            return
        menu = QMenu(self)
        delete_action = menu.addAction("Eliminar fragmento")
        chosen = menu.exec(self.list_widget.viewport().mapToGlobal(pos))
        if chosen == delete_action:
            self._confirm_delete(item)

    def _confirm_delete(self, item):
        fragment = item.data(Qt.UserRole) or {}
        document = fragment.get("document")
        fragment_index = fragment.get("_fragment_index")
        if not document or not isinstance(fragment_index, int):
            return

        preview = self._preview(fragment, limit=240) or "(Fragmento sin texto)"
        answer = QMessageBox.question(
            self,
            "Eliminar fragmento",
            f"¿Eliminar este fragmento de '{document}'?\n\n{preview}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.fragment_delete_requested.emit(self.code_name, document, fragment_index)
        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)
        self.viewer.clear()

        # Deleting shifts the remaining indices for the same document.
        for remaining_row in range(self.list_widget.count()):
            remaining_item = self.list_widget.item(remaining_row)
            remaining = remaining_item.data(Qt.UserRole) or {}
            old_index = remaining.get("_fragment_index")
            if remaining.get("document") == document and isinstance(old_index, int) and old_index > fragment_index:
                remaining["_fragment_index"] = old_index - 1
                remaining_item.setData(Qt.UserRole, remaining)

    def on_select(self):
        items = self.list_widget.selectedItems()
        if not items:
            self.viewer.clear()
            return
        frag = items[0].data(Qt.UserRole)
        self.viewer.setPlainText((frag.get("comment") or frag.get("text") or "").strip())
