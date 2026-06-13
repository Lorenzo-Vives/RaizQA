from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QListWidget,
    QListWidgetItem,
    QSplitter,
)

from gui.dialogs.code_viewer_window import CodeViewerWindow


class ThemesAnalysisDialog(QDialog):
    def __init__(self, codes_dict, themes, project, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Analisis de temas")
        self.resize(720, 420)
        self.codes_dict = codes_dict or {}
        self.themes = themes or []
        self.project = project
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Resumen de temas y categorias con frecuencia de fragmentos."))
        splitter = QSplitter()
        splitter.setOrientation(Qt.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Tema / Codigo", "Codigos", "Fragmentos"])
        self.tree.setColumnWidth(1, 90)
        self.tree.setColumnWidth(2, 90)
        self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        splitter.addWidget(self.tree)

        right_panel = QVBoxLayout()
        right_label = QLabel("Fragmentos del codigo seleccionado")
        self.fragment_list = QListWidget()
        self.fragment_list.itemClicked.connect(self._open_fragment_viewer)
        right_panel.addWidget(right_label)
        right_panel.addWidget(self.fragment_list, 1)
        right_wrapper = QDialog()
        right_wrapper.setLayout(right_panel)
        splitter.addWidget(right_wrapper)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, 1)

    def _code_stats(self):
        stats = {}
        for code_name, data in self.codes_dict.items():
            stats[code_name] = sum(len(frags) for frags in data.get("fragments", {}).values())
        return stats

    def _code_fragments(self):
        frags = {}
        for code_name, data in self.codes_dict.items():
            flat_frags = []
            for doc, doc_frags in data.get("fragments", {}).items():
                for f in doc_frags:
                    f_copy = dict(f)
                    f_copy["document"] = doc
                    f_copy["color"] = data.get("hexcolor", "#fff59d")
                    f_copy["type"] = "text"
                    flat_frags.append(f_copy)
            frags[code_name] = flat_frags
        return frags

    def _load_data(self):
        self.tree.clear()
        stats = self._code_stats()
        self._fragments = self._code_fragments()
        for theme in self.themes:
            name = theme.get("name")
            code_list = theme.get("codes") or []
            if not name:
                continue
            code_count = len(code_list)
            fragment_total = sum(stats.get(c, 0) for c in code_list)
            theme_item = QTreeWidgetItem([name, str(code_count), str(fragment_total)])
            theme_item.setData(0, Qt.UserRole, "theme")
            self.tree.addTopLevelItem(theme_item)
            for code_name in code_list:
                count = stats.get(code_name, 0)
                code_item = QTreeWidgetItem([code_name, "", str(count)])
                code_item.setData(0, Qt.UserRole, "code")
                theme_item.addChild(code_item)
            theme_item.setExpanded(True)

    def _on_tree_selection_changed(self):
        items = self.tree.selectedItems()
        if not items:
            self.fragment_list.clear()
            return
        item = items[0]
        if item.data(0, Qt.UserRole) != "code":
            self.fragment_list.clear()
            return
        code_name = item.text(0)
        fragments = self._fragments.get(code_name, [])
        self.fragment_list.clear()
        for frag in fragments:
            doc = frag.get("document") or ""
            text = frag.get("text") or ""
            preview = text.replace("\n", " ").strip()
            if len(preview) > 120:
                preview = preview[:117] + "..."
            label = f"{doc} | {preview}" if doc else preview
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, (code_name, frag))
            self.fragment_list.addItem(item)

    def _open_fragment_viewer(self, item):
        payload = item.data(Qt.UserRole)
        if not payload:
            return
        code_name, frag = payload
        doc_name = frag.get("document")
        if not doc_name or not self.project:
            return
        doc_path = self.project.get_document_path(doc_name)
        parent = self.parent()
        theme = parent._current_theme() if parent and hasattr(parent, "_current_theme") else None
        dark_mode = getattr(parent, "is_dark_mode", False)
        viewer = CodeViewerWindow(
            doc_path,
            self.codes_dict,
            theme=theme,
            dark_mode=dark_mode,
        )
        viewer.select_fragment(code_name, frag)
        viewer.exec()
