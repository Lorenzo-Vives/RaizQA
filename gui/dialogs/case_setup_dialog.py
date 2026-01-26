from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QDialogButtonBox,
    QInputDialog,
    QMessageBox,
    QAbstractItemView,
    QTextEdit,
)


class CaseSetupDialog(QDialog):
    def __init__(self, documents, doc_groups, case_studies, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Definir casos")
        self.resize(720, 420)
        self.documents = documents or []
        self.doc_groups = doc_groups or {}
        self.case_map = {}
        self.case_characteristics = {}
        self.case_comments = {}
        self.case_order = []
        self._load_cases(case_studies)
        self._build_ui()
        self._load_case_list()
        if self.case_list.count() > 0:
            self.case_list.setCurrentRow(0)
        else:
            self._refresh_doc_checks(None)

    def _load_cases(self, case_studies):
        for item in case_studies or []:
            name = (item or {}).get("name")
            if not name:
                continue
            docs = (item or {}).get("documents") or []
            valid_docs = [d for d in docs if d in self.documents]
            self.case_map[name] = set(valid_docs)
            self.case_characteristics[name] = (item or {}).get("characteristics", "") or ""
            self.case_comments[name] = (item or {}).get("comments", "") or ""
            self.case_order.append(name)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Crea casos y asigna documentos."))

        body = QHBoxLayout()
        left = QVBoxLayout()
        left_header = QHBoxLayout()
        left_header.addWidget(QLabel("Casos"))
        left_header.addStretch()
        self.btn_add = QPushButton("Agregar")
        self.btn_rename = QPushButton("Renombrar")
        self.btn_delete = QPushButton("Eliminar")
        self.btn_import_folders = QPushButton("Usar carpetas")
        left_header.addWidget(self.btn_add)
        left_header.addWidget(self.btn_rename)
        left_header.addWidget(self.btn_delete)
        left_header.addWidget(self.btn_import_folders)
        left.addLayout(left_header)

        self.case_list = QListWidget()
        self.case_list.currentItemChanged.connect(self._on_case_selected)
        left.addWidget(self.case_list, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel("Documentos"))
        self.doc_list = QListWidget()
        self.doc_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.doc_list.itemChanged.connect(self._on_doc_toggled)
        right.addWidget(self.doc_list, 1)
        right.addWidget(QLabel("Caracteristicas"))
        self.characteristics_edit = QTextEdit()
        self.characteristics_edit.setPlaceholderText("Describe las caracteristicas del caso...")
        self.characteristics_edit.textChanged.connect(self._on_characteristics_changed)
        right.addWidget(self.characteristics_edit, 1)
        right.addWidget(QLabel("Comentarios"))
        self.comments_edit = QTextEdit()
        self.comments_edit.setPlaceholderText("Agrega comentarios propios sobre el caso...")
        self.comments_edit.textChanged.connect(self._on_comments_changed)
        right.addWidget(self.comments_edit, 1)

        body.addLayout(left, 1)
        body.addLayout(right, 2)
        layout.addLayout(body, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.btn_add.clicked.connect(self._add_case)
        self.btn_rename.clicked.connect(self._rename_case)
        self.btn_delete.clicked.connect(self._delete_case)
        self.btn_import_folders.clicked.connect(self._import_from_folders)

        self._load_doc_list()

    def _load_case_list(self):
        self.case_list.clear()
        for name in self.case_order:
            self.case_list.addItem(name)

    def _load_doc_list(self):
        self.doc_list.clear()
        for doc in self.documents:
            item = QListWidgetItem(doc)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.doc_list.addItem(item)

    def _current_case(self):
        item = self.case_list.currentItem()
        return item.text() if item else None

    def _on_case_selected(self, current, previous):
        name = current.text() if current else None
        self._refresh_doc_checks(name)
        self._refresh_case_fields(name)

    def _refresh_doc_checks(self, case_name):
        selected = self.case_map.get(case_name, set()) if case_name else set()
        self.doc_list.setEnabled(bool(case_name))
        for idx in range(self.doc_list.count()):
            item = self.doc_list.item(idx)
            item.setCheckState(Qt.Checked if item.text() in selected else Qt.Unchecked)

    def _refresh_case_fields(self, case_name):
        enabled = bool(case_name)
        self.characteristics_edit.setEnabled(enabled)
        self.comments_edit.setEnabled(enabled)
        characteristics = self.case_characteristics.get(case_name, "") if enabled else ""
        comments = self.case_comments.get(case_name, "") if enabled else ""
        self.characteristics_edit.blockSignals(True)
        self.comments_edit.blockSignals(True)
        self.characteristics_edit.setPlainText(characteristics)
        self.comments_edit.setPlainText(comments)
        self.characteristics_edit.blockSignals(False)
        self.comments_edit.blockSignals(False)

    def _on_doc_toggled(self, item):
        case_name = self._current_case()
        if not case_name:
            return
        doc_name = item.text()
        self.case_map.setdefault(case_name, set())
        if item.checkState() == Qt.Checked:
            self.case_map[case_name].add(doc_name)
        else:
            self.case_map[case_name].discard(doc_name)

    def _on_characteristics_changed(self):
        case_name = self._current_case()
        if not case_name:
            return
        self.case_characteristics[case_name] = self.characteristics_edit.toPlainText()

    def _on_comments_changed(self):
        case_name = self._current_case()
        if not case_name:
            return
        self.case_comments[case_name] = self.comments_edit.toPlainText()

    def _add_case(self):
        name, ok = QInputDialog.getText(self, "Nuevo caso", "Nombre del caso:")
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            return
        if name in self.case_map:
            QMessageBox.warning(self, "Caso existente", "Ya existe un caso con ese nombre.")
            return
        self.case_map[name] = set()
        self.case_characteristics[name] = ""
        self.case_comments[name] = ""
        self.case_order.append(name)
        self.case_list.addItem(name)
        self.case_list.setCurrentRow(self.case_list.count() - 1)

    def _rename_case(self):
        current = self.case_list.currentItem()
        if not current:
            return
        old_name = current.text()
        new_name, ok = QInputDialog.getText(self, "Renombrar caso", "Nuevo nombre:", text=old_name)
        if not ok:
            return
        new_name = (new_name or "").strip()
        if not new_name or new_name == old_name:
            return
        if new_name in self.case_map:
            QMessageBox.warning(self, "Caso existente", "Ya existe un caso con ese nombre.")
            return
        self.case_map[new_name] = self.case_map.pop(old_name, set())
        self.case_characteristics[new_name] = self.case_characteristics.pop(old_name, "")
        self.case_comments[new_name] = self.case_comments.pop(old_name, "")
        index = self.case_order.index(old_name)
        self.case_order[index] = new_name
        current.setText(new_name)

    def _delete_case(self):
        current = self.case_list.currentItem()
        if not current:
            return
        name = current.text()
        confirm = QMessageBox.question(
            self,
            "Eliminar caso",
            f"Eliminar el caso '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        self.case_map.pop(name, None)
        self.case_characteristics.pop(name, None)
        self.case_comments.pop(name, None)
        if name in self.case_order:
            self.case_order.remove(name)
        row = self.case_list.row(current)
        self.case_list.takeItem(row)
        if self.case_list.count() > 0:
            self.case_list.setCurrentRow(min(row, self.case_list.count() - 1))
        else:
            self._refresh_doc_checks(None)
            self._refresh_case_fields(None)

    def _import_from_folders(self):
        folders = [k for k in self.doc_groups.keys() if k != "__root__"]
        if not folders:
            QMessageBox.information(self, "Carpetas", "No hay carpetas de documentos para usar como casos.")
            return
        for folder in folders:
            if folder in self.case_map:
                continue
            docs = self.doc_groups.get(folder, [])
            valid_docs = [d for d in docs if d in self.documents]
            if not valid_docs:
                continue
            self.case_map[folder] = set(valid_docs)
            self.case_characteristics.setdefault(folder, "")
            self.case_comments.setdefault(folder, "")
            self.case_order.append(folder)
        self._load_case_list()
        if self.case_list.count() > 0:
            self.case_list.setCurrentRow(0)

    def get_case_studies(self):
        output = []
        for name in self.case_order:
            docs = self.case_map.get(name, set())
            ordered = [d for d in self.documents if d in docs]
            output.append(
                {
                    "name": name,
                    "documents": ordered,
                    "characteristics": self.case_characteristics.get(name, "") or "",
                    "comments": self.case_comments.get(name, "") or "",
                }
            )
        return output
