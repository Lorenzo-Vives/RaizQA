import os
import random
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QSplitter, QTextEdit, QListWidget,
    QListWidgetItem, QLabel, QWidget, QHBoxLayout, QStackedWidget, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from gui.image_viewer import ImageDocumentViewer
from gui.theme import get_theme


class CodeViewerWindow(QDialog):
    """
    Ventana para visualizar los fragmentos codificados.
    Parte superior: visor de texto con encabezado de color y nombre del código (con jerarquía si aplica).
    Parte inferior: lista de códigos con formato tipo tabla: Documento | Código | Fragmento.
    """
    IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff")

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
        self.image_view = ImageDocumentViewer(self, read_only=True)
        self.viewer_stack = QStackedWidget()
        self.viewer_stack.addWidget(self.text_view)
        self.viewer_stack.addWidget(self.image_view)
        viewer_layout.addWidget(self.viewer_stack)

        splitter.addWidget(self.viewer_container)

        # ------------------------------------------------------------------
        #  PARTE INFERIOR: lista de códigos + encabezado tipo tabla
        # ------------------------------------------------------------------
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        search_row = QHBoxLayout()
        self.code_search_field = QLineEdit()
        self.code_search_field.setPlaceholderText("Buscar código por nombre")
        self.code_search_field.textChanged.connect(self.filter_code_list_by_name)
        self.search_count_label = QLabel("")
        self.search_count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        search_row.addWidget(self.code_search_field, 1)
        search_row.addWidget(self.search_count_label)
        bottom_layout.addLayout(search_row)

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
        self.image_view.apply_theme(theme)

        self.list_header_label.setStyleSheet(
            f"font-weight: bold; color: {theme['text_fg']}; background-color: {theme['panel_bg']}; "
            f"padding: 6px 10px; border-bottom: 1px solid {theme['border']};"
        )

        self.code_search_field.setStyleSheet(
            f"background-color: {theme['text_bg']}; color: {theme['text_fg']}; "
            f"border: 1px solid {theme['border']}; padding: 6px 8px;"
        )
        self.search_count_label.setStyleSheet(
            f"color: {theme['muted_text']}; font-size: 12px; padding-right: 6px;"
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
                preview_source = frag.get("comment") or frag.get("text") or ""
                preview = preview_source.strip().replace("\n", " ")
                if not preview and frag.get("type") == "image":
                    rect = frag.get("rect") or {}
                    if rect:
                        preview = f"(Zona {rect.get('x', 0)},{rect.get('y', 0)} {rect.get('w', 0)}x{rect.get('h', 0)})"
                    else:
                        preview = "(Imagen)"
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
                hint = item_widget.sizeHint()
                hint.setHeight(max(hint.height(), 60))
                item.setSizeHint(hint)
                item.setData(Qt.UserRole, (code, frag))
                self.code_list.addItem(item)
                self.code_list.setItemWidget(item, item_widget)

        self.filter_code_list_by_name(self.code_search_field.text())

    def filter_code_list_by_name(self, text):
        """Filtra la lista solo por nombre de código, no por contenido de fragmentos."""
        term = (text or "").strip().lower()
        visible_count = 0

        for idx in range(self.code_list.count()):
            item = self.code_list.item(idx)
            data = item.data(Qt.UserRole)
            code = data[0] if data else {}
            code_name = (code.get("name", "") if isinstance(code, dict) else "").lower()
            matches = not term or term in code_name
            item.setHidden(not matches)
            if matches:
                visible_count += 1

        current_item = self.code_list.currentItem()
        if current_item and current_item.isHidden():
            self.code_list.clearSelection()
            self.on_code_selected()

        if not term:
            self.search_count_label.setText(f"{visible_count} resultados")
        elif visible_count == 1:
            self.search_count_label.setText("1 coincidencia")
        else:
            self.search_count_label.setText(f"{visible_count} coincidencias")

    # ------------------------------------------------------------------
    def on_code_selected(self):
        """Muestra el fragmento del c?digo seleccionado con encabezado de color."""
        items = self.code_list.selectedItems()
        if not items:
            self.text_view.clear()
            self.viewer_stack.setCurrentWidget(self.text_view)
            self._reset_header_style()
            self.header_label.setText("Selecciona un fragmento...")
            return

        item = items[0]
        code, frag = item.data(Qt.UserRole)
        text = frag.get("text", "")
        self.text_view.clear()

        doc_name = frag.get("document") or os.path.basename(self.document_path)
        is_image = frag.get("type") == "image" or (doc_name and doc_name.lower().endswith(self.IMAGE_EXTENSIONS))
        if is_image:
            img_path = os.path.join(os.path.dirname(self.document_path), doc_name)
            if os.path.exists(img_path) and self.image_view.load_image(img_path):
                self.viewer_stack.setCurrentWidget(self.image_view)
                self.image_view.set_fragments([frag], active_fragment=frag)
                self.image_view.focus_fragment(frag)
            else:
                self.viewer_stack.setCurrentWidget(self.text_view)
                self.text_view.setHtml(f"<p style='color:{self.theme['muted_text']};'>Imagen no encontrada: {doc_name}</p>")
        else:
            self.viewer_stack.setCurrentWidget(self.text_view)
            self.text_view.setPlainText(text)

        # Color seg?n el c?digo
        color = self.code_colors.get(code["name"], QColor(100, 100, 150))
        self.header_widget.setStyleSheet(
            f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); "
            f"border-bottom: 1px solid {self.theme['border']};"
        )
        self.header_label.setStyleSheet("font-weight: bold; font-size: 13px; color: white;")

        # Mostrar jerarqu?a si la hay
        if code.get("parent"):
            self.header_label.setText(f"{code['parent']} ? {code['name']}")
        else:
            self.header_label.setText(code["name"])

    def select_fragment(self, code_name, fragment):
        """Selecciona un fragmento en la lista si existe y lo muestra."""
        if not code_name or not fragment:
            return
        target_doc = fragment.get("document")
        target_start = fragment.get("start")
        target_end = fragment.get("end")
        target_text = fragment.get("text")
        for idx in range(self.code_list.count()):
            item = self.code_list.item(idx)
            data = item.data(Qt.UserRole)
            if not data:
                continue
            code, frag = data
            if code.get("name") != code_name:
                continue
            if target_doc and frag.get("document") != target_doc:
                continue
            if target_start is not None and target_end is not None:
                if frag.get("start") == target_start and frag.get("end") == target_end:
                    self.code_list.setCurrentItem(item)
                    return
            if target_text and frag.get("text") == target_text:
                self.code_list.setCurrentItem(item)
                return

