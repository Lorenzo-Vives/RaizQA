import os
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QLabel,
    QTextEdit,
    QSplitter,
)
from PySide6.QtGui import QTextCursor, QTextCharFormat, QColor
from PySide6.QtCore import Qt


class CompareDialog(QDialog):
    """Visor lado a lado para comparar dos documentos y navegar coincidencias de códigos."""

    def __init__(self, project, codes_dict, left_doc=None, right_doc=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Comparar documentos")
        self.resize(1100, 650)
        self.project = project
        self.codes_dict = codes_dict or {}
        self.doc_left = left_doc
        self.doc_right = right_doc
        self.matches = []
        self.match_index = -1

        layout = QVBoxLayout(self)

        # Controles superiores
        top = QHBoxLayout()
        top.addWidget(QLabel("Documento A:"))
        self.cbo_left = QComboBox()
        self.cbo_left.currentTextChanged.connect(self.load_left)
        top.addWidget(self.cbo_left, 1)

        top.addSpacing(8)
        top.addWidget(QLabel("Documento B:"))
        self.cbo_right = QComboBox()
        self.cbo_right.currentTextChanged.connect(self.load_right)
        top.addWidget(self.cbo_right, 1)

        top.addSpacing(12)
        top.addWidget(QLabel("Código:"))
        self.cbo_code = QComboBox()
        self.cbo_code.currentTextChanged.connect(self.recompute_matches)
        top.addWidget(self.cbo_code, 1)

        self.btn_prev = QPushButton("Anterior")
        self.btn_prev.clicked.connect(self.prev_match)
        top.addWidget(self.btn_prev)

        self.btn_next = QPushButton("Siguiente")
        self.btn_next.clicked.connect(self.next_match)
        top.addWidget(self.btn_next)

        self.lbl_status = QLabel("0/0")
        top.addWidget(self.lbl_status)

        layout.addLayout(top)

        # Área de texto
        splitter = QSplitter(Qt.Horizontal)
        self.left_view = QTextEdit()
        self.left_view.setReadOnly(True)
        self.right_view = QTextEdit()
        self.right_view.setReadOnly(True)
        splitter.addWidget(self.left_view)
        splitter.addWidget(self.right_view)
        splitter.setSizes([550, 550])
        layout.addWidget(splitter, 1)

        self._populate_docs()
        self.load_left(self.doc_left)
        self.load_right(self.doc_right)
        self._populate_code_filter()
        self.recompute_matches()

    def _populate_docs(self):
        docs = []
        try:
            docs = sorted(self.project.list_documents())
        except Exception:
            docs = []
        self.cbo_left.addItems(docs)
        self.cbo_right.addItems(docs)
        if self.doc_left and self.doc_left in docs:
            self.cbo_left.setCurrentText(self.doc_left)
        if self.doc_right and self.doc_right in docs:
            self.cbo_right.setCurrentText(self.doc_right)
        elif len(docs) > 1 and not self.doc_right:
            self.cbo_right.setCurrentIndex(1)

    def _populate_code_filter(self):
        codes = sorted(self.codes_dict.keys())
        self.cbo_code.clear()
        self.cbo_code.addItem("(Todos)", "")
        for name in codes:
            self.cbo_code.addItem(name, name)

    def load_left(self, doc_name):
        self.doc_left = doc_name
        self._load_doc_to_view(self.left_view, doc_name)
        self.recompute_matches()

    def load_right(self, doc_name):
        self.doc_right = doc_name
        self._load_doc_to_view(self.right_view, doc_name)
        self.recompute_matches()

    def _load_doc_to_view(self, view, doc_name):
        if not doc_name:
            view.clear()
            return
        try:
            text = self.project.read_document(doc_name)
        except Exception:
            text = ""
        view.setPlainText(text)
        fragments = self._fragments_for_doc(doc_name)
        self._apply_fragments(view, fragments)

    def _fragments_for_doc(self, doc_name):
        frags = []
        for code_name, data in self.codes_dict.items():
            for frag in data.get("fragments", {}).get(doc_name, []):
                f_copy = dict(frag)
                f_copy["color"] = data.get("hexcolor", "#fff59d")
                f_copy["_code_name"] = code_name
                f_copy["document"] = doc_name
                frags.append(f_copy)
        return frags

    def _apply_fragments(self, view, fragments):
        cursor = view.textCursor()
        cursor.select(QTextCursor.Document)
        fmt_clear = QTextCharFormat()
        fmt_clear.setBackground(Qt.transparent)
        cursor.mergeCharFormat(fmt_clear)
        cursor.clearSelection()

        text = view.toPlainText()
        for frag in fragments:
            start = frag.get("start")
            end = frag.get("end")
            if start is None or end is None or start == end:
                snippet = frag.get("text", "")
                if snippet:
                    pos = text.find(snippet)
                    if pos != -1:
                        start = pos
                        end = pos + len(snippet)
            if start is None or end is None or end > len(text):
                continue
            color = QColor(frag.get("color", "#fff59d"))
            fmt = QTextCharFormat()
            fmt.setBackground(color)
            c = view.textCursor()
            c.setPosition(start)
            c.setPosition(end, QTextCursor.KeepAnchor)
            c.mergeCharFormat(fmt)

    def recompute_matches(self):
        self.matches = []
        self.match_index = -1
        if not self.doc_left or not self.doc_right:
            self._update_status()
            return

        code_filter = self.cbo_code.currentData()
        frags_left = self._fragments_for_doc(self.doc_left)
        frags_right = self._fragments_for_doc(self.doc_right)
        codes_left = {}
        for f in frags_left:
            codes_left.setdefault(f["_code_name"], []).append(f)
        codes_right = {}
        for f in frags_right:
            codes_right.setdefault(f["_code_name"], []).append(f)

        common = set(codes_left.keys()) & set(codes_right.keys())
        if code_filter:
            common = {c for c in common if c == code_filter}

        for code in sorted(common):
            left_list = codes_left.get(code, [])
            right_list = codes_right.get(code, [])
            limit = min(len(left_list), len(right_list))
            for idx in range(limit):
                self.matches.append({
                    "code": code,
                    "left": left_list[idx],
                    "right": right_list[idx],
                })

        self._update_status()
        if self.matches:
            self.match_index = 0
            self._go_to_match(self.matches[0])

    def _update_status(self):
        total = len(self.matches)
        current = self.match_index + 1 if self.match_index >= 0 else 0
        self.lbl_status.setText(f"{current}/{total}")

    def next_match(self):
        if not self.matches:
            return
        self.match_index = (self.match_index + 1) % len(self.matches)
        self._go_to_match(self.matches[self.match_index])

    def prev_match(self):
        if not self.matches:
            return
        self.match_index = (self.match_index - 1) % len(self.matches)
        self._go_to_match(self.matches[self.match_index])

    def _go_to_match(self, match):
        left = match.get("left")
        right = match.get("right")
        if left:
            self._select_range(self.left_view, left.get("start"), left.get("end"))
        if right:
            self._select_range(self.right_view, right.get("start"), right.get("end"))
        self._update_status()

    def _select_range(self, view, start, end):
        if start is None or end is None:
            return
        cursor = view.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        view.setTextCursor(cursor)
        view.ensureCursorVisible()
