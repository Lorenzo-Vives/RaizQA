import os
import shutil
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QFileDialog, QMessageBox, QInputDialog, QFrame, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QMenu, QDialog, QHeaderView, QTreeWidgetItemIterator,
    QGridLayout, QDialogButtonBox, QFileIconProvider, QAbstractItemView, QTextEdit
)
from PySide6.QtGui import QAction, QColor, QTextCursor, QTextCharFormat, QPainter, QPixmap, QIcon, QPalette
from PySide6.QtCore import Qt, QTimer, QPoint, QEvent
from docx import Document

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
        self._column_selection_info = None
        self._column_extra_selections = []
        self._prev_extra_selections = []
        self._search_matches = []
        self._search_index = -1
        self._search_term = ""

        # -------------------- LAYOUT PRINCIPAL --------------------
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)
        central_widget.setLayout(main_layout)

        # -------------------- TOP BAR (inspiración VSCode) --------------------
        topbar_frame = QFrame()
        topbar_frame.setObjectName("TopBarFrame")
        topbar_layout = QHBoxLayout(topbar_frame)
        topbar_layout.setContentsMargins(4, 1, 4, 1)
        topbar_layout.setSpacing(3)

        # Labels de proyecto y WD para reutilizarlos en la barra
        self.lbl_project = QLabel("Proyecto: Ninguno")
        self.lbl_project.setObjectName("ProjectLabel")
        self.lbl_project.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_working_dir = QLabel("WD: Ninguno")
        self.lbl_working_dir.setObjectName("MetaLabel")
        self.lbl_working_dir.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.lbl_top_brand = QLabel("RaizQA")
        self.lbl_top_brand.setObjectName("TopBrand")
        topbar_layout.addWidget(self.lbl_top_brand)

        topbar_layout.addSpacing(3)
        self.btn_menu_file = QPushButton("File")
        self.btn_menu_file.setObjectName("TopBarButton")
        self.btn_menu_file.setCursor(Qt.PointingHandCursor)
        topbar_layout.addWidget(self.btn_menu_file)
        self._setup_file_menu()

        self.btn_menu_options = QPushButton("Options")
        self.btn_menu_options.setObjectName("TopBarButton")
        self.btn_menu_options.setCursor(Qt.PointingHandCursor)
        topbar_layout.addWidget(self.btn_menu_options)
        self._setup_options_menu()

        topbar_layout.addStretch()

        self.search_field = QLineEdit()
        self.search_field.setObjectName("SearchField")
        self.search_field.setPlaceholderText("Busca en RaizQA")
        self.search_field.setReadOnly(False)
        self.search_field.returnPressed.connect(self.run_global_search)
        topbar_layout.addWidget(self.search_field, 3)

        self.btn_search_prev = QPushButton("←")
        self.btn_search_prev.setObjectName("SearchNavButton")
        self.btn_search_prev.setCursor(Qt.PointingHandCursor)
        self.btn_search_prev.clicked.connect(self.prev_search_match)
        topbar_layout.addWidget(self.btn_search_prev)

        self.btn_search_next = QPushButton("→")
        self.btn_search_next.setObjectName("SearchNavButton")
        self.btn_search_next.setCursor(Qt.PointingHandCursor)
        self.btn_search_next.clicked.connect(self.next_search_match)
        topbar_layout.addWidget(self.btn_search_next)

        self.lbl_search_count = QLabel("")
        self.lbl_search_count.setObjectName("SearchCount")
        topbar_layout.addWidget(self.lbl_search_count)

        meta_layout = QVBoxLayout()
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(0)
        meta_layout.addWidget(self.lbl_project)
        meta_layout.addWidget(self.lbl_working_dir)
        topbar_layout.addLayout(meta_layout)

        main_layout.addWidget(topbar_frame)

        # -------------------- ACCIONES --------------------
        actions_frame = QFrame()
        actions_frame.setObjectName("ActionsFrame")
        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(6)

        self.btn_working_dir = QPushButton("Seleccionar Working Directory")
        self.btn_working_dir.clicked.connect(self.select_working_dir)

        self.btn_create = QPushButton("Crear Proyecto")
        self.btn_create.clicked.connect(self.create_project)

        self.btn_open = QPushButton("Abrir Proyecto")
        self.btn_open.clicked.connect(self.open_project)

        self.btn_import_doc = QPushButton("Importar Archivo")
        self.btn_import_doc.clicked.connect(self.import_file)

        self.btn_save = QPushButton("💾 Guardar Proyecto")
        self.btn_save.clicked.connect(self.save_project)

        self.btn_view_codes = QPushButton("📚 Ver Códigos")
        self.btn_view_codes.clicked.connect(self.open_code_viewer)

        self.btn_export_codes = QPushButton("Exportar códigos")
        self.btn_export_codes.clicked.connect(self.export_code_tree)

        self.btn_export_diary = QPushButton("Exportar diario")
        self.btn_export_diary.clicked.connect(self.export_diary)

        self.btn_toggle_theme = QPushButton("☀️")
        self.btn_toggle_theme.clicked.connect(self.toggle_theme)

        self.btn_diary = QPushButton("📓 Diario de codificación")
        self.btn_diary.clicked.connect(self.open_diary)

        def add_action_row(buttons):
            row = QHBoxLayout()
            row.setSpacing(8)
            for btn in buttons:
                btn.setCursor(Qt.PointingHandCursor)
                btn.setMinimumHeight(32)
                btn.setProperty("actionButton", True)
                row.addWidget(btn)
            row.addStretch()
            actions_layout.addLayout(row)

        add_action_row(
            [
                self.btn_working_dir,
                self.btn_create,
                self.btn_open,
                self.btn_import_doc,
                self.btn_save,
                self.btn_toggle_theme,
            ]
        )
        add_action_row([self.btn_diary, self.btn_view_codes, self.btn_export_codes, self.btn_export_diary])
        main_layout.addWidget(actions_frame)

        # -------------------- CONTENIDO PRINCIPAL --------------------
        content_frame = QFrame()
        content_frame.setObjectName("ContentFrame")
        content_layout = QHBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(12)

        docs_card = QFrame()
        docs_card.setObjectName("PanelCard")
        docs_layout = QVBoxLayout(docs_card)
        docs_layout.setContentsMargins(12, 12, 12, 12)
        docs_layout.setSpacing(8)

        docs_header = QHBoxLayout()
        docs_header.setContentsMargins(0, 0, 0, 0)
        docs_header.setSpacing(2)
        docs_title = QLabel("Documentos importados")
        docs_title.setObjectName("Subheading")
        docs_title.setContentsMargins(0, 0, 0, 0)
        docs_header.addWidget(docs_title)
        self.btn_new_folder = QPushButton("📁")
        self.btn_new_folder.setObjectName("GhostButton")
        self.btn_new_folder.setToolTip("Crear carpeta de documentos")
        self.btn_new_folder.setFixedSize(24, 20)
        self.btn_new_folder.clicked.connect(self.create_document_folder)
        docs_header.addStretch()
        docs_header.addWidget(self.btn_new_folder)
        docs_layout.addLayout(docs_header)

        self.doc_tree = DocumentTree(drop_callback=self._on_doc_tree_drop)
        self.doc_tree.setHeaderLabels(["Documentos"])
        self.doc_tree.currentItemChanged.connect(self.display_document)
        self.doc_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.doc_tree.customContextMenuRequested.connect(self.doc_tree_context_menu)
        self.doc_tree.setDragEnabled(True)
        self.doc_tree.setAcceptDrops(True)
        self.doc_tree.setDropIndicatorShown(True)
        self.doc_tree.setDefaultDropAction(Qt.MoveAction)
        docs_layout.addWidget(self.doc_tree, 50)
        left_layout.addWidget(docs_card, 1)

        code_card = QFrame()
        code_card.setObjectName("PanelCard")
        code_layout = QVBoxLayout(code_card)
        code_layout.setContentsMargins(12, 12, 12, 12)
        code_layout.setSpacing(8)

        code_header = QLabel("Árbol de Códigos")
        code_header.setObjectName("Subheading")
        code_layout.addWidget(code_header)

        self.code_tree = CodeTree(drop_callback=self._on_code_tree_drop)
        self.code_tree.setHeaderLabels(["Código", "n", "Memo"])
        header = self.code_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        self.code_tree.setColumnWidth(1, 50)
        self.code_tree.setColumnWidth(2, 80)
        self.code_tree.setDragEnabled(True)
        self.code_tree.setAcceptDrops(True)
        self.code_tree.setDropIndicatorShown(True)
        self.code_tree.setDefaultDropAction(Qt.MoveAction)
        code_layout.addWidget(self.code_tree, 60)
        left_layout.addWidget(code_card, 2)

        # Eventos
        self.code_tree.itemClicked.connect(self.show_code_fragments)
        self.code_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.code_tree.customContextMenuRequested.connect(self.code_tree_context_menu)

        content_layout.addLayout(left_layout, 38)

        text_card = QFrame()
        text_card.setObjectName("PanelCard")
        text_layout = QVBoxLayout(text_card)
        text_layout.setContentsMargins(12, 12, 12, 12)
        text_layout.setSpacing(8)
        tab_bar = QFrame()
        tab_bar.setObjectName("TabBar")
        tab_bar.setFixedHeight(28)
        tab_bar_layout = QHBoxLayout(tab_bar)
        tab_bar_layout.setContentsMargins(8, 2, 8, 2)
        tab_bar_layout.setSpacing(6)
        tab_bar_layout.addStretch()
        text_layout.addWidget(tab_bar)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_area.customContextMenuRequested.connect(self.text_context_menu)
        self.text_area.installEventFilter(self)
        text_layout.addWidget(self.text_area, 1)
        content_layout.addWidget(text_card, 62)

        main_layout.addWidget(content_frame, 1)

        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(self.AUTO_SAVE_INTERVAL)

        self.apply_theme()
        self._refresh_options_menu()

    def _setup_file_menu(self):
        menu = QMenu(self)

        actions = [
            ("Seleccionar Working Directory", self.select_working_dir),
            ("Crear Proyecto", self.create_project),
            ("Abrir Proyecto", self.open_project),
            ("Importar Archivo", self.import_file),
            ("Guardar Proyecto", self.save_project),
            ("Guardar Proyecto Como...", self.save_project_as),
            ("Exportar códigos", self.export_code_tree),
            ("Exportar diario (Word)", self.export_diary),
        ]
        for title, handler in actions:
            act = QAction(title, self)
            act.triggered.connect(handler)
            menu.addAction(act)

        self.btn_menu_file.setMenu(menu)
        self.menu_file = menu

    def _setup_options_menu(self):
        menu = QMenu(self)
        self.action_toggle_theme = QAction(self)
        self.action_toggle_theme.triggered.connect(self.toggle_theme)
        menu.addAction(self.action_toggle_theme)
        self.btn_menu_options.setMenu(menu)
        self.menu_options = menu

    def _refresh_options_menu(self):
        if hasattr(self, "action_toggle_theme"):
            self.action_toggle_theme.setText("Modo claro" if self.is_dark_mode else "Modo oscuro")

    # -------------------- BÚSQUEDA GLOBAL --------------------
    def _update_search_label(self):
        if not self._search_matches:
            self.lbl_search_count.setText("")
            return
        self.lbl_search_count.setText(f"{self._search_index + 1}/{len(self._search_matches)}")

    def _select_document(self, doc_name):
        items = self.doc_tree.findItems(doc_name, Qt.MatchExactly | Qt.MatchRecursive, 0)
        if items:
            item = items[0]
            self.doc_tree.setCurrentItem(item)
            self.display_document(item, None)

    def _highlight_in_viewer(self, term, start_pos=None):
        if not hasattr(self, "text_area") or not term:
            return
        cursor = self.text_area.textCursor()
        if start_pos is not None:
            cursor.setPosition(start_pos)
        else:
            cursor.movePosition(QTextCursor.Start)
        self.text_area.setTextCursor(cursor)
        self.text_area.find(term)

    def run_global_search(self):
        term = self.search_field.text().strip() if hasattr(self, "search_field") else ""
        if not term:
            return
        if not self.current_project:
            QMessageBox.information(self, "Buscar", "Primero abre o crea un proyecto.")
            return

        self._search_term = term
        self._search_matches = []
        self._search_index = -1

        term_lower = term.lower()
        doc_matches = []
        code_matches = []
        memo_matches = []

        # Buscar en documentos
        for doc_name in self._all_documents():
            try:
                text = self.current_project.read_document(doc_name)
            except Exception:
                continue
            if term_lower in text.lower():
                doc_matches.append(doc_name)
                # recopilar ocurrencias con posiciones
                text_lower = text.lower()
                start = 0
                while True:
                    idx = text_lower.find(term_lower, start)
                    if idx == -1:
                        break
                    self._search_matches.append({"doc": doc_name, "start": idx, "length": len(term)})
                    start = idx + len(term)

        # Buscar en códigos y memos
        for code in self.codes:
            if term_lower in code["name"].lower():
                code_matches.append(code["name"])
        if self.memo_manager:
            for code_name, memo_text in self.memo_manager.memos.items():
                if term_lower in code_name.lower() or term_lower in (memo_text or "").lower():
                    if code_name not in memo_matches:
                        memo_matches.append(code_name)

        # Seleccionar primeras coincidencias
        if doc_matches:
            self._search_index = 0
            self._go_to_match(self._search_matches[self._search_index])
        elif code_matches:
            item = self.find_tree_item(code_matches[0])
            if item:
                self.code_tree.setCurrentItem(item)

        summary = []
        if doc_matches:
            summary.append(f"Documentos: {', '.join(doc_matches[:5])}" + ("..." if len(doc_matches) > 5 else ""))
        if code_matches:
            summary.append(f"Códigos: {', '.join(code_matches[:5])}" + ("..." if len(code_matches) > 5 else ""))
        if memo_matches:
            summary.append(f"Memos: {', '.join(memo_matches[:5])}" + ("..." if len(memo_matches) > 5 else ""))

        if not summary:
            QMessageBox.information(self, "Buscar", "Sin coincidencias en documentos, códigos o memos.")
        else:
            QMessageBox.information(self, "Buscar", "\n".join(summary))
        self._update_search_label()

    def _go_to_match(self, match):
        if not match:
            return
        self._select_document(match["doc"])
        # Asegurar que el texto está cargado antes de resaltar
        QTimer.singleShot(0, lambda: self._highlight_in_viewer(self._search_term, match["start"]))
        self._update_search_label()

    def next_search_match(self):
        if not self._search_matches:
            self.run_global_search()
            return
        if not self._search_term:
            return
        self._search_index = (self._search_index + 1) % len(self._search_matches)
        self._go_to_match(self._search_matches[self._search_index])

    def prev_search_match(self):
        if not self._search_matches:
            self.run_global_search()
            return
        if not self._search_term:
            return
        self._search_index = (self._search_index - 1) % len(self._search_matches)
        self._go_to_match(self._search_matches[self._search_index])

    # -------------------- TEMA --------------------
    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()
        self._refresh_options_menu()

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
            self.btn_toggle_theme.setText("🌙" if self.is_dark_mode else "☀️")

        base_styles = f"""
            QMainWindow {{
                background-color: {theme['window_bg']};
                color: {theme['text_fg']};
            }}
            QLabel {{
                color: {theme['text_fg']};
            }}
            QLabel#TopBrand {{
                font-weight: 700;
                padding-left: 2px;
                font-size: 11px;
            }}
            QFrame#TopBarFrame {{
                background-color: {theme['panel_bg']};
                border: 1px solid {theme['border']};
                border-radius: 5px;
            }}
            QLabel#SearchCount {{
                color: {theme['muted_text']};
                font-size: 11px;
                min-width: 46px;
                qproperty-alignment: AlignCenter;
            }}
            QPushButton#TopBarButton {{
                background: transparent;
                border: none;
                color: {theme['text_fg']};
                padding: 3px 7px;
                font-weight: 600;
                font-size: 11px;
            }}
            QPushButton#TopBarButton:hover {{
                background-color: {theme['selection']};
                color: {highlight_text};
                border-radius: 6px;
            }}
            QPushButton#SearchNavButton {{
                background: transparent;
                border: 1px solid {theme['border']};
                color: {theme['text_fg']};
                padding: 2px 6px;
                min-width: 24px;
                border-radius: 5px;
                font-size: 11px;
            }}
            QPushButton#SearchNavButton:hover {{
                background-color: {theme['selection']};
                color: {highlight_text};
            }}
            QLineEdit#SearchField {{
                background-color: {theme['text_bg']};
                color: {theme['text_fg']};
                border: 1px solid {theme['border']};
                border-radius: 6px;
                padding: 3px 9px;
                min-height: 22px;
                font-size: 11px;
            }}
            QLabel#SectionLabel {{
                font-weight: 700;
                font-size: 12px;
                letter-spacing: 0.4px;
                text-transform: uppercase;
                color: {theme['muted_text']};
            }}
            QLabel#Subheading {{
                font-weight: 700;
            }}
            QLabel#MetaLabel {{
                color: {theme['muted_text']};
                font-size: 11px;
            }}
            QLabel#ProjectLabel {{
                font-weight: 700;
            }}
            QFrame#ActionsFrame {{
                background: transparent;
            }}
            QFrame#ContentFrame {{
                background: transparent;
            }}
            QFrame#ActionCard {{
                background-color: {theme['panel_bg']};
                border: 1px solid {theme['border']};
                border-radius: 12px;
            }}
            QFrame#PanelCard {{
                background-color: {theme['panel_bg']};
                border: 1px solid {theme['border']};
                border-radius: 10px;
            }}
            QFrame#TabBar {{
                background-color: {theme['panel_bg']};
                border: 1px solid {theme['border']};
                border-radius: 6px;
            }}
            QPushButton {{
                background-color: {theme['button_bg']};
                color: {theme['button_fg']};
                border: 1px solid {theme['border']};
                padding: 8px 12px;
                border-radius: 8px;
            }}
            QPushButton[actionButton="true"] {{
                font-weight: 600;
                text-align: left;
                padding: 8px 12px;
            }}
            QPushButton#GhostButton {{
                background-color: transparent;
                border: 1px dashed {theme['border']};
                min-height: 20px;
                min-width: 24px;
                padding: 2px 4px;
            }}
            QPushButton:hover {{
                background-color: {theme['selection']};
                color: {highlight_text};
            }}
            QPushButton#GhostButton:hover {{
                background-color: {theme['panel_bg']};
                color: {theme['text_fg']};
            }}
        """
        self.setStyleSheet(base_styles)

        self.text_area.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: {theme['text_bg']};
                color: {theme['text_fg']};
                border: 1px solid {theme['border']};
                border-radius: 8px;
                padding: 6px 6px 6px 0;
                selection-background-color: {theme['selection']};
                selection-color: {highlight_text};
            }}
            QScrollBar:vertical {{
                background: {theme['panel_bg']};
                width: 10px;
                margin: 0px;
                border: 1px solid {theme['border']};
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme['selection']};
                min-height: 30px;
                border-radius: 6px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            """
        )

        self.doc_tree.setStyleSheet(
            f"""
            QTreeWidget {{
                background-color: {theme['tree_bg']};
                color: {theme['tree_fg']};
                border: 1px solid {theme['border']};
                border-radius: 8px;
                padding: 4px;
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
                border-radius: 8px;
                padding: 4px;
            }}
            QTreeWidget::item:selected {{
                background-color: {theme['selection']};
                color: {highlight_text};
            }}
            """
        )

        self.lbl_working_dir.setStyleSheet(f"font-size: 11px; color: {theme['muted_text']};")

        self.lbl_project.setStyleSheet(f"color: {theme['text_fg']}; font-weight: 700;")

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

    def save_project_as(self):
        if not self.current_project:
            QMessageBox.warning(self, "Guardar como", "No hay proyecto activo para guardar.")
            return

        base_dir = QFileDialog.getExistingDirectory(
            self,
            "Selecciona carpeta destino",
            self.working_dir or os.getcwd(),
        )
        if not base_dir:
            return

        new_name, ok = QInputDialog.getText(
            self,
            "Guardar proyecto como",
            "Nombre del proyecto:",
            text=f"{self.current_project.name}_copia",
        )
        if not ok or not new_name:
            return

        target_path = os.path.join(base_dir, new_name)
        if os.path.exists(target_path):
            QMessageBox.warning(self, "Guardar como", "Ya existe un proyecto con ese nombre en la carpeta seleccionada.")
            return

        # Guardar estado actual y copiar la carpeta del proyecto
        self.save_project()
        try:
            shutil.copytree(self.current_project.path, target_path)
        except Exception as exc:
            QMessageBox.critical(self, "Guardar como", f"No se pudo copiar el proyecto:\n{exc}")
            return

        self.working_dir = base_dir
        self.current_project = Project(new_name, base_dir)
        self.memo_manager = self.current_project.memo_manager
        self.lbl_working_dir.setText(f"WD: {base_dir}")
        self.lbl_project.setText(f"Proyecto: {new_name}")
        self.reset_project_state()
        self.load_project()
        QMessageBox.information(self, "Guardar como", f"Proyecto guardado como '{new_name}'.")

    def export_diary(self):
        if not self.current_project:
            QMessageBox.warning(self, "Exportar diario", "Primero abre o crea un proyecto.")
            return

        diary_text = ""
        try:
            diary_text = self.current_project.load_diary() or ""
        except Exception as exc:
            QMessageBox.critical(self, "Exportar diario", f"No se pudo leer el diario:\n{exc}")
            return

        default_dir = self.working_dir or os.getcwd()
        default_path = os.path.join(default_dir, f"{self.current_project.name}_diario.docx") if self.current_project else os.path.join(default_dir, "diario.docx")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar diario a Word",
            default_path,
            "Word (*.docx)",
        )
        if not path:
            return

        try:
            doc = Document()
            doc.add_heading(f"Diario de codificación - {self.current_project.name}", level=1)
            doc.add_paragraph(diary_text if diary_text.strip() else "(Diario vacío)")
            doc.save(path)
            QMessageBox.information(self, "Exportar diario", f"Diario exportado en:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Exportar diario", f"No se pudo exportar el diario:\n{exc}")


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
                    self._clear_column_selection()
                    self._start_column_selection(event.pos())
                    return True
                else:
                    if self._column_selection_info:
                        self._clear_column_selection()
            elif event.type() == QEvent.MouseMove:
                if self._column_selecting:
                    self._update_column_selection(event.pos())
                    return True
            elif event.type() in (QEvent.MouseButtonRelease, QEvent.Leave):
                if self._column_selecting:
                    self._update_column_selection(event.pos() if hasattr(event, "pos") else QPoint())
                    self._column_selecting = False
                    return True
            elif event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_C and event.modifiers() & Qt.ControlModifier:
                    cursor = self.text_area.textCursor()
                    if self._column_selection_info and not cursor.hasSelection():
                        self._copy_column_selection_to_clipboard()
                        return True
        return super().eventFilter(obj, event)

    def _start_column_selection(self, pos):
        cursor = self.text_area.cursorForPosition(pos)
        block = cursor.block()
        self._column_selecting = True
        self._column_start = (block.blockNumber(), cursor.positionInBlock())
        self._column_selection_info = None
        self._column_extra_selections = []
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
        width = max(1, abs(end_col - start_col))
        col_right = col_left + width

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
            selection = QTextEdit.ExtraSelection()
            c = QTextCursor(block)
            c.setPosition(block.position() + start_idx)
            c.setPosition(block.position() + end_idx, QTextCursor.KeepAnchor)
            selection.cursor = c
            selection.format = fmt
            selections.append(selection)

        self._column_selection_info = {
            "first_line": first_line,
            "last_line": last_line,
            "col_left": col_left,
            "width": width,
        }
        self._column_extra_selections = selections
        self.text_area.setExtraSelections(self._prev_extra_selections + selections)

    def _clear_column_selection(self):
        if self._column_selecting:
            self._column_selecting = False
        if self._prev_extra_selections:
            self.text_area.setExtraSelections(self._prev_extra_selections)
        else:
            self.text_area.setExtraSelections([])
        self._column_extra_selections = []
        self._column_selection_info = None
        self._prev_extra_selections = []

    def _apply_column_selection_style(self):
        if self._column_selection_info and self._column_extra_selections:
            self.text_area.setExtraSelections(self._prev_extra_selections + self._column_extra_selections)
        elif self._prev_extra_selections:
            self.text_area.setExtraSelections(self._prev_extra_selections)

    def _copy_column_selection_to_clipboard(self):
        """Construye el texto de la seleccion columnar y lo coloca en el portapapeles."""
        if not self._column_selection_info:
            return
        info = self._column_selection_info
        doc = self.text_area.document()
        lines = []
        for line in range(info["first_line"], info["last_line"] + 1):
            block = doc.findBlockByNumber(line)
            if not block.isValid():
                continue
            text = block.text()
            if info["col_left"] >= len(text):
                snippet = ""
            else:
                end_idx = min(len(text), info["col_left"] + info["width"])
                snippet = text[info["col_left"]:end_idx]
            lines.append(snippet)
        QApplication.clipboard().setText("\n".join(lines))

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
        self._clear_column_selection()
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
    
        self._clear_column_selection()
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

    # -------------------- EXPORTAR SISTEMA DE CÓDIGOS --------------------
    def export_code_tree(self):
        if not self.codes:
            QMessageBox.information(self, "Exportar códigos", "No hay códigos para exportar.")
            return

        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment
        except ImportError:
            QMessageBox.critical(
                self,
                "Exportar códigos",
                "Falta la dependencia 'openpyxl'. Agrega 'openpyxl' a requirements e instálala para exportar.",
            )
            return

        save_dir = self.working_dir or os.getcwd()
        default_path = os.path.join(save_dir, "codigos.xlsx")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar sistema de códigos",
            default_path,
            "Excel (*.xlsx)",
        )
        if not path:
            return

        rows = list(self._collect_code_rows_for_export())
        if not rows:
            QMessageBox.information(self, "Exportar códigos", "No se encontraron códigos en el árbol.")
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Códigos"

        header = ["Sistema de códigos", "", "", "", "Memo", "Frecuencia"]
        ws.append(header)

        header_fill = PatternFill(start_color="5d9bd3", end_color="5d9bd3", fill_type="solid")
        bold = Font(bold=True)
        for col_idx in range(1, len(header) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = bold
            cell.fill = header_fill
            cell.alignment = Alignment(vertical="center")

        memo_col = 5
        freq_col = 6
        data_fill = PatternFill(start_color="f6f8fb", end_color="f6f8fb", fill_type="solid")
        for level, name, memo, freq in rows:
            total_cols = max(freq_col, 1 + level)
            row = ["" for _ in range(total_cols)]
            name_col = 1 + level
            row[name_col - 1] = name
            if memo_col - 1 >= len(row):
                row.extend([""] * (memo_col - len(row)))
            row[memo_col - 1] = memo or ""
            if freq_col - 1 >= len(row):
                row.extend([""] * (freq_col - len(row)))
            row[freq_col - 1] = freq if freq is not None else ""
            ws.append(row)
            # si la fila tiene información en alguna columna, colorear toda la fila
            if any(str(cell).strip() for cell in row):
                current_row = ws.max_row
                for col_idx in range(1, freq_col + 1):
                    cell = ws.cell(row=current_row, column=col_idx)
                    cell.fill = data_fill

        ws.column_dimensions["A"].width = 36
        ws.column_dimensions["B"].width = 36
        ws.column_dimensions["C"].width = 36
        ws.column_dimensions["D"].width = 36
        ws.column_dimensions["E"].width = 48
        ws.column_dimensions["F"].width = 14

        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=freq_col):
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)

        try:
            wb.save(path)
            QMessageBox.information(self, "Exportar códigos", f"Sistema de códigos exportado en:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Exportar códigos", f"No se pudo guardar el archivo:\n{exc}")

    def _collect_code_rows_for_export(self):
        """Devuelve tuplas (nivel, nombre, memo, frecuencia) respetando el orden del arbol."""
        if not self.code_tree:
            return []

        def memo_for(name):
            if self.memo_manager:
                return self.memo_manager.get_memo(name)
            code_data = self.get_code_data(name)
            return code_data.get("memo") if code_data else ""

        def freq_for(code_data):
            if not code_data:
                return ""
            if "count" in code_data:
                return code_data.get("count")
            return len(code_data.get("fragments", []))

        def walk(item, level):
            name = self._code_item_name(item)
            data = self.get_code_data(name)
            yield (level, name, memo_for(name) or "", freq_for(data))
            for idx in range(item.childCount()):
                child = item.child(idx)
                yield from walk(child, level + 1)

        for idx in range(self.code_tree.topLevelItemCount()):
            item = self.code_tree.topLevelItem(idx)
            yield from walk(item, 0)

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

