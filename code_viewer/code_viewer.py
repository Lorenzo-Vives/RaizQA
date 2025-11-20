import os
import random
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QSplitter, QTextEdit, QListWidget,
    QListWidgetItem, QLabel, QWidget, QHBoxLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from gui.theme import get_theme


class CodeViewerWindow(QDialog):
    """
    Ventana para visualizar los fragmentos codificados.
    Parte superior: visor de texto con encabezado de color y nombre del código (con jerarquía si aplica).
    Parte inferior: lista de códigos con formato tipo tabla: Documento | Código | Fragmento.
    """

    def __init__(self, document_path, codes, theme=None, dark_mode=False):
        super().__init__()
        self.setWindowTitle("Visor de Códigos y Fragmentos")
        self.resize(900, 600)
        self.document_path = document_path
        self.codes = codes
        self.is_dark_mode = dark_mode
        self.theme = theme or get_theme(dark_mode)

        # --- Layout general ---
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)

        # ------------------------------------------------------------------
        #  PARTE SUPERIOR: visor de texto y encabezado de color
        # ------------------------------------------------------------------
        self.viewer_container = QWidget()
        viewer_layout = QVBoxLayout(self.viewer_container)
        viewer_layout.setContentsMargins(0, 0, 0, 0)

        # Encabezado color + texto
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(35)
        self.header_label = QLabel("Selecciona un fragmento...")
        self.header_label.setAlignment(Qt.AlignCenter)

        header_layout = QVBoxLayout(self.header_widget)
        header_layout.addWidget(self.header_label)
        header_layout.setContentsMargins(0, 0, 0, 0)

        viewer_layout.addWidget(self.header_widget)

        # Cuadro de texto
        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setPlaceholderText("Selecciona un fragmento para visualizarlo aquí...")
        viewer_layout.addWidget(self.text_view)

        splitter.addWidget(self.viewer_container)

        # ------------------------------------------------------------------
        #  PARTE INFERIOR: lista de códigos + encabezado tipo tabla
        # ------------------------------------------------------------------
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        # Encabezado visual
        self.list_header_label = QLabel("📄 Documento | 🏷️ Código | ✂️ Fragmento")
        bottom_layout.addWidget(self.list_header_label)

        # Lista de códigos
        self.code_list = QListWidget()
        self.code_list.itemSelectionChanged.connect(self.on_code_selected)
        bottom_layout.addWidget(self.code_list)

        splitter.addWidget(bottom_container)

        # ------------------------------------------------------------------
        # Configuración de colores y carga de lista
        # ------------------------------------------------------------------
        self.apply_theme()
        self.code_colors = self._assign_colors_to_codes()
        self.populate_code_list()

    def apply_theme(self):
        theme = self.theme
        highlight_text = "#0b0b0b" if self.is_dark_mode else "#ffffff"

        self.setStyleSheet(f"background-color: {theme['window_bg']}; color: {theme['text_fg']};")
        self.viewer_container.setStyleSheet(f"background-color: {theme['panel_bg']};")
        self._reset_header_style()

        self.text_view.setStyleSheet(
            f"background-color: {theme['text_bg']}; color: {theme['text_fg']}; font-size: 14px; "
            f"padding: 10px; border: 1px solid {theme['border']}; "
            f"selection-background-color: {theme['selection']}; selection-color: {highlight_text};"
        )

        self.list_header_label.setStyleSheet(
            f"font-weight: bold; color: {theme['text_fg']}; background-color: {theme['panel_bg']}; "
            f"padding: 6px 10px; border-bottom: 1px solid {theme['border']};"
        )

        self.code_list.setStyleSheet(
            f"""
            QListWidget {{
                background-color: {theme['list_bg']};
                color: {theme['list_fg']};
                border: none;
            }}
            QListWidget::item {{
                padding: 5px;
                border-bottom: 1px solid {theme['border']};
            }}
            QListWidget::item:selected {{
                background-color: {theme['selection']};
                color: {highlight_text};
            }}
            """
        )

    def _reset_header_style(self):
        theme = self.theme
        self.header_widget.setStyleSheet(
            f"background-color: {theme['panel_bg']}; border-bottom: 1px solid {theme['border']};"
        )
        self.header_label.setStyleSheet(
            f"font-weight: bold; font-size: 13px; color: {theme['text_fg']};"
        )

    # ============================================================
    # MÉTODOS AUXILIARES
    # ============================================================
    def _assign_colors_to_codes(self):
        """Asigna un color basado en la configuración del código."""
        color_map = {}
        for code in self.codes:
            color_hex = code.get("color")
            if color_hex:
                color_map[code["name"]] = QColor(color_hex)
            else:
                rgb = (random.randint(70, 190), random.randint(70, 190), random.randint(70, 190))
                color_map[code["name"]] = QColor(*rgb)
        return color_map

    # ------------------------------------------------------------------
    def populate_code_list(self):
        """Rellena la lista con los códigos y fragmentos (alineados en columnas)."""
        self.code_list.clear()
        theme = self.theme

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

                # --- Widget personalizado tipo fila ---
                item_widget = QWidget()
                row_layout = QHBoxLayout(item_widget)
                row_layout.setContentsMargins(10, 0, 10, 0)
                row_layout.setSpacing(15)

                # Documento
                doc_label = QLabel(f"📄 {doc_name}")
                doc_label.setFixedWidth(180)
                doc_label.setStyleSheet(f"color: {theme['text_fg']}; font-weight: 500;")
                doc_label.setToolTip(doc_name)
                row_layout.addWidget(doc_label)

                # Código
                code_label = QLabel(f"🏷️ {code_name}")
                code_label.setFixedWidth(180)
                code_label.setStyleSheet(f"color: {theme['text_fg']};")
                code_label.setToolTip(code_name)
                row_layout.addWidget(code_label)

                # Fragmento
                frag_label = QLabel(f"✂️ {preview}")
                frag_label.setWordWrap(True)
                frag_label.setStyleSheet(f"color: {theme['muted_text']};")
                row_layout.addWidget(frag_label, stretch=1)

                # Crear ítem en lista
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
            self._reset_header_style()
            self.header_label.setText("Selecciona un fragmento...")
            return

        item = items[0]
        code, frag = item.data(Qt.UserRole)
        text = frag.get("text", "")
        self.text_view.clear()
        self.text_view.setPlainText(text)

        # Color según el código
        color = self.code_colors.get(code["name"], QColor(100, 100, 150))
        self.header_widget.setStyleSheet(
            f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); "
            f"border-bottom: 1px solid {self.theme['border']};"
        )
        self.header_label.setStyleSheet("font-weight: bold; font-size: 13px; color: white;")

        # Mostrar jerarquía si la hay
        if code.get("parent"):
            self.header_label.setText(f"{code['parent']} → {code['name']}")
        else:
            self.header_label.setText(code["name"])
