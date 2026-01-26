from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QDialogButtonBox,
    QInputDialog,
    QMessageBox,
    QAbstractItemView,
)


TYPE_ROLE = Qt.UserRole
TYPE_THEME = "theme"
TYPE_CODE = "code"


class ThemeTreeWidget(QTreeWidget):
    def __init__(self, dialog):
        super().__init__(dialog)
        self.dialog = dialog
        self.setHeaderLabels(["Temas y categorias"])
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragDropMode(QAbstractItemView.DragDrop)

    def dropEvent(self, event):
        if self.dialog.handle_theme_drop(event):
            return
        super().dropEvent(event)


class ThemesCategoriesDialog(QDialog):
    def __init__(self, codes, themes, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Temas y categorias")
        self.resize(760, 440)
        self._updating = False
        self.codes = list(codes or [])
        self.themes = {}
        self.theme_order = []
        self._load_themes(themes)
        self._build_ui()
        self._load_theme_tree()

    def _load_themes(self, themes):
        for item in themes or []:
            name = (item or {}).get("name")
            if not name:
                continue
            codes = (item or {}).get("codes") or []
            valid_codes = [c for c in codes if c in self.codes]
            self.themes[name] = set(valid_codes)
            self.theme_order.append(name)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        header = QLabel("Arrastra codigos hacia un tema para agruparlos.")
        layout.addWidget(header)

        body = QHBoxLayout()

        left = QVBoxLayout()
        left_header = QHBoxLayout()
        left_header.addWidget(QLabel("Temas y categorias"))
        left_header.addStretch()
        self.btn_add_theme = QPushButton("Agregar")
        self.btn_rename_theme = QPushButton("Renombrar")
        self.btn_delete_theme = QPushButton("Eliminar")
        left_header.addWidget(self.btn_add_theme)
        left_header.addWidget(self.btn_rename_theme)
        left_header.addWidget(self.btn_delete_theme)
        left.addLayout(left_header)

        self.theme_tree = ThemeTreeWidget(self)
        self.theme_tree.itemClicked.connect(self._on_tree_item_clicked)
        self.theme_tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        left.addWidget(self.theme_tree, 1)

        self.btn_remove_code = QPushButton("Quitar codigo del tema")
        self.btn_remove_code.clicked.connect(self._remove_selected_codes)
        left.addWidget(self.btn_remove_code)

        right = QVBoxLayout()
        right.addWidget(QLabel("Codigos disponibles"))
        self.codes_hint = QLabel("Selecciona uno o varios codigos y arrastra al tema.")
        right.addWidget(self.codes_hint)
        self.code_list = QListWidget()
        self.code_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.code_list.setDragEnabled(True)
        right.addWidget(self.code_list, 1)
        self.lbl_count = QLabel("")
        right.addWidget(self.lbl_count)

        body.addLayout(left, 2)
        body.addLayout(right, 1)
        layout.addLayout(body, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.btn_add_theme.clicked.connect(self._add_theme)
        self.btn_rename_theme.clicked.connect(self._rename_theme)
        self.btn_delete_theme.clicked.connect(self._delete_theme)

        self._load_code_list()

    def _load_code_list(self):
        self.code_list.clear()
        for code in self.codes:
            item = QListWidgetItem(code)
            self.code_list.addItem(item)

    def _load_theme_tree(self):
        self.theme_tree.clear()
        for name in self.theme_order:
            theme_item = self._add_theme_item(name)
            for code in self._ordered_codes_for_theme(name):
                self._add_code_item(theme_item, code)
            theme_item.setExpanded(True)
        self._update_count(None)

    def _ordered_codes_for_theme(self, theme_name):
        selected = self.themes.get(theme_name, set())
        return [code for code in self.codes if code in selected]

    def _add_theme_item(self, name):
        item = QTreeWidgetItem([name])
        item.setData(0, TYPE_ROLE, TYPE_THEME)
        flags = item.flags()
        item.setFlags((flags | Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDropEnabled) & ~Qt.ItemIsDragEnabled)
        self.theme_tree.addTopLevelItem(item)
        return item

    def _add_code_item(self, theme_item, code_name):
        if self._find_code_child(theme_item, code_name):
            return
        item = QTreeWidgetItem([code_name])
        item.setData(0, TYPE_ROLE, TYPE_CODE)
        flags = item.flags()
        item.setFlags((flags | Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled) & ~Qt.ItemIsDropEnabled)
        theme_item.addChild(item)

    def _find_code_child(self, theme_item, code_name):
        for idx in range(theme_item.childCount()):
            child = theme_item.child(idx)
            if child.text(0) == code_name:
                return child
        return None

    def _item_type(self, item):
        return item.data(0, TYPE_ROLE) if item else None

    def _theme_item_from_item(self, item):
        if not item:
            return None
        if self._item_type(item) == TYPE_THEME:
            return item
        if self._item_type(item) == TYPE_CODE:
            return item.parent()
        return None

    def _on_tree_item_clicked(self, item, column):
        if self._item_type(item) == TYPE_THEME:
            item.setExpanded(True)
        self._update_count(item)

    def _on_tree_selection_changed(self):
        items = self.theme_tree.selectedItems()
        current = items[0] if items else None
        self._update_count(current)

    def _update_count(self, item):
        theme_item = self._theme_item_from_item(item)
        if not theme_item:
            self.lbl_count.setText("Codigos en tema: 0")
            return
        name = theme_item.text(0)
        count = len(self.themes.get(name, set()))
        self.lbl_count.setText(f"Codigos en tema: {count}")

    def _add_theme(self):
        name, ok = QInputDialog.getText(self, "Nuevo tema", "Nombre del tema o categoria:")
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            return
        if name in self.themes:
            QMessageBox.warning(self, "Tema existente", "Ya existe un tema con ese nombre.")
            return
        self.themes[name] = set()
        self.theme_order.append(name)
        theme_item = self._add_theme_item(name)
        theme_item.setExpanded(True)
        self.theme_tree.setCurrentItem(theme_item)
        self._update_count(theme_item)

    def _rename_theme(self):
        current = self.theme_tree.currentItem()
        theme_item = self._theme_item_from_item(current)
        if not theme_item:
            return
        old_name = theme_item.text(0)
        new_name, ok = QInputDialog.getText(self, "Renombrar tema", "Nuevo nombre:", text=old_name)
        if not ok:
            return
        new_name = (new_name or "").strip()
        if not new_name or new_name == old_name:
            return
        if new_name in self.themes:
            QMessageBox.warning(self, "Tema existente", "Ya existe un tema con ese nombre.")
            return
        self.themes[new_name] = self.themes.pop(old_name, set())
        index = self.theme_order.index(old_name)
        self.theme_order[index] = new_name
        theme_item.setText(0, new_name)
        self._update_count(theme_item)

    def _delete_theme(self):
        current = self.theme_tree.currentItem()
        theme_item = self._theme_item_from_item(current)
        if not theme_item:
            return
        name = theme_item.text(0)
        confirm = QMessageBox.question(
            self,
            "Eliminar tema",
            f"Eliminar el tema '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        self.themes.pop(name, None)
        if name in self.theme_order:
            self.theme_order.remove(name)
        idx = self.theme_tree.indexOfTopLevelItem(theme_item)
        if idx >= 0:
            self.theme_tree.takeTopLevelItem(idx)
        self._update_count(None)

    def _remove_selected_codes(self):
        selected = [i for i in self.theme_tree.selectedItems() if self._item_type(i) == TYPE_CODE]
        for item in selected:
            parent = item.parent()
            if not parent:
                continue
            theme_name = parent.text(0)
            self.themes.get(theme_name, set()).discard(item.text(0))
            parent.removeChild(item)
        self._update_count(self.theme_tree.currentItem())

    def _item_at_event(self, event):
        if hasattr(event, "position"):
            pos = event.position().toPoint()
        else:
            pos = event.pos()
        return self.theme_tree.itemAt(pos)

    def handle_theme_drop(self, event):
        target_item = self._item_at_event(event)
        theme_item = self._theme_item_from_item(target_item)
        if not theme_item:
            event.ignore()
            return True

        theme_name = theme_item.text(0)
        source = event.source()
        moved_codes = []

        if isinstance(source, QListWidget):
            for item in source.selectedItems():
                moved_codes.append(item.text())
        elif isinstance(source, ThemeTreeWidget):
            selected = [i for i in self.theme_tree.selectedItems() if self._item_type(i) == TYPE_CODE]
            for item in selected:
                old_parent = item.parent()
                if old_parent:
                    old_theme = old_parent.text(0)
                    self.themes.get(old_theme, set()).discard(item.text(0))
                    old_parent.removeChild(item)
                moved_codes.append(item.text(0))
        else:
            return False

        if not moved_codes:
            event.ignore()
            return True

        self.themes.setdefault(theme_name, set())
        for code_name in moved_codes:
            if code_name in self.themes[theme_name]:
                continue
            self.themes[theme_name].add(code_name)
            self._add_code_item(theme_item, code_name)

        theme_item.setExpanded(True)
        self._update_count(theme_item)
        event.acceptProposedAction()
        return True

    def get_themes_data(self):
        output = []
        for name in self.theme_order:
            selected = self.themes.get(name, set())
            ordered = [code for code in self.codes if code in selected]
            output.append({"name": name, "codes": ordered})
        return output
