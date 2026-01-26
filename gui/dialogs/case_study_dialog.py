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
    QSplitter,
    QPushButton,
    QTextEdit,
)

from code_viewer.code_viewer import CodeViewerWindow
from gui.dialogs.case_setup_dialog import CaseSetupDialog


class CaseStudyDialog(QDialog):
    def __init__(self, project, codes, documents, case_studies, doc_groups, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Estudio de casos")
        self.resize(860, 520)
        self.project = project
        self.codes = codes or []
        self.documents = documents or []
        self.doc_groups = doc_groups or {}
        self.case_studies = case_studies or []
        self.updated = False
        self._loading_case = False
        self._codes_by_name = {c.get("name"): c for c in self.codes if c.get("name")}
        self._children = self._build_children_map()
        self._build_ui()
        if not self.case_studies:
            if not self._open_case_setup():
                self.reject()
                return
        self._load_cases()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Selecciona un caso para analizar sus codigos y fragmentos."))

        splitter = QSplitter()
        splitter.setOrientation(Qt.Horizontal)

        left_panel = QVBoxLayout()
        left_header = QHBoxLayout()
        left_header.addWidget(QLabel("Casos"))
        left_header.addStretch()
        self.btn_manage_cases = QPushButton("Definir casos")
        self.btn_manage_cases.clicked.connect(self._manage_cases)
        left_header.addWidget(self.btn_manage_cases)
        left_panel.addLayout(left_header)
        self.doc_list = QListWidget()
        self.doc_list.itemSelectionChanged.connect(self._on_case_selected)
        left_panel.addWidget(self.doc_list, 1)
        left_wrapper = QDialog()
        left_wrapper.setLayout(left_panel)
        splitter.addWidget(left_wrapper)

        right_panel = QVBoxLayout()
        self.case_title = QLabel("Caso seleccionado: -")
        right_panel.addWidget(self.case_title)
        right_panel.addWidget(QLabel("Caracteristicas"))
        self.characteristics_edit = QTextEdit()
        self.characteristics_edit.setPlaceholderText("Describe las caracteristicas del caso...")
        self.characteristics_edit.textChanged.connect(self._on_characteristics_changed)
        right_panel.addWidget(self.characteristics_edit, 1)
        right_panel.addWidget(QLabel("Comentarios"))
        self.comments_edit = QTextEdit()
        self.comments_edit.setPlaceholderText("Agrega comentarios propios sobre el caso...")
        self.comments_edit.textChanged.connect(self._on_comments_changed)
        right_panel.addWidget(self.comments_edit, 1)
        self.summary_label = QLabel("")
        right_panel.addWidget(self.summary_label)
        self.code_tree = QTreeWidget()
        self.code_tree.setHeaderLabels(["Codigo", "Fragmentos"])
        self.code_tree.itemSelectionChanged.connect(self._on_code_selected)
        right_panel.addWidget(self.code_tree, 2)
        right_panel.addWidget(QLabel("Fragmentos del codigo seleccionado"))
        self.fragment_list = QListWidget()
        self.fragment_list.itemClicked.connect(self._open_fragment_viewer)
        right_panel.addWidget(self.fragment_list, 3)
        right_wrapper = QDialog()
        right_wrapper.setLayout(right_panel)
        splitter.addWidget(right_wrapper)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, 1)

    def _load_cases(self):
        self.doc_list.clear()
        for case in self.case_studies:
            name = case.get("name")
            if not name:
                continue
            self.doc_list.addItem(QListWidgetItem(name))
        if self.doc_list.count() > 0:
            self.doc_list.setCurrentRow(0)
        else:
            self._load_case_details(None)

    def _build_children_map(self):
        children = {}
        for code in self.codes:
            name = code.get("name")
            parent = code.get("parent")
            if not name:
                continue
            children.setdefault(parent, []).append(name)
        return children

    def _case_docs(self, case_name):
        for case in self.case_studies:
            if case.get("name") == case_name:
                return case.get("documents", []) or []
        return []

    def _case_entry(self, case_name):
        for case in self.case_studies:
            if case.get("name") == case_name:
                return case
        return None

    def _load_case_details(self, case_name):
        self._loading_case = True
        enabled = bool(case_name)
        self.case_title.setText(f"Caso seleccionado: {case_name}" if case_name else "Caso seleccionado: -")
        self.characteristics_edit.setEnabled(enabled)
        self.comments_edit.setEnabled(enabled)
        case = self._case_entry(case_name) if case_name else None
        characteristics = (case or {}).get("characteristics", "") if enabled else ""
        comments = (case or {}).get("comments", "") if enabled else ""
        self.characteristics_edit.blockSignals(True)
        self.comments_edit.blockSignals(True)
        self.characteristics_edit.setPlainText(characteristics or "")
        self.comments_edit.setPlainText(comments or "")
        self.characteristics_edit.blockSignals(False)
        self.comments_edit.blockSignals(False)
        self._loading_case = False

    def _doc_counts(self, doc_names):
        counts = {}
        for code in self.codes:
            name = code.get("name")
            if not name:
                continue
            frags = code.get("fragments", []) or []
            doc_frags = [f for f in frags if f.get("document") in doc_names]
            if doc_frags:
                counts[name] = len(doc_frags)
        return counts

    def _doc_fragments_by_code(self, doc_names):
        mapping = {}
        for code in self.codes:
            name = code.get("name")
            if not name:
                continue
            frags = code.get("fragments", []) or []
            doc_frags = [f for f in frags if f.get("document") in doc_names]
            if doc_frags:
                mapping[name] = doc_frags
        return mapping

    def _should_show_code(self, name, counts):
        if name in counts:
            return True
        for child in self._children.get(name, []):
            if self._should_show_code(child, counts):
                return True
        return False

    def _build_code_tree(self, doc_names):
        self.code_tree.clear()
        counts = self._doc_counts(doc_names)
        self._fragments_by_code = self._doc_fragments_by_code(doc_names)

        def add_code_item(name, parent_item=None):
            count = counts.get(name, 0)
            item = QTreeWidgetItem([name, str(count) if count else ""])
            item.setData(0, Qt.UserRole, name)
            if parent_item:
                parent_item.addChild(item)
            else:
                self.code_tree.addTopLevelItem(item)
            for child in self._children.get(name, []):
                if self._should_show_code(child, counts):
                    add_code_item(child, item)
            return item

        for top in self._children.get(None, []):
            if self._should_show_code(top, counts):
                add_code_item(top)

        total_codes = len(counts)
        total_fragments = sum(counts.values())
        self.summary_label.setText(f"Codigos con fragmentos: {total_codes} | Total de fragmentos: {total_fragments}")

    def _on_case_selected(self):
        items = self.doc_list.selectedItems()
        if not items:
            return
        case_name = items[0].text()
        case_docs = self._case_docs(case_name)
        self._load_case_details(case_name)
        self._build_code_tree(case_docs)
        self.fragment_list.clear()

    def _on_characteristics_changed(self):
        if self._loading_case:
            return
        items = self.doc_list.selectedItems()
        if not items:
            return
        case_name = items[0].text()
        entry = self._case_entry(case_name)
        if entry is None:
            return
        entry["characteristics"] = self.characteristics_edit.toPlainText()
        self.updated = True

    def _on_comments_changed(self):
        if self._loading_case:
            return
        items = self.doc_list.selectedItems()
        if not items:
            return
        case_name = items[0].text()
        entry = self._case_entry(case_name)
        if entry is None:
            return
        entry["comments"] = self.comments_edit.toPlainText()
        self.updated = True

    def _on_code_selected(self):
        items = self.code_tree.selectedItems()
        if not items:
            self.fragment_list.clear()
            return
        code_name = items[0].data(0, Qt.UserRole)
        fragments = self._fragments_by_code.get(code_name, [])
        self.fragment_list.clear()
        for frag in fragments:
            text = frag.get("text") or ""
            preview = text.replace("\n", " ").strip()
            if len(preview) > 120:
                preview = preview[:117] + "..."
            label = preview or "(Fragmento)"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, (code_name, frag))
            self.fragment_list.addItem(item)

    def _open_fragment_viewer(self, item):
        payload = item.data(Qt.UserRole)
        if not payload:
            return
        code_name, frag = payload
        doc_name = frag.get("document")
        if not doc_name:
            return
        doc_path = self.project.get_document_path(doc_name)
        parent = self.parent()
        theme = parent._current_theme() if parent and hasattr(parent, "_current_theme") else None
        dark_mode = getattr(parent, "is_dark_mode", False)
        viewer = CodeViewerWindow(
            doc_path,
            self.codes,
            theme=theme,
            dark_mode=dark_mode,
        )
        viewer.select_fragment(code_name, frag)
        viewer.exec()

    def _open_case_setup(self):
        dialog = CaseSetupDialog(self.documents, self.doc_groups, self.case_studies, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return False
        self.case_studies = dialog.get_case_studies()
        self.updated = True
        return True

    def _manage_cases(self):
        if self._open_case_setup():
            self._load_cases()
            self.code_tree.clear()
            self.fragment_list.clear()

    def get_case_studies(self):
        return self.case_studies
