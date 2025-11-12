import os
import random
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QSplitter, QTextEdit, QListWidget,
    QListWidgetItem, QLabel, QWidget, QHBoxLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont


class CodeViewerWindow(QDialog):
    """
    Ventana para visualizar los fragmentos codificados.
    Parte superior: visor de texto con encabezado de color y nombre del código (con jerarquía si aplica).
    Parte inferior: lista de códigos con formato tipo tabla: 📄 Documento | 🧩 Código | ✂️ Fragmento.
    """

    def __init__(self, document_path, codes):
        super().__init__()
        self.setWindowTitle("Visor de Códigos y Fragmentos")
        self.resize(900, 600)
        self.document_path = document_path
        self.codes = codes

        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)

        # --- Contenedor del visor superior ---
        self.viewer_container = QWidget()
        viewer_layout = QVBoxLayout(self.viewer_container)
        viewer_layout.setContentsMargins(0, 0, 0, 0)

        # 🔹 Encabezado de color + nombre del código (más pequeño)
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(35)
        self.header_label = QLabel("Selecciona un fragmento...")
        self.header_label.setAlignment(Qt.AlignCenter)
        self.header_label.setStyleSheet("font-weight: bold; font-size: 13px; color: white;")
        header_layout = QVBoxLayout(self.header_widget)
        header_layout.addWidget(self.header_label)
        header_layout.setContentsMargins(0, 0, 0, 0)
        viewer_layout.addWidget(self.header_widget)

        # 🔹 Visor de texto (blanco)
        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setStyleSheet(
            "background-color: white; color: black; font-size: 14px; padding: 10px;"
        )
        self.text_view.setPlaceholderText("Selecciona un fragmento para visualizarlo aquí...")
        viewer_layout.addWidget(self.text_view)

        splitter.addWidget(self.viewer_container)

        # --- Zona inferior: lista de códigos y fragmentos ---
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        # 🔹 Encabezado visual tipo tabla
        header_label = QLabel("📄 Documento | 🧩 Código | ✂️ Fragmento")
        header_label.setStyleSheet(
            "font-weight: bold; color: #333; background-color: #f0f0f0; "
            "padding: 6px 10px; border-bottom: 1px solid #ccc;"
        )
        bottom_layout.addWidget(header_label)

        # 🔹 Lista de códigos
        self.code_list = QListWidget()
        self.code_list.itemSelectionChanged.connect(self.on_code_selected)
        self.code_list.setStyleSheet("""
            QListWidget {
                background-color: #fafafa;
                border: none;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #cce5ff;
                color: black;
            }
        """)
        bottom_layout.addWidget(self.code_list)

        splitter.addWidget(bottom_container)

        # Colores para cada código
        self.code_colors = self._assign_colors_to_codes()
        self.populate_code_list()

    # ------------------------------------------------------------------
    def _assign_colors_to_codes(self):
        """Asigna un color aleatorio a cada código."""
        color_map = {}
        for code in self.codes:
            rgb = (random.randint(70, 190), random.randint(70, 190), random.randint(70, 190))
            color_map[code["name"]] = QColor(*rgb)
        return color_map

    # ------------------------------------------------------------------
    def populate_code_list(self):
        """Rellena la lista con los códigos y fragmentos (alineados en columnas)."""
        self.code_list.clear()

        for code in self.codes:
            fragments = code.get("fragments", [])
            if not fragments:
                continue

            for frag in fragments:
                preview = frag["text"].strip().replace("\n", " ")
                if len(preview) > 100:
                    preview = preview[:100] + "..."

                # --- Datos base ---
                code_name = code["name"]
                doc_name = os.path.basename(frag.get("document", self.document_path))

                # --- Widget personalizado ---
                item_widget = QWidget()
                row_layout = QHBoxLayout(item_widget)
                row_layout.setContentsMargins(10, 0, 10, 0)
                row_layout.setSpacing(15)

                # Documento (ancho fijo)
                doc_label = QLabel(f"📄 {doc_name}")
                doc_label.setFixedWidth(180)
                doc_label.setStyleSheet("color: #333; font-weight: 500;")
                doc_label.setToolTip(doc_name)
                row_layout.addWidget(doc_label)

                # Código (ancho fijo)
                code_label = QLabel(f"🧩 {code_name}")
                code_label.setFixedWidth(180)
                code_label.setStyleSheet("color: #333;")
                code_label.setToolTip(code_name)
                row_layout.addWidget(code_label)

                # Fragmento (expandible)
                frag_label = QLabel(f"✂️ {preview}")
                frag_label.setWordWrap(True)
                frag_label.setStyleSheet("color: #555;")
                row_layout.addWidget(frag_label, stretch=1)

                item = QListWidgetItem()
                item.setSizeHint(item_widget.sizeHint())
                item.setData(Qt.UserRole, (code, frag))
                self.code_list.addItem(item)
                self.code_list.setItemWidget(item, item_widget)

    # ------------------------------------------------------------------
    def on_code_selected(self):
        """Muestra el fragmento del código seleccionado con encabezado de color."""
        items = self.code_list.selectedItems()
        if not items:
            self.text_view.clear()
            self.header_widget.setStyleSheet("background-color: #444;")
            self.header_label.setText("Selecciona un fragmento...")
            return

        item = items[0]
        code, frag = item.data(Qt.UserRole)
        text = frag.get("text", "")
        self.text_view.clear()
        self.text_view.setPlainText(text)

        # 🔹 Encabezado con color del código
        color = self.code_colors.get(code["name"], QColor(100, 100, 150))
        self.header_widget.setStyleSheet(
            f"background-color: rgb({color.red()}, {color.green()}, {color.blue()});"
        )

        # 🔹 Mostrar jerarquía solo arriba
        if code.get("parent"):
            self.header_label.setText(f"{code['parent']} → {code['name']}")
        else:
            self.header_label.setText(code["name"])
