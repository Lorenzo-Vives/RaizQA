from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from gui.theme import get_theme


class CodeMatrixDialog(QDialog):
    """Matriz Documento x Codigo con modo tabla y heatmap."""

    def __init__(self, documents, codes, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Code Matrix Browser")
        self.resize(980, 640)
        self.documents = documents or []
        self.codes = codes or []
        self.is_dark_mode = bool(getattr(parent, "is_dark_mode", False))
        self.theme = get_theme(self.is_dark_mode)

        layout = QVBoxLayout(self)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Documento:"))
        self.cbo_doc = QComboBox()
        self.cbo_doc.addItem("(Todos)")
        for doc_name in self.documents:
            self.cbo_doc.addItem(doc_name)
        self.cbo_doc.currentIndexChanged.connect(self.build_table)
        filter_row.addWidget(self.cbo_doc)

        filter_row.addWidget(QLabel("Vista:"))
        self.cbo_view = QComboBox()
        self.cbo_view.addItems(["Tabla + Heatmap", "Heatmap", "Tabla"])
        self.cbo_view.currentIndexChanged.connect(self.build_table)
        filter_row.addWidget(self.cbo_view)

        filter_row.addWidget(QLabel("Escala:"))
        self.cbo_scale = QComboBox()
        self.cbo_scale.addItems(["Global", "Por fila", "Por documento"])
        self.cbo_scale.currentIndexChanged.connect(self.build_table)
        filter_row.addWidget(self.cbo_scale)

        filter_row.addWidget(QLabel("Ordenar:"))
        self.cbo_sort = QComboBox()
        self.cbo_sort.addItems(["Nombre", "Total descendente"])
        self.cbo_sort.currentIndexChanged.connect(self.build_table)
        filter_row.addWidget(self.cbo_sort)

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_refresh.clicked.connect(self.build_table)
        filter_row.addWidget(self.btn_refresh)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self.lbl_summary = QLabel("")
        layout.addWidget(self.lbl_summary)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(False)
        self.table.setSortingEnabled(False)
        layout.addWidget(self.table)

        self._apply_theme()
        self.build_table()

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
            QComboBox QAbstractItemView {{
                background-color: {theme['list_bg']};
                color: {theme['list_fg']};
                selection-background-color: {theme['selection']};
                selection-color: {highlight_text};
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

    def build_table(self):
        row_labels, col_labels, matrix = self._compute_matrix()
        self.table.clear()
        self.table.setRowCount(len(row_labels))
        self.table.setColumnCount(len(col_labels))
        self.table.setVerticalHeaderLabels(row_labels)
        self.table.setHorizontalHeaderLabels(col_labels)

        maxima = self._compute_maxima(matrix)
        view_mode = self.cbo_view.currentText()

        for row_idx, row_values in enumerate(matrix):
            for col_idx, value in enumerate(row_values):
                item = QTableWidgetItem("" if value == 0 and view_mode == "Heatmap" else str(value) if value else "")
                item.setTextAlignment(Qt.AlignCenter)
                if view_mode != "Tabla":
                    color = self._heat_color(value, maxima, row_idx, col_idx)
                    item.setBackground(QBrush(color))
                    item.setForeground(QBrush(self._contrast_color(color)))
                self.table.setItem(row_idx, col_idx, item)

        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        self._update_summary(matrix, row_labels, col_labels)

    def _compute_matrix(self):
        docs_filter = self.cbo_doc.currentText()
        active_docs = self.documents if docs_filter == "(Todos)" else [docs_filter]

        counts = {}
        for code in self.codes:
            code_name = code.get("name", "")
            for frag in code.get("fragments", []):
                doc_name = frag.get("document")
                if doc_name in active_docs:
                    counts[(code_name, doc_name)] = counts.get((code_name, doc_name), 0) + 1

        rows = []
        for code in self.codes:
            code_name = code.get("name", "")
            total = sum(counts.get((code_name, doc_name), 0) for doc_name in active_docs)
            rows.append((code_name, total))

        if self.cbo_sort.currentText() == "Total descendente":
            rows.sort(key=lambda entry: (-entry[1], entry[0].lower()))
        else:
            rows.sort(key=lambda entry: entry[0].lower())

        row_labels = [name for name, _ in rows]
        matrix = []
        for code_name in row_labels:
            matrix.append([counts.get((code_name, doc_name), 0) for doc_name in active_docs])

        return row_labels, active_docs, matrix

    def _compute_maxima(self, matrix):
        if not matrix:
            return {"global": 0, "rows": [], "cols": []}
        row_max = [max(row) if row else 0 for row in matrix]
        col_max = []
        col_count = len(matrix[0]) if matrix and matrix[0] else 0
        for col_idx in range(col_count):
            col_max.append(max(matrix[row_idx][col_idx] for row_idx in range(len(matrix))) if matrix else 0)
        global_max = max(row_max) if row_max else 0
        return {"global": global_max, "rows": row_max, "cols": col_max}

    def _heat_color(self, value, maxima, row_idx, col_idx):
        theme = self.theme
        if value <= 0:
            return QColor(theme["text_bg"])

        scale_mode = self.cbo_scale.currentText()
        if scale_mode == "Por fila":
            denom = maxima["rows"][row_idx] if row_idx < len(maxima["rows"]) else 0
        elif scale_mode == "Por documento":
            denom = maxima["cols"][col_idx] if col_idx < len(maxima["cols"]) else 0
        else:
            denom = maxima["global"]

        ratio = value / denom if denom else 0
        ratio = max(0.0, min(1.0, ratio))

        base = QColor(theme["text_bg"])
        accent = QColor(theme["selection"])
        if self.is_dark_mode:
            low = self._blend(base, accent, 0.18)
            high = self._blend(base, accent, 0.9)
        else:
            low = self._blend(base, accent, 0.12)
            high = self._blend(base, accent, 0.82)
        return self._blend(low, high, ratio)

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

    def _update_summary(self, matrix, row_labels, col_labels):
        total_cells = len(row_labels) * len(col_labels)
        total_hits = sum(sum(row) for row in matrix)
        non_zero = sum(1 for row in matrix for value in row if value > 0)
        self.lbl_summary.setText(
            f"Codigos: {len(row_labels)} | Documentos: {len(col_labels)} | "
            f"Fragmentos: {total_hits} | Celdas activas: {non_zero}/{total_cells if total_cells else 0}"
        )
