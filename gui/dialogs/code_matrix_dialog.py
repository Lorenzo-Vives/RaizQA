from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
)

from gui.theme import get_theme


class DocumentSelectionDialog(QDialog):
    def __init__(self, documents, selected_documents=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Elegir documentos")
        self.resize(420, 520)
        selected = set(selected_documents or [])

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Selecciona los documentos que entraran en las matrices."))

        actions = QHBoxLayout()
        self.btn_all = QPushButton("Seleccionar todos")
        self.btn_none = QPushButton("Limpiar")
        self.btn_all.clicked.connect(self._select_all)
        self.btn_none.clicked.connect(self._clear_all)
        actions.addWidget(self.btn_all)
        actions.addWidget(self.btn_none)
        actions.addStretch()
        layout.addLayout(actions)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        for doc_name in documents or []:
            item = QListWidgetItem(doc_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if doc_name in selected else Qt.Unchecked)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _select_all(self):
        for idx in range(self.list_widget.count()):
            self.list_widget.item(idx).setCheckState(Qt.Checked)

    def _clear_all(self):
        for idx in range(self.list_widget.count()):
            self.list_widget.item(idx).setCheckState(Qt.Unchecked)

    def selected_documents(self):
        docs = []
        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            if item.checkState() == Qt.Checked:
                docs.append(item.text())
        return docs


class CodeMatrixDialog(QDialog):
    """Code Matrix Browser con presencia, frecuencia, heatmap y relaciones."""

    SCOPE_SINGLE = "Documento seleccionado"
    SCOPE_SELECTED = "Documentos elegidos"
    SCOPE_ALL = "Todos los documentos"

    def __init__(self, documents, codes_dict, current_doc=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Code Matrix Browser")
        self.resize(1160, 720)
        self.documents = list(documents or [])
        self.codes_dict = codes_dict or {}
        self.current_doc = current_doc if current_doc in self.documents else (self.documents[0] if self.documents else None)
        self.selected_documents = [self.current_doc] if self.current_doc else list(self.documents)
        self.is_dark_mode = bool(getattr(parent, "is_dark_mode", False))
        self.theme = get_theme(self.is_dark_mode)

        layout = QVBoxLayout(self)
        layout.addLayout(self._build_controls())

        self.lbl_summary = QLabel("")
        layout.addWidget(self.lbl_summary)

        self.tabs = QTabWidget()
        self.presence_table = self._new_table()
        self.frequency_table = self._new_table()
        self.heatmap_table = self._new_table()
        self.cooccurrence_table = self._new_table()

        self.tabs.addTab(self.presence_table, "Presencia 0/1")
        self.tabs.addTab(self.frequency_table, "Frecuencia")
        self.tabs.addTab(self.heatmap_table, "Heatmap")
        self.tabs.addTab(self.cooccurrence_table, "Co-ocurrencia (aparecen juntos)")
        layout.addWidget(self.tabs, 1)

        self._apply_theme()
        self.build_tables()

    def _build_controls(self):
        controls = QHBoxLayout()

        controls.addWidget(QLabel("Alcance:"))
        self.cbo_scope = QComboBox()
        self.cbo_scope.addItems([self.SCOPE_SINGLE, self.SCOPE_SELECTED, self.SCOPE_ALL])
        self.cbo_scope.currentIndexChanged.connect(self._on_scope_changed)
        controls.addWidget(self.cbo_scope)

        controls.addWidget(QLabel("Documento:"))
        self.cbo_doc = QComboBox()
        for doc_name in self.documents:
            self.cbo_doc.addItem(doc_name)
        if self.current_doc:
            self.cbo_doc.setCurrentText(self.current_doc)
        self.cbo_doc.currentIndexChanged.connect(self.build_tables)
        controls.addWidget(self.cbo_doc, 1)

        self.btn_choose_docs = QPushButton("Elegir documentos")
        self.btn_choose_docs.clicked.connect(self._choose_documents)
        controls.addWidget(self.btn_choose_docs)

        controls.addWidget(QLabel("Escala heatmap:"))
        self.cbo_scale = QComboBox()
        self.cbo_scale.addItems(["Global", "Por fila", "Por columna"])
        self.cbo_scale.currentIndexChanged.connect(self.build_tables)
        controls.addWidget(self.cbo_scale)

        controls.addWidget(QLabel("Ordenar codigos:"))
        self.cbo_sort = QComboBox()
        self.cbo_sort.addItems(["Nombre", "Total descendente"])
        self.cbo_sort.currentIndexChanged.connect(self.build_tables)
        controls.addWidget(self.cbo_sort)

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_refresh.clicked.connect(self.build_tables)
        controls.addWidget(self.btn_refresh)
        controls.addStretch()
        return controls

    def _new_table(self):
        table = QTableWidget()
        table.setAlternatingRowColors(False)
        table.setSortingEnabled(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        return table

    def _apply_theme(self):
        theme = self.theme
        highlight_text = "#0b0b0b" if self.is_dark_mode else "#ffffff"
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {theme['window_bg']};
                color: {theme['text_fg']};
            }}
            QLabel {{
                color: {theme['text_fg']};
            }}
            QComboBox, QPushButton {{
                background-color: {theme['button_bg']};
                color: {theme['button_fg']};
                border: 1px solid {theme['border']};
                border-radius: 6px;
                padding: 6px 10px;
            }}
            QComboBox QAbstractItemView, QListWidget {{
                background-color: {theme['list_bg']};
                color: {theme['list_fg']};
                selection-background-color: {theme['selection']};
                selection-color: {highlight_text};
            }}
            QTabWidget::pane {{
                border: 1px solid {theme['border']};
            }}
            QTabBar::tab {{
                background-color: {theme['panel_bg']};
                color: {theme['text_fg']};
                border: 1px solid {theme['border']};
                padding: 7px 12px;
            }}
            QTabBar::tab:selected {{
                background-color: {theme['text_bg']};
                border-bottom-color: {theme['text_bg']};
            }}
            QTableWidget {{
                background-color: {theme['text_bg']};
                color: {theme['text_fg']};
                border: 1px solid {theme['border']};
                gridline-color: {theme['border']};
            }}
            QHeaderView::section {{
                background-color: {theme['panel_bg']};
                color: {theme['text_fg']};
                border: 1px solid {theme['border']};
                padding: 6px;
                font-weight: 600;
            }}
            """
        )

    def _on_scope_changed(self):
        is_single = self.cbo_scope.currentText() == self.SCOPE_SINGLE
        self.cbo_doc.setEnabled(is_single)
        self.btn_choose_docs.setEnabled(self.cbo_scope.currentText() == self.SCOPE_SELECTED)
        self.build_tables()

    def _choose_documents(self):
        dialog = DocumentSelectionDialog(self.documents, self.selected_documents, self)
        if dialog.exec() != QDialog.Accepted:
            return
        selected = dialog.selected_documents()
        if not selected:
            return
        self.selected_documents = selected
        self.cbo_scope.setCurrentText(self.SCOPE_SELECTED)
        self.build_tables()

    def _active_documents(self):
        scope = self.cbo_scope.currentText()
        if scope == self.SCOPE_ALL:
            return list(self.documents)
        if scope == self.SCOPE_SELECTED:
            return [doc for doc in self.selected_documents if doc in self.documents]
        doc_name = self.cbo_doc.currentText()
        return [doc_name] if doc_name else []

    def build_tables(self):
        active_docs = self._active_documents()
        if not active_docs:
            self.lbl_summary.setText("No hay documentos seleccionados.")
            for table in self._all_tables():
                self._fill_table(table, [], [], [])
            return

        code_rows, doc_cols, frequency = self._frequency_matrix(active_docs)
        presence = [[1 if value > 0 else 0 for value in row] for row in frequency]
        relation_labels, cooccurrence = self._cooccurrence_matrix(active_docs, code_rows)

        self._fill_table(self.presence_table, code_rows, doc_cols, presence, show_zero=True)
        self._fill_table(self.frequency_table, code_rows, doc_cols, frequency, show_zero=True)
        self._fill_table(self.heatmap_table, code_rows, doc_cols, frequency, heatmap=True, show_zero=True)
        self._fill_table(self.cooccurrence_table, relation_labels, relation_labels, cooccurrence, heatmap=True, show_zero=True)
        self._update_summary(active_docs, frequency, presence, cooccurrence)

    def _all_tables(self):
        return [
            self.presence_table,
            self.frequency_table,
            self.heatmap_table,
            self.cooccurrence_table,
        ]

    def _code_names(self):
        names = list(self.codes_dict.keys())
        if self.cbo_sort.currentText() == "Total descendente":
            totals = {name: self._code_total(name) for name in names}
            return sorted(names, key=lambda name: (-totals.get(name, 0), name.lower()))
        return sorted(names, key=lambda name: name.lower())

    def _code_total(self, code_name):
        code_data = self.codes_dict.get(code_name)
        if not code_data:
            return 0
        return sum(len(frags) for frags in code_data.get("fragments", {}).values())

    def _code_by_name(self, code_name):
        return self.codes_dict.get(code_name)

    def _frequency_matrix(self, active_docs):
        counts = {}
        active_set = set(active_docs)
        for code_name, data in self.codes_dict.items():
            for doc_name, frags in data.get("fragments", {}).items():
                if doc_name in active_set:
                    counts[(code_name, doc_name)] = counts.get((code_name, doc_name), 0) + len(frags)

        row_labels = self._code_names()
        matrix = []
        for code_name in row_labels:
            matrix.append([counts.get((code_name, doc_name), 0) for doc_name in active_docs])
        return row_labels, active_docs, matrix

    def _fragments_by_code(self, active_docs, code_rows):
        active_set = set(active_docs)
        by_code = {code_name: [] for code_name in code_rows}
        for code_name, data in self.codes_dict.items():
            if code_name not in by_code:
                continue
            for doc, frags in data.get("fragments", {}).items():
                if doc in active_set:
                    for frag in frags:
                        f_copy = dict(frag)
                        f_copy["document"] = doc
                        f_copy["_code_name"] = code_name
                        f_copy["color"] = data.get("hexcolor", "#fff59d")
                        by_code[code_name].append(f_copy)
        return by_code

    def _cooccurrence_matrix(self, active_docs, code_rows):
        by_code = self._fragments_by_code(active_docs, code_rows)
        doc_sets = {
            code_name: {frag.get("document") for frag in fragments if frag.get("document")}
            for code_name, fragments in by_code.items()
        }
        matrix = []
        for row_code in code_rows:
            row = []
            for col_code in code_rows:
                row.append(len(doc_sets.get(row_code, set()) & doc_sets.get(col_code, set())))
            matrix.append(row)
        return code_rows, matrix

    def _concurrence_matrix(self, active_docs, code_rows):
        by_code = self._fragments_by_code(active_docs, code_rows)
        matrix = []
        for row_code in code_rows:
            row = []
            row_fragments = by_code.get(row_code, [])
            for col_code in code_rows:
                col_fragments = by_code.get(col_code, [])
                if row_code == col_code:
                    row.append(len(row_fragments))
                else:
                    row.append(self._count_overlaps(row_fragments, col_fragments))
            matrix.append(row)
        return code_rows, matrix

    def _count_overlaps(self, left_fragments, right_fragments):
        total = 0
        for left in left_fragments:
            for right in right_fragments:
                if left is right:
                    continue
                if self._fragments_overlap(left, right):
                    total += 1
        return total

    def _fragments_overlap(self, left, right):
        if left.get("document") != right.get("document"):
            return False
        if left.get("type") == "image" or right.get("type") == "image":
            return self._rects_overlap(left.get("rect"), right.get("rect"))
        return self._ranges_overlap(left.get("start"), left.get("end"), right.get("start"), right.get("end"))

    def _ranges_overlap(self, start_a, end_a, start_b, end_b):
        if None in (start_a, end_a, start_b, end_b):
            return False
        try:
            start_a, end_a, start_b, end_b = int(start_a), int(end_a), int(start_b), int(end_b)
        except (TypeError, ValueError):
            return False
        return max(start_a, start_b) < min(end_a, end_b)

    def _rects_overlap(self, rect_a, rect_b):
        if not rect_a or not rect_b:
            return False
        try:
            ax, ay, aw, ah = float(rect_a.get("x", 0)), float(rect_a.get("y", 0)), float(rect_a.get("w", 0)), float(rect_a.get("h", 0))
            bx, by, bw, bh = float(rect_b.get("x", 0)), float(rect_b.get("y", 0)), float(rect_b.get("w", 0)), float(rect_b.get("h", 0))
        except (TypeError, ValueError):
            return False
        if aw <= 0 or ah <= 0 or bw <= 0 or bh <= 0:
            return False
        return max(ax, bx) < min(ax + aw, bx + bw) and max(ay, by) < min(ay + ah, by + bh)

    def _fill_table(self, table, row_labels, col_labels, matrix, heatmap=False, show_zero=False):
        table.clear()
        table.setRowCount(len(row_labels))
        table.setColumnCount(len(col_labels))
        table.setVerticalHeaderLabels(row_labels)
        table.setHorizontalHeaderLabels(col_labels)

        maxima = self._compute_maxima(matrix)
        for row_idx, row_values in enumerate(matrix):
            for col_idx, value in enumerate(row_values):
                text = str(value) if value or show_zero else ""
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if heatmap:
                    color = self._heat_color(value, maxima, row_idx, col_idx)
                    item.setBackground(QBrush(color))
                    item.setForeground(QBrush(self._contrast_color(color)))
                table.setItem(row_idx, col_idx, item)

        table.resizeColumnsToContents()
        table.resizeRowsToContents()

    def _compute_maxima(self, matrix):
        if not matrix:
            return {"global": 0, "rows": [], "cols": []}
        row_max = [max(row) if row else 0 for row in matrix]
        col_count = len(matrix[0]) if matrix and matrix[0] else 0
        col_max = [
            max(matrix[row_idx][col_idx] for row_idx in range(len(matrix)))
            for col_idx in range(col_count)
        ]
        return {"global": max(row_max) if row_max else 0, "rows": row_max, "cols": col_max}

    def _heat_color(self, value, maxima, row_idx, col_idx):
        theme = self.theme
        if value <= 0:
            return QColor(theme["text_bg"])

        scale_mode = self.cbo_scale.currentText()
        if scale_mode == "Por fila":
            denom = maxima["rows"][row_idx] if row_idx < len(maxima["rows"]) else 0
        elif scale_mode == "Por columna":
            denom = maxima["cols"][col_idx] if col_idx < len(maxima["cols"]) else 0
        else:
            denom = maxima["global"]

        ratio = value / denom if denom else 0
        ratio = max(0.0, min(1.0, ratio))
        base = QColor(theme["text_bg"])
        low = QColor("#d6f0ff" if not self.is_dark_mode else "#173247")
        high = QColor("#d62828" if not self.is_dark_mode else "#ff8f3d")
        if ratio < 0.5:
            return self._blend(base, low, ratio * 2)
        return self._blend(low, high, (ratio - 0.5) * 2)

    def _blend(self, first, second, weight):
        weight = max(0.0, min(1.0, weight))
        inv = 1.0 - weight
        return QColor(
            int(first.red() * inv + second.red() * weight),
            int(first.green() * inv + second.green() * weight),
            int(first.blue() * inv + second.blue() * weight),
        )

    def _contrast_color(self, background):
        brightness = (background.red() * 299 + background.green() * 587 + background.blue() * 114) / 1000
        return QColor("#111111" if brightness > 155 else "#f5f5f5")

    def _update_summary(self, active_docs, frequency, presence, cooccurrence):
        total_freq = sum(sum(row) for row in frequency)
        active_cells = sum(1 for row in presence for value in row if value)
        co_total = self._upper_triangle_sum(cooccurrence)
        chosen = ", ".join(active_docs[:3])
        if len(active_docs) > 3:
            chosen += f" (+{len(active_docs) - 3})"
        self.lbl_summary.setText(
            f"Documentos: {len(active_docs)} [{chosen}] | Codigos: {len(frequency)} | "
            f"Fragmentos codificados: {total_freq} | Presencias: {active_cells} | "
            f"Co-ocurrencias: {co_total}"
        )

    def _upper_triangle_sum(self, matrix):
        total = 0
        for row_idx, row in enumerate(matrix):
            for col_idx, value in enumerate(row):
                if col_idx > row_idx:
                    total += value
        return total
