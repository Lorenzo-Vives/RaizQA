import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QTextEdit, QFileDialog, QMessageBox, QInputDialog,
    QTreeWidget, QTreeWidgetItem, QMenu, QDialog, QHeaderView, QTreeWidgetItemIterator,
    QGridLayout, QDialogButtonBox, QFileIconProvider, QAbstractItemView
)
from PySide6.QtGui import QColor, QTextCursor, QTextCharFormat, QPainter, QPixmap, QIcon, QPalette
from PySide6.QtCore import Qt, QTimer, QPoint, QEvent

from gui.dialogs.memo_dialog import MemoDialog
from gui.dialogs.fragments_dialog import CodeFragmentsDialog
from gui.dialogs.diary_dialog import DiaryDialog
from gui.document_tree import DocumentTree
from gui.code_tree import CodeTree
from code_viewer.code_viewer import CodeViewerWindow  # Absolute import desde root
from core.project import Project
from gui.theme import get_theme

class RaizQAGUI(QMainWindow):
    AUTO_SAVE_INTERVAL = 30000
    COLOR_PALETTE = [
        ("Amarillo", "#ffcc00"),
        ("Coral", "#ff7043"),
        ("Turquesa", "#4db6ac"),
        ("Lavanda", "#9575cd"),
        ("Celeste", "#64b5f6"),
        ("Rosa", "#f48fb1"),
        ("Verde", "#aed581"),
        ("Naranja", "#ffab40"),
        ("Gris", "#90a4ae"),
        ("Rojo", "#ff6f61"),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RaizQA 🌱")
        self.setGeometry(100, 100, 1000, 600)

        self.current_project = None
        self.memo_manager = None
        self.working_dir = None
        self.current_doc = None
        self.codes = []
        self.highlights = {}        # todos los subrayados por documento
        self.highlighted = []       # subrayados del documento actual
        self._color_index = 0
        self.doc_groups = {"__root__": []}
        self.is_dark_mode = False
        self.icon_provider = QFileIconProvider()
        self._column_selecting = False
        self._column_start = None  # (line, col)
        self._prev_extra_selections = []

        # -------------------- LAYOUT PRINCIPAL --------------------
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        top_container = QVBoxLayout()
        top_row = QHBoxLayout()
        bottom_row = QHBoxLayout()
        middle_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # -------------------- TOP --------------------
        self.btn_working_dir = QPushButton("Seleccionar Working Directory")
        self.btn_working_dir.clicked.connect(self.select_working_dir)
        top_row.addWidget(self.btn_working_dir)

        self.btn_create = QPushButton("Crear Proyecto")
        self.btn_create.clicked.connect(self.create_project)
        top_row.addWidget(self.btn_create)

        self.btn_open = QPushButton("Abrir Proyecto")
        self.btn_open.clicked.connect(self.open_project)
        top_row.addWidget(self.btn_open)

        self.btn_import_doc = QPushButton("Importar Archivo")
        self.btn_import_doc.clicked.connect(self.import_file)
        top_row.addWidget(self.btn_import_doc)

        self.btn_save = QPushButton("💾 Guardar Proyecto")
        self.btn_save.clicked.connect(self.save_project)
        top_row.addWidget(self.btn_save)

        self.btn_view_codes = QPushButton("📚 Ver Códigos")
        self.btn_view_codes.clicked.connect(self.open_code_viewer)
        top_row.addWidget(self.btn_view_codes)

        self.btn_toggle_theme = QPushButton("Modo oscuro")
        self.btn_toggle_theme.clicked.connect(self.toggle_theme)
        top_row.addWidget(self.btn_toggle_theme)

        top_row.addStretch()
        self.lbl_project = QLabel("Proyecto: Ninguno")
        top_row.addWidget(self.lbl_project)
        top_container.addLayout(top_row)

        self.btn_diary = QPushButton("📓 Diario de codificación")
        self.btn_diary.clicked.connect(self.open_diary)
        bottom_row.addWidget(self.btn_diary)
        bottom_row.addStretch()
        top_container.addLayout(bottom_row)

        main_layout.addLayout(top_container)

        # -------------------- MIDDLE --------------------
        left_layout = QVBoxLayout()
        docs_header = QHBoxLayout()
        docs_header.setContentsMargins(0, 0, 0, 0)
        docs_header.addWidget(QLabel("Documentos importados"))
        self.btn_new_folder = QPushButton("📁")
        self.btn_new_folder.setToolTip("Crear carpeta de documentos")
        self.btn_new_folder.setFixedWidth(36)
        self.btn_new_folder.clicked.connect(self.create_document_folder)
        docs_header.addWidget(self.btn_new_folder)
        docs_header.addStretch()
        left_layout.addLayout(docs_header)

        self.doc_tree = DocumentTree(drop_callback=self._on_doc_tree_drop)
        self.doc_tree.setHeaderLabels(["Documentos"])
        self.doc_tree.currentItemChanged.connect(self.display_document)
        self.doc_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.doc_tree.customContextMenuRequested.connect(self.doc_tree_context_menu)
        self.doc_tree.setDragEnabled(True)
        self.doc_tree.setAcceptDrops(True)
        self.doc_tree.setDropIndicatorShown(True)
        self.doc_tree.setDefaultDropAction(Qt.MoveAction)
        left_layout.addWidget(self.doc_tree, 50)

        self.code_tree = CodeTree(drop_callback=self._on_code_tree_drop)
        self.code_tree.setHeaderLabels(["Código", "n", "Memo"])
        header = self.code_tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.code_tree.setDragEnabled(True)
        self.code_tree.setAcceptDrops(True)
        self.code_tree.setDropIndicatorShown(True)
        self.code_tree.setDefaultDropAction(Qt.MoveAction)
        left_layout.addWidget(QLabel("Árbol de Códigos"))
        left_layout.addWidget(self.code_tree, 50)

        # Eventos
        self.code_tree.itemClicked.connect(self.show_code_fragments)
        self.code_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.code_tree.customContextMenuRequested.connect(self.code_tree_context_menu)

        middle_layout.addLayout(left_layout, 40)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_area.customContextMenuRequested.connect(self.text_context_menu)
        self.text_area.installEventFilter(self)
        middle_layout.addWidget(self.text_area, 60)
        main_layout.addLayout(middle_layout)

        self.lbl_working_dir = QLabel("WD: Ninguno")
        self.lbl_working_dir.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_working_dir.setStyleSheet("font-size:10px; color: gray; margin-top:-10px;")
        main_layout.addWidget(self.lbl_working_dir)

        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(self.AUTO_SAVE_INTERVAL)

        self.apply_theme()

    # -------------------- TEMA --------------------
    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

    def _current_theme(self):
        return get_theme(self.is_dark_mode)

    def apply_theme(self):
        theme = self._current_theme()
        highlight_text = "#0b0b0b" if self.is_dark_mode else "#ffffff"

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(theme["window_bg"]))
        palette.setColor(QPalette.Base, QColor(theme["text_bg"]))
        palette.setColor(QPalette.AlternateBase, QColor(theme["panel_bg"]))
        palette.setColor(QPalette.Text, QColor(theme["text_fg"]))
        palette.setColor(QPalette.Button, QColor(theme["button_bg"]))
        palette.setColor(QPalette.ButtonText, QColor(theme["button_fg"]))
        palette.setColor(QPalette.Highlight, QColor(theme["selection"]))
        palette.setColor(QPalette.HighlightedText, QColor(highlight_text))

        app = QApplication.instance()
        if app:
            app.setPalette(palette)
        self.setPalette(palette)

        if hasattr(self, "btn_toggle_theme"):
            self.btn_toggle_theme.setText("Modo claro" if self.is_dark_mode else "Modo oscuro")

        base_styles = f"""
            QMainWindow {{
                background-color: {theme['window_bg']};
                color: {theme['text_fg']};
            }}
            QLabel {{
                color: {theme['text_fg']};
            }}
            QPushButton {{
                background-color: {theme['button_bg']};
                color: {theme['button_fg']};
                border: 1px solid {theme['border']};
                padding: 6px 10px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {theme['selection']};
                color: {highlight_text};
            }}
        """
        self.setStyleSheet(base_styles)

        self.text_area.setStyleSheet(
            f"background-color: {theme['text_bg']}; color: {theme['text_fg']}; "
            f"border: 1px solid {theme['border']}; padding: 8px; "
            f"selection-background-color: {theme['selection']}; selection-color: {highlight_text};"
        )

        self.doc_tree.setStyleSheet(
            f"""
            QTreeWidget {{
                background-color: {theme['tree_bg']};
                color: {theme['tree_fg']};
                border: 1px solid {theme['border']};
            }}
            QTreeWidget::item:selected {{
                background-color: {theme['selection']};
                color: {highlight_text};
            }}
            """
        )

        self.code_tree.setStyleSheet(
            f"""
            QTreeWidget {{
                background-color: {theme['tree_bg']};
                color: {theme['tree_fg']};
                border: 1px solid {theme['border']};
            }}
            QTreeWidget::item:selected {{
                background-color: {theme['selection']};
                color: {highlight_text};
            }}
            """
        )

        self.lbl_working_dir.setStyleSheet(
            f"font-size: 10px; color: {theme['muted_text']}; margin-top: -10px;"
        )

        self.lbl_project.setStyleSheet(f"color: {theme['text_fg']}; font-weight: bold;")

        self._refresh_code_tree_colors()
        self.restore_highlights()
        self._apply_column_selection_style()

    # -------------------- MEMOS --------------------
    def code_tree_context_menu(self, pos):
        if not self.current_project or not self.memo_manager:
            return

        item = self.code_tree.itemAt(pos)
        if not item:
            return

        code_name = self._code_item_name(item)
        menu = QMenu()

        view_memo_action = menu.addAction("👁️ Ver memo")
        add_memo_action = menu.addAction("📝 Agregar / editar memo")
        delete_memo_action = menu.addAction("❌ Eliminar memo")

        action = menu.exec(self.code_tree.viewport().mapToGlobal(pos))
        if action == view_memo_action:
            self.view_memo(code_name)
        elif action == add_memo_action:
            self.add_or_edit_memo(code_name)
        elif action == delete_memo_action:
            self.delete_memo(code_name)

    def view_memo(self, code_name):
        if not self.memo_manager:
            return

        memo_text = self.memo_manager.get_memo(code_name)
        if not memo_text.strip():
            QMessageBox.information(self, "Sin memo", f"El código '{code_name}' no tiene memo asociado.")
            return

        dialog = MemoDialog(code_name, memo_text)
        dialog.exec()

    def add_or_edit_memo(self, code_name):
        if not self.memo_manager:
            return

        memo_text = self.memo_manager.get_memo(code_name)
        dialog = MemoDialog(code_name, memo_text)
        if dialog.exec() == QDialog.Accepted:
            new_text = dialog.get_memo()
            self.memo_manager.add_or_update_memo(code_name, new_text)
            self.update_memo_icon(code_name, has_memo=bool(new_text.strip()))
            QMessageBox.information(self, "Memo guardado", f"Memo actualizado para '{code_name}'.")

    def delete_memo(self, code_name):
        if not self.memo_manager:
            return
        self.memo_manager.delete_memo(code_name)
        self.update_memo_icon(code_name, has_memo=False)

    # -------------------- DIARIO --------------------
    def open_diary(self):
        if not self.current_project:
            QMessageBox.information(self, "Diario", "Abre o crea un proyecto para usar el diario.")
            return

        try:
            diary_text = self.current_project.load_diary()
        except Exception as exc:
            QMessageBox.critical(self, "Diario", f"No se pudo cargar el diario:\n{exc}")
            diary_text = ""

        dialog = DiaryDialog(diary_text, parent=self)
        if dialog.exec() == QDialog.Accepted:
            new_text = dialog.get_text()
            try:
                self.current_project.save_diary(new_text)
                QMessageBox.information(self, "Diario", "Diario guardado correctamente.")
            except Exception as exc:
                QMessageBox.critical(self, "Diario", f"No se pudo guardar el diario:\n{exc}")

    # -------------------- FUNCIONES NUEVAS --------------------
    def show_code_fragments(self, item, column):
        code_name = self._code_item_name(item)
        code = next((c for c in self.codes if c["name"] == code_name), None)
        if code and "fragments" in code:
            dialog = CodeFragmentsDialog(code_name, code["fragments"])
            dialog.exec()

    # -------------------- FUNCIONES BÁSICAS --------------------
    def select_working_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Selecciona Working Directory")
        if dir_path:
            self.working_dir = dir_path
            self.lbl_working_dir.setText(f"WD: {dir_path}")

    def create_project(self):
        if not self.working_dir:
            QMessageBox.warning(self, "Crear Proyecto", "Primero selecciona el Working Directory.")
            return
        name, ok = QInputDialog.getText(self, "Crear Proyecto", "Nombre del nuevo proyecto:")
        if ok and name:
            self.current_project = Project(name, self.working_dir)
            self.memo_manager = self.current_project.memo_manager
            self.reset_project_state()
            self.lbl_project.setText(f"Proyecto: {name}")
            QMessageBox.information(self, "Proyecto creado", f"Proyecto '{name}' creado exitosamente.")
            self.save_project()

    def open_project(self):
        if not self.working_dir:
            QMessageBox.warning(self, "Abrir Proyecto", "Primero selecciona el Working Directory.")
            return
        projects = [d for d in os.listdir(self.working_dir) if os.path.isdir(os.path.join(self.working_dir, d))]
        if not projects:
            QMessageBox.warning(self, "Abrir Proyecto", "No se encontraron proyectos.")
            return
        selected, ok = QInputDialog.getItem(self, "Abrir Proyecto", "Selecciona proyecto:", projects, 0, False)
        if ok and selected:
            self.current_project = Project(selected, self.working_dir)
            self.memo_manager = self.current_project.memo_manager
            self.lbl_project.setText(f"Proyecto: {self.current_project.name}")
            self.reset_project_state()
            self.load_project()
            QMessageBox.information(self, "Proyecto abierto", f"Proyecto '{self.current_project.name}' abierto.")

    def reset_project_state(self):
        """Reinicia colecciones y widgets al cambiar de proyecto."""
        self.codes = []
        self.highlights = {}
        self.highlighted = []
        self.current_doc = None
        self._color_index = 0
        self.doc_groups = {"__root__": []}
        self.doc_tree.clear()
        self.code_tree.clear()
        self.text_area.clear()
        self._clear_column_selection()

    def save_project(self):
        if not self.current_project:
            return
        self._rebuild_doc_groups_from_tree()
        self._rebuild_codes_from_tree()
        documents = self._all_documents()
        self.current_project.save_state(self.codes, documents, self.highlights, self.doc_groups)


    def auto_save(self):
        self.save_project()

    def load_project(self):
        if not self.current_project:
            return

        data = self.current_project.load_state()

        self.codes = data.get("codes", [])
        self.highlights = data.get("highlights", {})
        self.ensure_code_colors()

        self.code_tree.clear()
        self.doc_tree.clear()
        self.doc_groups = data.get("doc_groups")
        if not self.doc_groups:
            documents = data.get("documents") or self.current_project.list_documents()
            self.doc_groups = {"__root__": documents}
        self._populate_doc_tree()

        for c in self.codes:
            parent_item = self.find_tree_item(c.get("parent")) if c.get("parent") else None
            code_item = QTreeWidgetItem([c["name"], str(c.get("count", 0)), ""])
            code_item.setData(0, Qt.UserRole + 1, c["name"])
            self._configure_code_item(code_item)
            if parent_item:
                parent_item.addChild(code_item)
            else:
                self.code_tree.addTopLevelItem(code_item)
            self.apply_code_item_color(code_item, c.get("color", "#fff59d"))

        # Sincronizar jerarquía de padres con el árbol actual (por si hubo drag & drop previo)
        self._rebuild_codes_from_tree()

        if self.memo_manager:
            for code_name, memo_text in self.memo_manager.memos.items():
                if memo_text.strip():
                    self.update_memo_icon(code_name, True)

        self._color_index = max(self._color_index, len(self.codes))

    def ensure_code_colors(self):
        for code in self.codes:
            if not code.get("color"):
                code["color"] = self.next_palette_color()

    def _populate_doc_tree(self):
        self.doc_tree.clear()
        first_doc = None
        for folder, docs in self.doc_groups.items():
            parent = None
            if folder != "__root__":
                parent = self._ensure_folder_item(folder)
            for doc in docs:
                item = self._add_doc_item(doc, parent)
                if first_doc is None:
                    first_doc = item
        if first_doc and not self.current_doc:
            self.doc_tree.setCurrentItem(first_doc)

    def _all_documents(self):
        docs = []
        for doc_list in self.doc_groups.values():
            docs.extend(doc_list)
        return docs

    def _rebuild_doc_groups_from_tree(self):
        groups = {"__root__": []}
        for i in range(self.doc_tree.topLevelItemCount()):
            item = self.doc_tree.topLevelItem(i)
            item_type = item.data(0, Qt.UserRole)
            if item_type == "folder":
                folder_name = item.text(0)
                groups[folder_name] = []
                for j in range(item.childCount()):
                    child = item.child(j)
                    if child.data(0, Qt.UserRole) == "doc":
                        groups[folder_name].append(child.text(0))
            elif item_type == "doc":
                groups["__root__"].append(item.text(0))
        self.doc_groups = groups

    def _on_doc_tree_drop(self):
        self._rebuild_doc_groups_from_tree()
        self.save_project()

    def _set_folder_icon(self, item):
        try:
            item.setIcon(0, self.icon_provider.icon(QFileIconProvider.Folder))
        except Exception:
            pass

    def _set_doc_icon(self, item):
        try:
            item.setIcon(0, self.icon_provider.icon(QFileIconProvider.File))
        except Exception:
            pass

    def _ensure_folder_item(self, name):
        for i in range(self.doc_tree.topLevelItemCount()):
            item = self.doc_tree.topLevelItem(i)
            if item.data(0, Qt.UserRole) == "folder" and item.text(0) == name:
                return item
        folder_item = QTreeWidgetItem([name])
        folder_item.setData(0, Qt.UserRole, "folder")
        flags = folder_item.flags()
        folder_item.setFlags(flags | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        folder_item.setExpanded(True)
        self._set_folder_icon(folder_item)
        self.doc_tree.addTopLevelItem(folder_item)
        return folder_item

    def _add_doc_item(self, name, parent=None):
        item = QTreeWidgetItem([name])
        item.setData(0, Qt.UserRole, "doc")
        flags = item.flags()
        item.setFlags(flags | Qt.ItemIsDragEnabled | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        self._set_doc_icon(item)
        if parent:
            parent.addChild(item)
        else:
            self.doc_tree.addTopLevelItem(item)
        return item

    def _find_folder_item(self, name):
        if not name or name == "__root__":
            return None
        for i in range(self.doc_tree.topLevelItemCount()):
            item = self.doc_tree.topLevelItem(i)
            if item.data(0, Qt.UserRole) == "folder" and item.text(0) == name:
                return item
        return None

    def _current_folder_name(self):
        item = self.doc_tree.currentItem()
        if item and item.data(0, Qt.UserRole) == "folder":
            return item.text(0)
        if item and item.data(0, Qt.UserRole) == "doc":
            parent = item.parent()
            if parent and parent.data(0, Qt.UserRole) == "folder":
                return parent.text(0)
        return "__root__"

    def _rebuild_codes_from_tree(self):
        for idx in range(self.code_tree.topLevelItemCount()):
            self._update_code_parent_recursive(self.code_tree.topLevelItem(idx), None)

    def _update_code_parent_recursive(self, item, parent_name):
        if not item:
            return
        code_name = self._code_item_name(item)
        code_data = self.get_code_data(code_name)
        if code_data:
            code_data["parent"] = parent_name
        for i in range(item.childCount()):
            self._update_code_parent_recursive(item.child(i), code_name)

    def _configure_code_item(self, item):
        flags = item.flags()
        item.setFlags(flags | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled | Qt.ItemIsEnabled | Qt.ItemIsSelectable)

    def _code_item_name(self, item):
        stored = item.data(0, Qt.UserRole + 1)
        if stored:
            return stored
        return item.text(0).strip()

    # -------------------- SELECCIÓN COLUMNAR EN TEXTO --------------------
    def eventFilter(self, obj, event):
        if obj is self.text_area:
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier):
                    self._start_column_selection(event.pos())
                    return True
            elif event.type() == QEvent.MouseMove:
                if self._column_selecting:
                    self._update_column_selection(event.pos())
                    return True
            elif event.type() in (QEvent.MouseButtonRelease, QEvent.Leave):
                if self._column_selecting:
                    self._update_column_selection(event.pos() if hasattr(event, "pos") else QPoint())
                    self._column_selecting = False
                    return True
        return super().eventFilter(obj, event)

    def _start_column_selection(self, pos):
        cursor = self.text_area.cursorForPosition(pos)
        block = cursor.block()
        self._column_selecting = True
        self._column_start = (block.blockNumber(), cursor.positionInBlock())
        self._prev_extra_selections = self.text_area.extraSelections()
        self._update_column_selection(pos)

    def _update_column_selection(self, pos):
        if not self._column_selecting or not self._column_start:
            return
        cursor = self.text_area.cursorForPosition(pos)
        current_block = cursor.block()
        current_pos_in_block = cursor.positionInBlock()

        start_line, start_col = self._column_start
        end_line = current_block.blockNumber()
        end_col = current_pos_in_block

        first_line = min(start_line, end_line)
        last_line = max(start_line, end_line)
        col_left = min(start_col, end_col)
        col_right = max(start_col, end_col)

        doc = self.text_area.document()
        selections = []

        fmt = QTextCharFormat()
        selection_color = QColor(self._current_theme()["selection"])
        selection_color.setAlpha(160)
        fmt.setBackground(selection_color)
        fmt.setForeground(QColor(self._current_theme()["text_fg"]))

        for line in range(first_line, last_line + 1):
            block = doc.findBlockByNumber(line)
            if not block.isValid():
                continue
            text = block.text()
            start_idx = min(col_left, len(text))
            end_idx = min(col_right, len(text))
            if start_idx == end_idx and col_right != col_left:
                end_idx = start_idx
            selection = QTextEdit.ExtraSelection()
            c = QTextCursor(block)
            c.setPosition(block.position() + start_idx)
            c.setPosition(block.position() + end_idx, QTextCursor.KeepAnchor)
            selection.cursor = c
            selection.format = fmt
            selections.append(selection)

        self.text_area.setExtraSelections(self._prev_extra_selections + selections)

    def _clear_column_selection(self):
        if self._column_selecting:
            self._column_selecting = False
        if self._prev_extra_selections:
            self.text_area.setExtraSelections(self._prev_extra_selections)
        else:
            self.text_area.setExtraSelections([])
        self._prev_extra_selections = []

    def _apply_column_selection_style(self):
        if not self._prev_extra_selections:
            return
        self.text_area.setExtraSelections(self._prev_extra_selections)

    def _on_code_tree_drop(self):
        self._rebuild_codes_from_tree()
        self.save_project()


    # -------------------- IMPORTAR ARCHIVO --------------------
    def import_file(self):
        if not self.current_project:
            QMessageBox.warning(self, "Importar archivo", "Primero crea o abre un proyecto.")
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", "", "Documentos (*.txt *.pdf *.docx)")
        if not file_path:
            return

        try:
            file_name, text = self.current_project.import_document(file_path)
        except ValueError as err:
            QMessageBox.warning(self, "Importar archivo", str(err))
            return
        except Exception as err:
            QMessageBox.critical(self, "Importar archivo", f"No se pudo procesar el archivo:\n{err}")
            return

        existing = self._all_documents()
        folder = self._current_folder_name()
        if file_name not in existing:
            self.doc_groups.setdefault(folder, []).append(file_name)
            new_item = self._add_doc_item(file_name, self._find_folder_item(folder))
            self.doc_tree.setCurrentItem(new_item)

        self.text_area.setPlainText(text)
        self.current_doc = file_name
        self._rebuild_doc_groups_from_tree()
        self.save_project()
        QMessageBox.information(self, "Importar", f"✅ Documento '{file_name}' importado correctamente.")

    # -------------------- DOCUMENTO --------------------
    def display_document(self, current, previous=None):
        if not current or current.data(0, Qt.UserRole) != "doc":
            return

        #  1. Guardar los subrayados del documento anterior
        if self.current_doc is not None:
            self.save_current_highlights()

        #  2. Actualizar el documento actual
        self.current_doc = current.text(0)
        if self.current_project:
            text = self.current_project.read_document(self.current_doc)
            self.text_area.setPlainText(text)
        else:
            self.text_area.clear()

        #  3. Restaurar los subrayados del documento nuevo
        self.highlighted = self.highlights.get(self.current_doc, []).copy()
        for frag in self.highlighted:
            if not frag.get("color"):
                frag["color"] = self._get_code_color(frag)
        self.restore_highlights()

    # -------------------- CARPETAS / DOCUMENTOS --------------------
    def doc_tree_context_menu(self, pos):
        menu = QMenu(self)
        add_folder_action = menu.addAction("Nueva carpeta")

        selected_item = self.doc_tree.itemAt(pos)
        move_action = None
        if selected_item and selected_item.data(0, Qt.UserRole) == "doc":
            move_action = menu.addAction("Mover a carpeta…")

        action = menu.exec(self.doc_tree.viewport().mapToGlobal(pos))
        if action == add_folder_action:
            self.create_document_folder()
        elif action == move_action:
            self.move_document_to_folder(selected_item)

    def create_document_folder(self):
        name, ok = QInputDialog.getText(self, "Nueva carpeta", "Nombre de la carpeta:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in self.doc_groups:
            QMessageBox.information(self, "Carpeta", "Ya existe una carpeta con ese nombre.")
            return
        self.doc_groups[name] = []
        folder_item = self._ensure_folder_item(name)
        self.doc_tree.setCurrentItem(folder_item)
        self._rebuild_doc_groups_from_tree()
        self.save_project()

    def move_document_to_folder(self, doc_item):
        if not doc_item or doc_item.data(0, Qt.UserRole) != "doc":
            return

        folders = [k for k in self.doc_groups.keys() if k != "__root__"]
        options = ["(Sin carpeta)"] + folders
        target, ok = QInputDialog.getItem(self, "Mover documento", "Selecciona carpeta destino:", options, 0, False)
        if not ok:
            return

        doc_name = doc_item.text(0)
        self._remove_doc_from_groups(doc_name)
        if target != "(Sin carpeta)":
            self.doc_groups.setdefault(target, []).append(doc_name)
            parent_item = self._ensure_folder_item(target)
        else:
            parent_item = None

        # quitar de árbol actual
        if doc_item.parent():
            doc_item.parent().removeChild(doc_item)
        else:
            idx = self.doc_tree.indexOfTopLevelItem(doc_item)
            if idx >= 0:
                self.doc_tree.takeTopLevelItem(idx)

        if parent_item:
            parent_item.addChild(doc_item)
            parent_item.setExpanded(True)
        else:
            self.doc_tree.addTopLevelItem(doc_item)

        self.doc_tree.setCurrentItem(doc_item)
        self._rebuild_doc_groups_from_tree()
        self.save_project()

    def _remove_doc_from_groups(self, name):
        for folder, docs in self.doc_groups.items():
            if name in docs:
                docs.remove(name)
                break


    # -------------------- FUNCIONES DE DOCUMENTO --------------------
    def open_document(self, file_path):
        if not self.current_project:
            return

        # Guardar subrayados del documento actual
        if self.current_doc:
            self.save_current_highlights()
    
        self.current_doc = os.path.basename(file_path)
        text = self.current_project.read_document(self.current_doc)
        self.text_area.setPlainText(text)
    
        #  Cargar solo los fragmentos del documento actual
        self.highlighted = []
        for c in self.codes:
            for frag in c.get("fragments", []):
                if frag.get("document") == self.current_doc:
                    if not frag.get("color"):
                        frag["color"] = c.get("color", "#fff59d")
                    self.highlighted.append(frag)
                
        self.restore_highlights()


    # -------------------- CÓDIGOS --------------------
    def text_context_menu(self, pos):
        cursor = self.text_area.textCursor()
        selected_text = cursor.selectedText()
        selection_start = cursor.selectionStart()
        selection_end = cursor.selectionEnd()
        self._clear_column_selection()
        menu = QMenu()

        if selected_text and selection_start != selection_end and self.current_doc:
            create_code_action = menu.addAction("➕ Crear nuevo código")
            create_subcode_action = menu.addAction("↳ Crear subcódigo")

            if self.codes:
                add_to_existing = menu.addMenu("📌 Agregar a código existente")
                for c in self.codes:
                    act = add_to_existing.addAction(c["name"])
                    act.triggered.connect(
                        lambda checked=False, name=c["name"], text=selected_text,
                        start=selection_start, end=selection_end:
                        self.add_to_existing_code(name, text, start, end)
                    )

            action = menu.exec(self.text_area.mapToGlobal(pos))
            if action == create_code_action:
                self.create_new_code(selected_text, selection_start, selection_end)
            elif action == create_subcode_action:
                self.create_subcode(selected_text, selection_start, selection_end)
        else:
            menu.exec(self.text_area.mapToGlobal(pos))

    def create_new_code(self, selected_text, start, end, parent_item=None, code_label=None):
        if not self.current_doc:
            QMessageBox.warning(self, "Nuevo código", "Selecciona un documento antes de codificar.")
            return
        if start is None or end is None or start == end:
            return

        if not code_label:
            code_label, ok = QInputDialog.getText(self, "Nuevo Código", "Nombre del código:")
            if not ok or not code_label:
                return

        parent_name = self._code_item_name(parent_item) if parent_item else None
        parent_color = None
        if parent_name:
            parent_data = self.get_code_data(parent_name)
            parent_color = parent_data.get("color") if parent_data else None

        suggested_color = parent_color or self.next_palette_color()
        color_hex = self.ask_color_from_palette(suggested_color)

        fragment = {
            "text": selected_text,
            "document": self.current_doc,
            "start": start,
            "end": end,
            "color": color_hex
        }

        code_item = QTreeWidgetItem([code_label, "1", ""])
        code_item.setData(0, Qt.UserRole + 1, code_label)
        self._configure_code_item(code_item)
        if parent_item:
            parent_item.addChild(code_item)
            parent_item.setExpanded(True)
        else:
            self.code_tree.addTopLevelItem(code_item)
        self.apply_code_item_color(code_item, color_hex)

        self.codes.append({
            "name": code_label,
            "parent": parent_name,
            "memo": "",
            "color": color_hex,
            "count": 1,
            "fragments": [fragment]
        })

        self.highlight_fragment(fragment, QColor(color_hex))
        self.save_current_highlights()
        self._rebuild_codes_from_tree()
        self.save_project()

    def add_to_existing_code(self, code_name, selected_text, start, end):
        if not self.current_doc:
            return

        code_data = self.get_code_data(code_name)
        if not code_data:
            return

        color_hex = code_data.get("color", "#fff59d")
        fragment = {
            "text": selected_text,
            "document": self.current_doc,
            "start": start,
            "end": end,
            "color": color_hex
        }

        code_data.setdefault("fragments", []).append(fragment)
        code_data["count"] = len(code_data["fragments"])
        self.update_code_count(code_name, code_data["count"])
        self.highlight_fragment(fragment, QColor(color_hex))
        self.save_current_highlights()
        self.save_project()

    def highlight_fragment(self, fragment, color=None):
        """Resalta un fragmento solo en su documento correspondiente."""
        if fragment.get("document") != self.current_doc:
            return

        start_pos = fragment.get("start")
        end_pos = fragment.get("end")

        if start_pos is None or end_pos is None or start_pos == end_pos:
            start_pos, end_pos = self._resolve_fragment_positions(fragment)

        doc_text = self.text_area.toPlainText()
        if start_pos is None or end_pos is None or end_pos > len(doc_text):
            return

        color_code = fragment.get("color")
        if not color_code:
            color_code = self._get_code_color(fragment)
            fragment["color"] = color_code

        cursor = self.text_area.textCursor()
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        chosen_color = color or QColor(color_code)
        self.highlight_selection(cursor, chosen_color)
        self._clear_column_selection()

    def _adjust_highlight_color(self, color):
        """Ajusta el color del subrayado según el tema activo."""
        qcolor = QColor(color) if isinstance(color, QColor) else QColor(str(color))
        if self.is_dark_mode:
            base = QColor(self._current_theme()["text_bg"])
            qcolor = self._blend_colors(qcolor, base, 0.45)
            qcolor.setAlpha(220)
        else:
            qcolor = qcolor.lighter(110)
            qcolor.setAlpha(255)
        return qcolor

    def _blend_colors(self, primary, secondary, weight):
        """Mezcla dos QColor según un peso (0..1) para suavizar tonos."""
        weight = max(0.0, min(1.0, weight))
        inv = 1.0 - weight
        r = int(primary.red() * weight + secondary.red() * inv)
        g = int(primary.green() * weight + secondary.green() * inv)
        b = int(primary.blue() * weight + secondary.blue() * inv)
        return QColor(r, g, b)

    def _resolve_fragment_positions(self, fragment):
        """Obtiene posiciones por texto si no existen offsets persistidos."""
        snippet = fragment.get("text", "")
        if not snippet:
            return None, None
        doc_text = self.text_area.toPlainText()
        start_pos = doc_text.find(snippet)
        if start_pos == -1:
            return None, None
        end_pos = start_pos + len(snippet)
        fragment["start"] = start_pos
        fragment["end"] = end_pos
        return start_pos, end_pos

    def _get_code_color(self, fragment):
        """Obtiene el color asociado al código padre de un fragmento."""
        for c in self.codes:
            if fragment in c.get("fragments", []):
                return c.get("color", "#fff59d")
        return "#fff59d"

    def update_code_count(self, code_name, new_count):
        iterator = QTreeWidgetItemIterator(self.code_tree)
        while iterator.value():
            item = iterator.value()
            if self._code_item_name(item) == code_name:
                item.setText(1, str(new_count))
                break
            iterator += 1

    def create_subcode(self, selected_text, start, end):
        iterator = QTreeWidgetItemIterator(self.code_tree)
        code_names = []
        while iterator.value():
            code_names.append(self._code_item_name(iterator.value()))
            iterator += 1
        if not code_names:
            QMessageBox.warning(self, "Subcódigo", "Primero crea un código principal.")
            return

        parent_name, ok = QInputDialog.getItem(self, "Subcódigo", "Selecciona código padre:", code_names, 0, False)
        if not ok or not parent_name:
            return

        sub_label, ok = QInputDialog.getText(self, "Nuevo Subcódigo", "Nombre del subcódigo:")
        if not ok or not sub_label:
            return

        parent_item = self.find_tree_item(parent_name)
        if parent_item:
            self.create_new_code(selected_text, start, end, parent_item, sub_label)

    def find_tree_item(self, code_name):
        iterator = QTreeWidgetItemIterator(self.code_tree)
        while iterator.value():
            item = iterator.value()
            if self._code_item_name(item) == code_name:
                return item
            iterator += 1
        return None


    # -------------------- VER CÓDIGOS --------------------
    def open_code_viewer(self):
        if not self.codes:
            QMessageBox.information(self, "Códigos", "No hay códigos creados aún.")
            return
        if not self.current_doc:
            QMessageBox.information(self, "Códigos", "Primero selecciona un documento.")
            return
        doc_path = self.current_project.get_document_path(self.current_doc)
        viewer = CodeViewerWindow(
            doc_path,
            self.codes,
            theme=self._current_theme(),
            dark_mode=self.is_dark_mode,
        )
        viewer.exec()

    # -------------------- DESTACADO --------------------
    def highlight_selection(self, cursor, color):
        fmt = QTextCharFormat()
        fmt.setBackground(self._adjust_highlight_color(color))
        cursor.mergeCharFormat(fmt)

    def restore_highlights(self):
        """Aplica los fragmentos de self.highlighted en el text_area."""
        if not self.current_doc:
            return

        #  Limpiar resaltado previo
        cursor = self.text_area.textCursor()
        cursor.select(QTextCursor.Document)
        fmt_clear = QTextCharFormat()
        fmt_clear.setBackground(Qt.transparent)
        cursor.mergeCharFormat(fmt_clear)
        cursor.clearSelection()

        #  Aplicar los fragmentos guardados en self.highlighted
        for frag in self.highlighted:
            self.highlight_fragment(frag)



    def save_current_highlights(self):
        """Guarda los subrayados del documento actual en self.highlights."""
        if not self.current_doc:
            return

        # Filtrar los fragmentos del documento actual
        doc_fragments = []
        for c in self.codes:
            for frag in c.get("fragments", []):
                if frag.get("document") == self.current_doc:
                    if not frag.get("color"):
                        frag["color"] = c.get("color", "#fff59d")
                    doc_fragments.append(frag)

        self.highlighted = doc_fragments  # mantener en memoria para el documento actual
        self.highlights[self.current_doc] = doc_fragments


    # -------------------------
    # Actualizar ícono de memo
    # -------------------------
    def update_memo_icon(self, code_name, has_memo):
        """Actualiza el ícono de memo  en el árbol de códigos."""
        from PySide6.QtWidgets import QTreeWidgetItemIterator
        iterator = QTreeWidgetItemIterator(self.code_tree)
        while iterator.value():
            item = iterator.value()
            if self._code_item_name(item) == code_name:
                item.setText(2, "📝" if has_memo else "")
                break
            iterator += 1

    # -------------------- UTILIDADES DE COLOR --------------------
    def next_palette_color(self):
        color = self.COLOR_PALETTE[self._color_index % len(self.COLOR_PALETTE)][1]
        self._color_index += 1
        return color

    def ask_color_from_palette(self, suggested):
        dialog = ColorPickerDialog(self.COLOR_PALETTE, suggested, self)
        if dialog.exec() == QDialog.Accepted and dialog.selected_color:
            return dialog.selected_color
        return suggested

    def apply_code_item_color(self, item, color_hex):
        color = QColor(color_hex)
        background = self._code_item_background(color)
        foreground = QColor(self._current_theme()["tree_fg"])
        for col in range(item.columnCount()):
            item.setBackground(col, background)
            item.setForeground(col, foreground)
        icon = self._circle_icon(color)
        item.setIcon(0, icon)
        name = self._code_item_name(item)
        item.setText(0, f"   {name}")

    def _code_item_background(self, color):
        """Devuelve el color de fondo del árbol (sin resaltar el ítem)."""
        return QColor(self._current_theme()["tree_bg"])

    def _refresh_code_tree_colors(self):
        iterator = QTreeWidgetItemIterator(self.code_tree)
        while iterator.value():
            item = iterator.value()
            code_name = self._code_item_name(item)
            code = self.get_code_data(code_name)
            if code:
                self.apply_code_item_color(item, code.get("color", "#fff59d"))
            iterator += 1

    def _circle_icon(self, color):
        pixmap = QPixmap(12, 12)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.transparent)
        painter.drawEllipse(2, 2, 8, 8)
        painter.end()
        return QIcon(pixmap)

    def get_code_data(self, code_name):
        for code in self.codes:
            if code["name"] == code_name:
                return code
        return None


class ColorPickerDialog(QDialog):
    """Muestra 10 colores fijos inspirados en MaxQDA para seleccionar un código."""

    def __init__(self, palette, current_color=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar color del código")
        self.setModal(True)
        self.selected_color = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Elige uno de los colores disponibles:"))

        grid = QGridLayout()
        grid.setSpacing(10)

        for index, (label, color_hex) in enumerate(palette):
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(120, 40)
            border = "#222" if color_hex == current_color else "#666"
            text_color = "#000" if QColor(color_hex).lightness() > 128 else "#fff"
            btn.setStyleSheet(
                f"background-color: {color_hex}; color: {text_color}; "
                f"border: 2px solid {border}; border-radius: 6px;"
            )
            btn.clicked.connect(lambda checked=False, c=color_hex: self._select_and_accept(c))
            grid.addWidget(btn, index // 2, index % 2)

        layout.addLayout(grid)

        btn_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _select_and_accept(self, color_hex):
        self.selected_color = color_hex
        self.accept()

