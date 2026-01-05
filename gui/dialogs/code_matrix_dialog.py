from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QTableWidget, QTableWidgetItem, QPushButton
from PySide6.QtCore import Qt


class CodeMatrixDialog(QDialog):
    """Matriz Documento x Código mostrando frecuencias de fragmentos."""

    def __init__(self, documents, codes, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Code Matrix Browser")
        self.resize(900, 600)
        self.documents = documents
        self.codes = codes or []

        layout = QVBoxLayout(self)

        # Filtros mínimos
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Documento:"))
        self.cbo_doc = QComboBox()
        self.cbo_doc.addItem("(Todos)")
        for d in documents:
            self.cbo_doc.addItem(d)
        self.cbo_doc.currentIndexChanged.connect(self.build_table)
        filter_row.addWidget(self.cbo_doc)

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_refresh.clicked.connect(self.build_table)
        filter_row.addWidget(self.btn_refresh)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.documents))
        self.table.setRowCount(len(self.codes))
        layout.addWidget(self.table)

        self.build_table()

    def build_table(self):
        docs_filter = self.cbo_doc.currentText()
        active_docs = self.documents if docs_filter == "(Todos)" else [docs_filter]

        self.table.setRowCount(len(self.codes))
        self.table.setColumnCount(len(active_docs))
        self.table.setVerticalHeaderLabels([c.get("name", "") for c in self.codes])
        self.table.setHorizontalHeaderLabels(active_docs)

        # Precalcular conteos por (code, doc)
        counts = {}
        for code in self.codes:
            code_name = code.get("name")
            for frag in code.get("fragments", []):
                doc = frag.get("document")
                if doc in active_docs:
                    counts.setdefault((code_name, doc), 0)
                    counts[(code_name, doc)] += 1

        for r, code in enumerate(self.codes):
            name = code.get("name")
            for c, doc in enumerate(active_docs):
                val = counts.get((name, doc), 0)
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, item)

        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
