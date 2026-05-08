import os
import shutil
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox, QInputDialog, QFrame, QLineEdit, QSizeGrip,
    QTreeWidget, QTreeWidgetItem, QMenu, QDialog, QHeaderView, QTreeWidgetItemIterator,
    QGridLayout, QDialogButtonBox, QFileIconProvider, QAbstractItemView, QTextEdit,
    QStackedWidget
)
from PySide6.QtGui import QAction, QColor, QTextCursor, QTextCharFormat, QPainter, QPixmap, QIcon, QPalette
from PySide6.QtCore import Qt, QTimer, QPoint, QEvent
from docx import Document

from gui.dialogs.memo_dialog import MemoDialog
from gui.dialogs.fragments_dialog import CodeFragmentsDialog
from gui.dialogs.diary_dialog import DiaryDialog
from gui.dialogs.compare_dialog import CompareDialog
from gui.dialogs.code_matrix_dialog import CodeMatrixDialog
from gui.dialogs.wordcloud_dialog import WordCloudDialog
from gui.dialogs.themes_categories_dialog import ThemesCategoriesDialog
from gui.dialogs.themes_analysis_dialog import ThemesAnalysisDialog
from gui.dialogs.case_study_dialog import CaseStudyDialog
from gui.document_tree import DocumentTree
from gui.code_tree import CodeTree
from gui.image_viewer import ImageDocumentViewer
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
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setWindowTitle("RaizQA 🌱")
        self.setGeometry(100, 100, 1000, 600)

        self.current_project = None
        self.memo_manager = None
        self.working_dir = None
        self.current_doc = None
        self.codes = []
        self.code_themes = []
        self.case_studies = []
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
        self._zoom_level = 0
        self._codes_expanded = True
        self._image_selection_info = None

        # -------------------- LAYOUT PRINCIPAL --------------------
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)

        # -------------------- TOP BAR (inspiración VSCode) --------------------
        topbar_frame = QFrame()
        topbar_frame.setObjectName("TopBarFrame")
        topbar_frame.setFixedHeight(34)
        self.topbar_frame = topbar_frame
        topbar_layout = QHBoxLayout(topbar_frame)
        topbar_layout.setContentsMargins(8, 2, 8, 2)
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
        topbar_layout.addSpacing(6)

        self.btn_minimize = QPushButton("_")
        self.btn_minimize.setObjectName("WindowButton")
        self.btn_minimize.setFixedSize(24, 20)
        self.btn_minimize.clicked.connect(self.showMinimized)
        topbar_layout.addWidget(self.btn_minimize)

        self.btn_maximize = QPushButton("[]")
        self.btn_maximize.setObjectName("WindowButton")
        self.btn_maximize.setFixedSize(24, 20)
        self.btn_maximize.clicked.connect(self.toggle_maximize)
        topbar_layout.addWidget(self.btn_maximize)

        self.btn_close = QPushButton("X")
        self.btn_close.setObjectName("WindowButtonClose")
        self.btn_close.setFixedSize(24, 20)
        self.btn_close.clicked.connect(self.close)
        topbar_layout.addWidget(self.btn_close)

        main_layout.addWidget(topbar_frame)

        content_wrapper = QWidget()
        content_wrapper_layout = QVBoxLayout(content_wrapper)
        content_wrapper_layout.setContentsMargins(12, 12, 12, 12)
        content_wrapper_layout.setSpacing(10)

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

        self.btn_add_code = QPushButton("Agregar código")
        self.btn_add_code.clicked.connect(self.add_code_from_toolbar)

        self.btn_themes_categories = QPushButton("Temas y categorías")
        self.btn_themes_categories.clicked.connect(self.open_themes_categories)

        self.btn_export_codes = QPushButton("Exportar libro de códigos")
        self.btn_export_codes.clicked.connect(self.export_code_tree)

        self.btn_export_fragments = QPushButton("Exportar fragmentos")
        self.btn_export_fragments.clicked.connect(self.export_code_fragments)

        self.btn_compare = QPushButton("Comparar documentos")
        self.btn_compare.clicked.connect(self.open_compare_dialog)

        self.btn_code_matrix = QPushButton("Code Matrix Browser")
        self.btn_code_matrix.clicked.connect(self.open_code_matrix)

        self.btn_wordcloud = QPushButton("Nube de palabras")
        self.btn_wordcloud.clicked.connect(self.open_wordcloud_dialog)

        self.btn_themes_analysis = QPushButton("Analisis de temas")
        self.btn_themes_analysis.clicked.connect(self.open_themes_analysis)

        self.btn_case_study = QPushButton("Estudio de casos")
        self.btn_case_study.clicked.connect(self.open_case_study)

        self.btn_export_diary = QPushButton("Exportar diario")
        self.btn_export_diary.clicked.connect(self.export_diary)

        self.btn_toggle_theme = QPushButton("☀️")
        self.btn_toggle_theme.clicked.connect(self.toggle_theme)

        self.btn_diary = QPushButton("📓 Diario de codificación")
        self.btn_diary.clicked.connect(self.open_diary)

        self.btn_nav_home = QPushButton("Inicio")
        self.btn_nav_codes = QPushButton("Códigos")
        self.btn_nav_analysis = QPushButton("Análisis")

        nav_row = QHBoxLayout()
        nav_row.setSpacing(8)
        for btn in (self.btn_nav_home, self.btn_nav_codes, self.btn_nav_analysis, self.btn_toggle_theme):
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(30)
            btn.setProperty("navButton", True)
            if btn is not self.btn_toggle_theme:
                btn.setCheckable(True)
            nav_row.addWidget(btn)
        nav_row.addStretch()
        actions_layout.addLayout(nav_row)

        def add_action_row(target_layout, buttons):
            row = QHBoxLayout()
            row.setSpacing(8)
            for btn in buttons:
                btn.setCursor(Qt.PointingHandCursor)
                btn.setMinimumHeight(32)
                btn.setProperty("actionButton", True)
                row.addWidget(btn)
            row.addStretch()
            target_layout.addLayout(row)

        self.actions_home = QWidget()
        home_layout = QVBoxLayout(self.actions_home)
        home_layout.setContentsMargins(0, 0, 0, 0)
        home_layout.setSpacing(6)
        add_action_row(home_layout, [self.btn_working_dir, self.btn_create, self.btn_open, self.btn_import_doc])

        self.actions_codes = QWidget()
        codes_layout = QVBoxLayout(self.actions_codes)
        codes_layout.setContentsMargins(0, 0, 0, 0)
        codes_layout.setSpacing(6)
        add_action_row(codes_layout, [self.btn_add_code, self.btn_view_codes, self.btn_themes_categories, self.btn_export_codes, self.btn_export_fragments, self.btn_diary, self.btn_export_diary])

        self.actions_analysis = QWidget()
        analysis_layout = QVBoxLayout(self.actions_analysis)
        analysis_layout.setContentsMargins(0, 0, 0, 0)
        analysis_layout.setSpacing(6)
        add_action_row(analysis_layout, [self.btn_compare, self.btn_code_matrix, self.btn_wordcloud, self.btn_themes_analysis, self.btn_case_study])

        actions_layout.addWidget(self.actions_home)
        actions_layout.addWidget(self.actions_codes)
        actions_layout.addWidget(self.actions_analysis)

        self.btn_nav_home.clicked.connect(lambda: self._set_actions_view("home"))
        self.btn_nav_codes.clicked.connect(lambda: self._set_actions_view("codes"))
        self.btn_nav_analysis.clicked.connect(lambda: self._set_actions_view("analysis"))
        self._set_actions_view("home")

        content_wrapper_layout.addWidget(actions_frame)

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

        code_header_row = QHBoxLayout()
        code_header_row.setContentsMargins(0, 0, 0, 0)
        code_header_row.setSpacing(6)
        code_header = QLabel("Árbol de Códigos")
        code_header.setObjectName("Subheading")
        code_header_row.addWidget(code_header)
        code_header_row.addStretch()
        self.code_search_field = QLineEdit()
        self.code_search_field.setPlaceholderText("Buscar código")
        self.code_search_field.textChanged.connect(self.filter_codes)
        self.code_search_field.setFixedWidth(180)
        self.btn_toggle_code_expand = QPushButton("Contraer")
        self.btn_toggle_code_expand.setFixedWidth(90)
        self.btn_toggle_code_expand.clicked.connect(self.toggle_code_tree_expansion)
        code_header_row.addWidget(self.btn_toggle_code_expand)
        code_header_row.addWidget(self.code_search_field)
        code_layout.addLayout(code_header_row)

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
        self.code_tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        code_layout.addWidget(self.code_tree, 60)
        left_layout.addWidget(code_card, 2)

        # Eventos
        self._code_tree_updating = False
        self.code_tree.itemPressed.connect(self._on_code_tree_item_clicked)
        self.code_tree.itemDoubleClicked.connect(self._on_code_tree_item_double_clicked)
        self.code_tree.itemChanged.connect(self._on_code_tree_item_changed)
        self.code_tree.itemDelegate().closeEditor.connect(self._on_code_tree_editor_closed)
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

        self.viewer_stack = QStackedWidget()

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_area.customContextMenuRequested.connect(self.text_context_menu)
        self.text_area.installEventFilter(self)
        self.viewer_stack.addWidget(self.text_area)

        self.image_viewer = ImageDocumentViewer(self)
        self.image_viewer.selectionChanged.connect(self._on_image_selection_changed)
        self.image_viewer.contextMenuRequested.connect(self._image_context_menu)
        self.viewer_stack.addWidget(self.image_viewer)

        text_layout.addWidget(self.viewer_stack, 1)
        content_layout.addWidget(text_card, 62)

        content_wrapper_layout.addWidget(content_frame, 1)

        resize_row = QHBoxLayout()
        resize_row.setContentsMargins(0, 0, 0, 0)
        resize_row.addStretch()
        self.size_grip = QSizeGrip(self)
        resize_row.addWidget(self.size_grip)
        content_wrapper_layout.addLayout(resize_row)

        main_layout.addWidget(content_wrapper, 1)

        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(self.AUTO_SAVE_INTERVAL)

        self.apply_theme()
        self._refresh_options_menu()
        self._setup_titlebar_drag()

    def _setup_file_menu(self):
        menu = QMenu(self)

        actions = [
            ("Seleccionar Working Directory", self.select_working_dir),
            ("Crear Proyecto", self.create_project),
            ("Abrir Proyecto", self.open_project),
            ("Importar Archivo", self.import_file),
            ("Guardar Proyecto", self.save_project),
            ("Guardar Proyecto Como...", self.save_project_as),
            ("Exportar libro de códigos", self.export_code_tree),
            ("Exportar fragmentos", self.export_code_fragments),
            ("Exportar diario (Word)", self.export_diary),
            ("Comparar documentos", self.open_compare_dialog),
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

    def _setup_titlebar_drag(self):
        self._drag_pos = None
        self._titlebar_drag_widgets = [
            self.topbar_frame,
            self.lbl_top_brand,
            self.lbl_project,
            self.lbl_working_dir,
            self.lbl_search_count,
        ]
        for widget in self._titlebar_drag_widgets:
            widget.installEventFilter(self)

    def _set_actions_view(self, view_name):
        self.actions_home.setVisible(view_name == "home")
        self.actions_codes.setVisible(view_name == "codes")
        self.actions_analysis.setVisible(view_name == "analysis")
        self.btn_nav_home.setChecked(view_name == "home")
        self.btn_nav_codes.setChecked(view_name == "codes")
        self.btn_nav_analysis.setChecked(view_name == "analysis")

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

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
            if self._is_image_document(doc_name):
                continue
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
                border-bottom: 1px solid {theme['border']};
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
            QPushButton[navButton="true"] {{
                background-color: {theme['panel_bg']};
                border: 1px solid {theme['border']};
                padding: 6px 12px;
                font-weight: 600;
            }}
            QPushButton[navButton="true"]:checked {{
                background-color: {theme['selection']};
                color: {highlight_text};
                border-color: {theme['selection']};
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
            QPushButton#WindowButton {{
                background: transparent;
                border: 1px solid {theme['border']};
                color: {theme['text_fg']};
                padding: 1px 6px;
                border-radius: 4px;
                font-size: 10px;
            }}
            QPushButton#WindowButton:hover {{
                background-color: {theme['selection']};
                color: {highlight_text};
            }}
            QPushButton#WindowButtonClose {{
                background: transparent;
                border: 1px solid {theme['border']};
                color: {theme['text_fg']};
                padding: 1px 6px;
                border-radius: 4px;
                font-size: 10px;
            }}
            QPushButton#WindowButtonClose:hover {{
                background-color: #e81123;
                color: #ffffff;
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
        self.image_viewer.apply_theme(theme)

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
        if not self.current_project:
            return

        item = self.code_tree.itemAt(pos)
        code_name = self._code_item_name(item) if item else None
        menu = QMenu()
        add_code_action = menu.addAction("Agregar código")
        rename_action = None
        view_fragments_action = None
        view_memo_action = None
        add_memo_action = None
        delete_memo_action = None

        if item and self.memo_manager:
            menu.addSeparator()
            rename_action = menu.addAction("Renombrar codigo")
            view_fragments_action = menu.addAction("Ver fragmentos")
            menu.addSeparator()

            view_memo_action = menu.addAction("👁️ Ver memo")
            add_memo_action = menu.addAction("📝 Agregar / editar memo")
            delete_memo_action = menu.addAction("❌ Eliminar memo")

        action = menu.exec(self.code_tree.viewport().mapToGlobal(pos))
        if action == add_code_action:
            self.prompt_add_code(parent_item=item)
        elif action == rename_action:
            self._start_code_rename(item)
        elif action == view_fragments_action:
            self.show_code_fragments(item, 1)
        elif action == view_memo_action:
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

    def delete_document(self, doc_item):
        if not doc_item or doc_item.data(0, Qt.UserRole) != "doc":
            return
        doc_name = doc_item.text(0)
        confirm = QMessageBox.question(
            self,
            "Eliminar documento",
            f"¿Eliminar el documento '{doc_name}' del proyecto?\nSe quitarán sus fragmentos y subrayados.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        if self.current_project:
            try:
                self.current_project.delete_document(doc_name)
            except Exception as exc:
                QMessageBox.critical(self, "Eliminar documento", f"No se pudo eliminar el archivo:\n{exc}")
                return

        self._remove_doc_from_groups(doc_name)
        parent = doc_item.parent()
        if parent:
            parent.removeChild(doc_item)
        else:
            idx = self.doc_tree.indexOfTopLevelItem(doc_item)
            if idx >= 0:
                self.doc_tree.takeTopLevelItem(idx)

        if self.current_doc == doc_name:
            self.current_doc = None
            self.text_area.clear()
            self.image_viewer.clear_image()
            self._show_text_viewer()

        self.highlights.pop(doc_name, None)
        self._remove_fragments_for_document(doc_name)

        self._rebuild_doc_groups_from_tree()
        self.save_project()
        QMessageBox.information(self, "Eliminar documento", f"Documento '{doc_name}' eliminado del proyecto.")

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

    def _on_code_tree_item_clicked(self, item, column):
        if column == 2:
            code_name = self._code_item_name(item)
            self.add_or_edit_memo(code_name)
            return
        if column == 1:
            self.show_code_fragments(item, column)

    def _on_code_tree_item_double_clicked(self, item, column):
        if column == 0:
            self._start_code_rename(item)

    def _on_code_tree_editor_closed(self, editor, hint):
        item = self.code_tree.currentItem()
        if item:
            QTimer.singleShot(0, lambda item=item: self._restore_code_item_label(item))

    def _start_code_rename(self, item):
        if not item:
            return
        code_name = self._code_item_name(item)
        self._code_tree_updating = True
        item.setText(0, code_name)
        self._code_tree_updating = False
        self.code_tree.setCurrentItem(item, 0)
        self.code_tree.editItem(item, 0)

    def _on_code_tree_item_changed(self, item, column):
        if self._code_tree_updating or column != 0:
            return

        old_name = self._code_item_name(item)
        new_name = item.text(0).strip()
        if new_name == old_name:
            self._restore_code_item_label(item)
            return

        if not new_name:
            self._restore_code_item_label(item)
            QMessageBox.warning(self, "Renombrar codigo", "El nombre del codigo no puede quedar vacio.")
            return

        if self._code_name_exists(new_name, exclude_item=item):
            self._restore_code_item_label(item)
            QMessageBox.warning(self, "Renombrar codigo", "Ya existe un codigo con ese nombre.")
            return

        self._rename_code(old_name, new_name, item)

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
        self.code_themes = []
        self.case_studies = []
        self.highlights = {}
        self.highlighted = []
        self.current_doc = None
        self._color_index = 0
        self.doc_groups = {"__root__": []}
        self.doc_tree.clear()
        self.code_tree.clear()
        self.text_area.clear()
        self.image_viewer.clear_image()
        self._show_text_viewer()
        self._image_selection_info = None
        self._clear_column_selection()
        if hasattr(self, "code_search_field"):
            self.code_search_field.clear()

    def save_project(self):
        if not self.current_project:
            return
        self._rebuild_doc_groups_from_tree()
        self._rebuild_codes_from_tree()
        documents = self._all_documents()
        self.current_project.save_state(self.codes, documents, self.highlights, self.doc_groups, self.code_themes, self.case_studies)

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
        self.code_themes = data.get("themes", [])
        self.case_studies = data.get("case_studies", [])
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
        if hasattr(self, "code_search_field"):
            self.filter_codes(self.code_search_field.text())

    def ensure_code_colors(self):
        for code in self.codes:
            if not code.get("color"):
                code["color"] = self.next_palette_color()

    def filter_codes(self, text):
        """Filtra el árbol de códigos por nombre."""
        term = (text or "").strip().lower()
        if not hasattr(self, "code_tree"):
            return

        def recurse(item):
            child_visible = False
            for i in range(item.childCount()):
                child_visible = recurse(item.child(i)) or child_visible
            item_match = not term or term in self._code_item_name(item).lower()
            visible = item_match or child_visible
            item.setHidden(not visible)
            if visible and term:
                item.setExpanded(True)
            return visible

        for idx in range(self.code_tree.topLevelItemCount()):
            recurse(self.code_tree.topLevelItem(idx))

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

    def _is_image_document(self, doc_name):
        if not doc_name:
            return False
        return doc_name.lower().endswith(tuple(Project.IMAGE_EXTENSIONS))

    def _is_current_doc_image(self):
        return self._is_image_document(self.current_doc)

    def _show_text_viewer(self):
        self.viewer_stack.setCurrentWidget(self.text_area)

    def _show_image_viewer(self):
        self.viewer_stack.setCurrentWidget(self.image_viewer)

    def _current_image_fragments(self):
        if not self.current_doc:
            return []
        fragments = []
        for code in self.codes:
            for frag in code.get("fragments", []):
                if frag.get("document") == self.current_doc and frag.get("type") == "image":
                    if not frag.get("color"):
                        frag["color"] = code.get("color", "#fff59d")
                    fragments.append(frag)
        return fragments

    def _image_selection_payload(self):
        rect = self.image_viewer.get_selection_rect()
        if not rect:
            return None
        size = self.image_viewer.image_size()
        if not size:
            return None
        return {"rect": rect, "image_size": size}

    def _on_image_selection_changed(self, rect):
        self._image_selection_info = rect

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
        self.filter_codes(self.code_search_field.text() if hasattr(self, "code_search_field") else "")

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
        item.setFlags(
            flags
            | Qt.ItemIsDragEnabled
            | Qt.ItemIsDropEnabled
            | Qt.ItemIsEnabled
            | Qt.ItemIsSelectable
            | Qt.ItemIsEditable
        )

    def _code_item_name(self, item):
        stored = item.data(0, Qt.UserRole + 1)
        if stored:
            return stored
        return item.text(0).strip()

    def _code_name_exists(self, name, exclude_item=None):
        iterator = QTreeWidgetItemIterator(self.code_tree)
        while iterator.value():
            item = iterator.value()
            if item is not exclude_item and self._code_item_name(item) == name:
                return True
            iterator += 1
        return any(code.get("name") == name for code in self.codes if not self.find_tree_item(code.get("name")))

    def _restore_code_item_label(self, item):
        if not item:
            return
        code_name = self._code_item_name(item)
        code_data = self.get_code_data(code_name)
        self._code_tree_updating = True
        if code_data:
            self.apply_code_item_color(item, code_data.get("color", "#fff59d"))
        else:
            item.setText(0, code_name)
        self._code_tree_updating = False

    def _rename_code(self, old_name, new_name, item):
        code_data = self.get_code_data(old_name)
        if not code_data:
            self._restore_code_item_label(item)
            return

        code_data["name"] = new_name
        for code in self.codes:
            if code.get("parent") == old_name:
                code["parent"] = new_name

        self._rename_code_in_themes(old_name, new_name)
        if self.memo_manager and hasattr(self.memo_manager, "rename_memo"):
            self.memo_manager.rename_memo(old_name, new_name)

        self._code_tree_updating = True
        item.setData(0, Qt.UserRole + 1, new_name)
        self.apply_code_item_color(item, code_data.get("color", "#fff59d"))
        self._code_tree_updating = False

        self._rebuild_codes_from_tree()
        self.save_project()

    def _rename_code_in_themes(self, old_name, new_name):
        for theme in self.code_themes:
            codes = theme.get("codes") or []
            theme["codes"] = [new_name if code == old_name else code for code in codes]

    # -------------------- SELECCIÓN COLUMNAR EN TEXTO --------------------
    def eventFilter(self, obj, event):
        if hasattr(self, "_titlebar_drag_widgets") and obj in self._titlebar_drag_widgets:
            if event.type() == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
                self.toggle_maximize()
                return True
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                if self.isMaximized():
                    return True
                if hasattr(event, "globalPosition"):
                    self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    return True
            elif event.type() == QEvent.MouseMove:
                if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
                    if self.isMaximized():
                        return True
                    if hasattr(event, "globalPosition"):
                        self.move(event.globalPosition().toPoint() - self._drag_pos)
                        return True
            elif event.type() == QEvent.MouseButtonRelease:
                self._drag_pos = None
                return True
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

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            if event.key() in (Qt.Key_Plus, Qt.Key_Equal):
                self.zoom_in()
                return
            if event.key() == Qt.Key_Minus:
                self.zoom_out()
                return
            if event.key() == Qt.Key_0:
                self.zoom_reset()
                return
        super().keyPressEvent(event)

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

    # -------------------- ZOOM --------------------
    def zoom_in(self):
        if self._is_current_doc_image():
            self.image_viewer.zoom_in()
            return
        if hasattr(self, "text_area"):
            self.text_area.zoomIn(1)
            self._zoom_level += 1

    def zoom_out(self):
        if self._is_current_doc_image():
            self.image_viewer.zoom_out()
            return
        if hasattr(self, "text_area"):
            self.text_area.zoomOut(1)
            self._zoom_level -= 1

    def zoom_reset(self):
        if self._is_current_doc_image():
            self.image_viewer.zoom_reset()
            return
        if not hasattr(self, "text_area"):
            return
        if self._zoom_level > 0:
            self.text_area.zoomOut(self._zoom_level)
        elif self._zoom_level < 0:
            self.text_area.zoomIn(-self._zoom_level)
        self._zoom_level = 0

    def _on_code_tree_drop(self):
        self._rebuild_codes_from_tree()
        self.save_project()


    # -------------------- IMPORTAR ARCHIVO --------------------
    def import_file(self):
        if not self.current_project:
            QMessageBox.warning(self, "Importar archivo", "Primero crea o abre un proyecto.")
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo",
            "",
            "Documentos o imagenes (*.txt *.pdf *.docx *.png *.jpg *.jpeg *.bmp *.gif *.tiff)",
        )
        if not file_path:
            return

        try:
            file_name, _ = self.current_project.import_document(file_path)
        except ValueError as err:
            QMessageBox.warning(self, "Importar archivo", str(err))
            return
        except Exception as err:
            QMessageBox.critical(self, "Importar archivo", f"No se pudo procesar el archivo:\n{err}")
            return

        existing = self._all_documents()
        folder = self._current_folder_name()
        new_item = None
        if file_name not in existing:
            self.doc_groups.setdefault(folder, []).append(file_name)
            new_item = self._add_doc_item(file_name, self._find_folder_item(folder))
        else:
            found = self.doc_tree.findItems(file_name, Qt.MatchExactly | Qt.MatchRecursive, 0)
            if found:
                new_item = found[0]

        self.current_doc = file_name
        if new_item:
            self.doc_tree.setCurrentItem(new_item)
            self.display_document(new_item)
        else:
            self.display_document(self.doc_tree.currentItem())
        self._rebuild_doc_groups_from_tree()
        self.save_project()
        QMessageBox.information(self, "Importar", f"Archivo '{file_name}' importado correctamente.")

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
            doc_path = self.current_project.get_document_path(self.current_doc)
            if self._is_image_document(self.current_doc):
                self._show_image_document(doc_path)
            else:
                self._show_text_viewer()
                text = self.current_project.read_document(self.current_doc)
                self.text_area.setPlainText(text)
        else:
            self.text_area.clear()
            self.image_viewer.clear_image()

        #  3. Restaurar los subrayados del documento nuevo
        self.highlighted = self.highlights.get(self.current_doc, []).copy()
        for frag in self.highlighted:
            if not frag.get("color"):
                frag["color"] = self._get_code_color(frag)
        self.restore_highlights()

    def _show_image_document(self, doc_path):
        if not os.path.exists(doc_path) or not self.image_viewer.load_image(doc_path):
            self._show_text_viewer()
            self.text_area.setPlainText("No se encontró la imagen en el proyecto.")
            return
        self._show_image_viewer()
        self.image_viewer.clear_selection()

    # -------------------- CARPETAS / DOCUMENTOS --------------------
    def doc_tree_context_menu(self, pos):
        menu = QMenu(self)
        add_folder_action = menu.addAction("Nueva carpeta")

        selected_item = self.doc_tree.itemAt(pos)
        move_action = None
        delete_action = None
        if selected_item and selected_item.data(0, Qt.UserRole) == "doc":
            move_action = menu.addAction("Mover a carpeta…")
            delete_action = menu.addAction("Eliminar documento")

        action = menu.exec(self.doc_tree.viewport().mapToGlobal(pos))
        if action == add_folder_action:
            self.create_document_folder()
        elif action == move_action:
            self.move_document_to_folder(selected_item)
        elif action == delete_action:
            self.delete_document(selected_item)

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

    def _remove_fragments_for_document(self, doc_name):
        """Elimina los fragmentos asociados a un documento y actualiza conteos."""
        for code in self.codes:
            frags = code.get("fragments", [])
            frags = [f for f in frags if f.get("document") != doc_name]
            code["fragments"] = frags
            code["count"] = len(frags)
            self.update_code_count(code["name"], code["count"])


    # -------------------- FUNCIONES DE DOCUMENTO --------------------
    def open_document(self, file_path):
        if not self.current_project:
            return

        # Guardar subrayados del documento actual
        if self.current_doc:
            self.save_current_highlights()
    
        self._clear_column_selection()
        self.current_doc = os.path.basename(file_path)
        if self.current_project:
            doc_path = self.current_project.get_document_path(self.current_doc)
            if self._is_image_document(self.current_doc):
                self._show_image_document(doc_path)
            else:
                self._show_text_viewer()
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
        if self._is_current_doc_image():
            self._image_context_menu(global_pos=self.image_viewer.mapToGlobal(pos))
            return
        cursor = self.text_area.textCursor()
        selected_text = cursor.selectedText()
        selection_start = cursor.selectionStart()
        selection_end = cursor.selectionEnd()
        self._clear_column_selection()
        menu = QMenu()

        create_code_action = None
        create_subcode_action = None
        create_live_code_action = None
        if selected_text and selection_start != selection_end and self.current_doc:
            create_code_action = menu.addAction("⚡ Crear nuevo código")
            create_subcode_action = menu.addAction("➔ Crear subcódigo")
            create_live_code_action = menu.addAction("Codificar in vivo")

            if self.codes:
                add_to_existing = menu.addMenu("📎 Agregar a código existente")
                for c in self.codes:
                    act = add_to_existing.addAction(c["name"])
                    act.triggered.connect(
                        lambda checked=False, name=c["name"], text=selected_text,
                        start=selection_start, end=selection_end:
                        self.add_to_existing_code(name, text, start, end)
                    )

        if menu.actions():
            menu.addSeparator()
        zoom_in_action = menu.addAction("Aumentar zoom")
        zoom_out_action = menu.addAction("Disminuir zoom")
        zoom_reset_action = menu.addAction("Restablecer zoom")

        action = menu.exec(self.text_area.mapToGlobal(pos))
        if action == create_code_action:
            self.create_new_code(selected_text, selection_start, selection_end)
        elif action == create_subcode_action:
            self.create_subcode(selected_text, selection_start, selection_end)
        elif action == create_live_code_action:
            auto_label = self._suggest_live_code_name(selected_text)
            self.create_new_code(selected_text, selection_start, selection_end, code_label=auto_label)
        elif action == zoom_in_action:
            self.zoom_in()
        elif action == zoom_out_action:
            self.zoom_out()
        elif action == zoom_reset_action:
            self.zoom_reset()

    def _image_context_menu(self, scene_pos=None, global_pos=None, target_fragment=None):
        selection = self._image_selection_payload()
        has_selection = bool(selection and selection.get("rect"))
        menu = QMenu()
        create_code_action = menu.addAction("Crear nuevo codigo para zona" if has_selection else "Crear nuevo codigo para imagen")
        create_subcode_action = menu.addAction("Crear subcodigo para zona" if has_selection else "Crear subcodigo para imagen")
        if self.codes:
            add_to_existing = menu.addMenu("Agregar a codigo existente")
            for c in self.codes:
                code_name = c["name"]
                act = add_to_existing.addAction(code_name)
                act.triggered.connect(lambda checked=False, name=code_name: self.add_image_to_existing(name))

        if menu.actions():
            menu.addSeparator()
        zoom_in_action = menu.addAction("Aumentar zoom")
        zoom_out_action = menu.addAction("Disminuir zoom")
        zoom_reset_action = menu.addAction("Restablecer zoom")

        menu_pos = global_pos or self.mapToGlobal(self.rect().center())
        action = menu.exec(menu_pos)
        if action == create_code_action:
            note = self._prompt_image_note(
                "Nuevo codigo (imagen)",
                "Descripcion del fragmento (opcional):",
                default_text="Zona de imagen" if has_selection else "Imagen completa",
            )
            if note is None:
                return
            self.create_new_code("", None, None, is_image=True, note=note, image_selection=selection)
        elif action == create_subcode_action:
            self.create_subcode_for_image(selection)
        elif action == zoom_in_action:
            self.zoom_in()
        elif action == zoom_out_action:
            self.zoom_out()
        elif action == zoom_reset_action:
            self.zoom_reset()

    def _prompt_image_note(self, title, label, default_text="Imagen completa"):
        note, ok = QInputDialog.getText(self, title, label, text=default_text)
        if not ok:
            return None
        return note.strip() or default_text

    def add_image_to_existing(self, code_name, image_selection=None):
        selection = image_selection or self._image_selection_payload()
        has_selection = bool(selection and selection.get("rect"))
        note = self._prompt_image_note(
            "Agregar a codigo",
            "Descripcion del fragmento (opcional):",
            default_text="Zona de imagen" if has_selection else "Imagen completa",
        )
        if note is None:
            return
        self.add_to_existing_code(code_name, note, None, None, is_image=True, note=note, image_selection=selection)

    def create_subcode_for_image(self, image_selection=None):
        iterator = QTreeWidgetItemIterator(self.code_tree)
        code_names = []
        while iterator.value():
            code_names.append(self._code_item_name(iterator.value()))
            iterator += 1
        if not code_names:
            QMessageBox.warning(self, "Subcodigo", "Primero crea un codigo principal.")
            return

        parent_name, ok = QInputDialog.getItem(self, "Subcodigo", "Selecciona codigo padre:", code_names, 0, False)
        if not ok or not parent_name:
            return

        sub_label, ok = QInputDialog.getText(self, "Nuevo Subcodigo", "Nombre del subcodigo:")
        if not ok or not sub_label:
            return

        selection = image_selection or self._image_selection_payload()
        has_selection = bool(selection and selection.get("rect"))
        note = self._prompt_image_note(
            "Nuevo fragmento (imagen)",
            "Descripcion del fragmento (opcional):",
            default_text="Zona de imagen" if has_selection else "Imagen completa",
        )
        if note is None:
            return

        parent_item = self.find_tree_item(parent_name)
        if parent_item:
            self.create_new_code("", None, None, parent_item, sub_label, is_image=True, note=note, image_selection=selection)

    def add_code_from_toolbar(self):
        self.prompt_add_code()

    def prompt_add_code(self, parent_item=None):
        if not self.current_project:
            QMessageBox.warning(self, "Agregar codigo", "Primero abre o crea un proyecto.")
            return

        parent_name = self._code_item_name(parent_item) if parent_item else None
        prompt_title = "Agregar subcodigo" if parent_name else "Agregar codigo"
        prompt_label = f"Nombre del codigo hijo de '{parent_name}':" if parent_name else "Nombre del codigo:"
        code_label, ok = QInputDialog.getText(self, prompt_title, prompt_label)
        if not ok:
            return

        code_label = (code_label or "").strip()
        if not code_label:
            QMessageBox.warning(self, "Agregar codigo", "El nombre del codigo no puede quedar vacio.")
            return

        if self._code_name_exists(code_label):
            QMessageBox.warning(self, "Agregar codigo", "Ya existe un codigo con ese nombre.")
            return

        parent_color = None
        if parent_name:
            parent_data = self.get_code_data(parent_name)
            parent_color = parent_data.get("color") if parent_data else None

        color_hex = self.ask_color_from_palette(parent_color or self.next_palette_color())
        self._append_code_entry(code_label, parent_item=parent_item, color_hex=color_hex)
        self._rebuild_codes_from_tree()
        self.save_project()

    def _build_fragment(self, text, start, end, color_hex, is_image=False, image_selection=None, note=None):
        fragment = {
            "text": text,
            "document": self.current_doc,
            "start": start,
            "end": end,
            "color": color_hex,
            "type": "image" if is_image else "text",
        }
        if is_image:
            selection = image_selection or {}
            fragment["text"] = text or "<IMAGE>"
            fragment["comment"] = note or text or ""
            rect = selection.get("rect")
            image_size = selection.get("image_size")
            if rect:
                fragment["rect"] = rect
                fragment["area"] = int(rect.get("w", 0) * rect.get("h", 0))
            if image_size:
                fragment["image_size"] = image_size
                total = max(1, image_size.get("w", 0) * image_size.get("h", 0))
                fragment["coverage"] = round(fragment.get("area", 0) / total, 6)
        return fragment

    def create_new_code(self, selected_text, start, end, parent_item=None, code_label=None, is_image=False, note=None, image_selection=None):
        if not self.current_doc:
            QMessageBox.warning(self, "Nuevo codigo", "Selecciona un documento antes de codificar.")
            return
        if not is_image and (start is None or end is None or start == end):
            return

        if not code_label:
            prompt_title = "Nuevo Codigo (imagen)" if is_image else "Nuevo Codigo"
            code_label, ok = QInputDialog.getText(self, prompt_title, "Nombre del codigo:")
            if not ok or not code_label:
                return
        code_label = code_label.strip()
        if not code_label:
            QMessageBox.warning(self, "Nuevo codigo", "El nombre del codigo no puede quedar vacio.")
            return
        if self._code_name_exists(code_label):
            QMessageBox.warning(self, "Nuevo codigo", "Ya existe un codigo con ese nombre.")
            return

        parent_name = self._code_item_name(parent_item) if parent_item else None
        parent_color = None
        if parent_name:
            parent_data = self.get_code_data(parent_name)
            parent_color = parent_data.get("color") if parent_data else None

        suggested_color = parent_color or self.next_palette_color()
        color_hex = self.ask_color_from_palette(suggested_color)

        if is_image:
            selection = image_selection or self._image_selection_payload()
            note_text = note if note is not None else self._prompt_image_note("Nuevo fragmento (imagen)", "Descripcion del fragmento (opcional):")
            if note_text is None:
                return
            selected_text = note_text
            start = None
            end = None
        else:
            selection = None

        fragment = self._build_fragment(selected_text, start, end, color_hex, is_image=is_image, image_selection=selection, note=note)
        self._append_code_entry(code_label, parent_item=parent_item, color_hex=color_hex, fragment=fragment)

        if not is_image:
            self.highlight_fragment(fragment, QColor(color_hex))
        else:
            self.image_viewer.clear_selection()
        self.save_current_highlights()
        self._rebuild_codes_from_tree()
        self.save_project()

    def _append_code_entry(self, code_label, parent_item=None, color_hex=None, fragment=None):
        parent_name = self._code_item_name(parent_item) if parent_item else None
        stored_color = color_hex or self.next_palette_color()
        fragments = [fragment] if fragment else []
        count = len(fragments)

        code_item = QTreeWidgetItem([code_label, str(count), ""])
        code_item.setData(0, Qt.UserRole + 1, code_label)
        self._configure_code_item(code_item)
        if parent_item:
            parent_item.addChild(code_item)
            parent_item.setExpanded(True)
        else:
            self.code_tree.addTopLevelItem(code_item)
        self.apply_code_item_color(code_item, stored_color)

        self.codes.append({
            "name": code_label,
            "parent": parent_name,
            "memo": "",
            "color": stored_color,
            "count": count,
            "fragments": fragments,
        })
        return code_item


    def add_to_existing_code(self, code_name, selected_text, start, end, is_image=False, note=None, image_selection=None):
        if not self.current_doc:
            return

        code_data = self.get_code_data(code_name)
        if not code_data:
            return

        if is_image:
            selection = image_selection or self._image_selection_payload()
            note_text = note if note is not None else self._prompt_image_note("Agregar a codigo", "Descripcion del fragmento (opcional):")
            if note_text is None:
                return
            selected_text = note_text
            start = None
            end = None
        else:
            selection = None

        color_hex = code_data.get("color", "#fff59d")
        fragment = self._build_fragment(selected_text, start, end, color_hex, is_image=is_image, image_selection=selection, note=note)

        code_data.setdefault("fragments", []).append(fragment)
        code_data["count"] = len(code_data["fragments"])
        self.update_code_count(code_name, code_data["count"])
        if not is_image:
            self.highlight_fragment(fragment, QColor(color_hex))
        else:
            self.image_viewer.clear_selection()
        self.save_current_highlights()
        self.save_project()


    def highlight_fragment(self, fragment, color=None):
        """Resalta un fragmento solo en su documento correspondiente."""
        if fragment.get("document") != self.current_doc:
            return
        if fragment.get("type") == "image" or self._is_current_doc_image():
            if self._is_current_doc_image():
                self.image_viewer.focus_fragment(fragment)
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

    def open_themes_categories(self):
        if not self.current_project:
            QMessageBox.information(self, "Temas y categorÃ­as", "Primero abre o crea un proyecto.")
            return
        codes = [c.get("name") for c in self.codes if c.get("name")]
        dialog = ThemesCategoriesDialog(codes, self.code_themes, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.code_themes = dialog.get_themes_data()
            self.save_project()

    def open_compare_dialog(self):
        if not self.current_project:
            QMessageBox.information(self, "Comparar", "Primero abre o crea un proyecto.")
            return
        docs = self._all_documents()
        if len(docs) < 2:
            QMessageBox.information(self, "Comparar", "Necesitas al menos dos documentos para comparar.")
            return
        left = self.current_doc or (docs[0] if docs else None)
        right = None
        if len(docs) >= 2:
            right = docs[1] if docs[0] == left else docs[0]
        dialog = CompareDialog(self.current_project, self.codes, left_doc=left, right_doc=right, parent=self)
        dialog.exec()

    def open_code_matrix(self):
        if not self.current_project:
            QMessageBox.information(self, "Code Matrix", "Primero abre o crea un proyecto.")
            return
        docs = self._all_documents()
        if not docs:
            QMessageBox.information(self, "Code Matrix", "No hay documentos para mostrar.")
            return
        if not self.codes:
            QMessageBox.information(self, "Code Matrix", "No hay códigos creados aún.")
            return
        dialog = CodeMatrixDialog(docs, self.codes, current_doc=self.current_doc, parent=self)
        dialog.exec()

    def open_wordcloud_dialog(self):
        if not self.current_project:
            QMessageBox.information(self, "Nube de palabras", "Primero abre o crea un proyecto.")
            return
        docs = self._all_documents()
        if not docs:
            QMessageBox.information(self, "Nube de palabras", "No hay documentos para analizar.")
            return
        dialog = WordCloudDialog(self.current_project, docs, parent=self)
        dialog.exec()

    def open_themes_analysis(self):
        if not self.current_project:
            QMessageBox.information(self, "Analisis de temas", "Primero abre o crea un proyecto.")
            return
        if not self.code_themes:
            QMessageBox.information(self, "Analisis de temas", "No hay temas o categorias creadas.")
            return
        dialog = ThemesAnalysisDialog(self.codes, self.code_themes, self.current_project, parent=self)
        dialog.exec()

    def open_case_study(self):
        if not self.current_project:
            QMessageBox.information(self, "Estudio de casos", "Primero abre o crea un proyecto.")
            return
        docs = self._all_documents()
        if not docs:
            QMessageBox.information(self, "Estudio de casos", "No hay documentos para analizar.")
            return
        if not self.codes:
            QMessageBox.information(self, "Estudio de casos", "No hay cÃ³digos creados aÃºn.")
            return
        dialog = CaseStudyDialog(
            self.current_project,
            self.codes,
            docs,
            self.case_studies,
            self.doc_groups,
            parent=self,
        )
        dialog.exec()
        if dialog.updated:
            self.case_studies = dialog.get_case_studies()
            self.save_project()

    # -------------------- EXPORTAR SISTEMA DE CÓDIGOS --------------------
    def export_code_tree(self):
        if not self.codes:
            QMessageBox.information(self, "Exportar libro de códigos", "No hay códigos para exportar.")
            return

        excel_deps = self._load_excel_export_dependencies("Exportar libro de códigos")
        if not excel_deps:
            return
        Workbook, _, _, _ = excel_deps

        path = self._ask_excel_export_path("Guardar libro de códigos", "libro_de_codigos.xlsx")
        if not path:
            return

        rows = self._collect_code_rows_for_export()
        if not rows:
            QMessageBox.information(self, "Exportar libro de códigos", "No se encontraron códigos en el árbol.")
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Libro de códigos"
        self._write_codebook_sheet(ws, rows, title_text="Libro de códigos", frequency_label="Frecuencia")
        self._save_excel_workbook(wb, path, "Exportar libro de códigos", "Libro de códigos exportado en:")

    def export_code_fragments(self):
        if not self.codes:
            QMessageBox.information(self, "Exportar fragmentos", "No hay códigos para exportar.")
            return

        excel_deps = self._load_excel_export_dependencies("Exportar fragmentos")
        if not excel_deps:
            return
        Workbook, _, _, _ = excel_deps

        rows = self._collect_code_rows_for_export(text_only=True)
        if not rows:
            QMessageBox.information(self, "Exportar fragmentos", "No hay fragmentos de texto asociados a códigos o subcódigos.")
            return

        dialog = ExportCodeSelectionDialog(rows, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return

        selected_names = dialog.selected_code_names()
        if not selected_names:
            QMessageBox.information(self, "Exportar fragmentos", "Selecciona al menos un código o subcódigo.")
            return

        selected_rows = self._collect_code_rows_for_export(selected_names=selected_names, text_only=True)
        if not selected_rows:
            QMessageBox.information(self, "Exportar fragmentos", "Los códigos seleccionados no tienen fragmentos de texto para exportar.")
            return

        path = self._ask_excel_export_path("Guardar fragmentos", "fragmentos_codificados.xlsx")
        if not path:
            return

        fragment_rows = self._collect_text_fragments_for_export(selected_names)
        wb = Workbook()
        ws_codes = wb.active
        ws_codes.title = "Libro de códigos"
        self._write_codebook_sheet(ws_codes, selected_rows, title_text="Libro de códigos", frequency_label="Fragmentos")

        ws_fragments = wb.create_sheet("Fragmentos")
        self._write_fragments_sheet(ws_fragments, fragment_rows)

        self._save_excel_workbook(
            wb,
            path,
            "Exportar fragmentos",
            "Libro de códigos y fragmentos exportados en:",
        )

    def _load_excel_export_dependencies(self, dialog_title):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment
        except ImportError:
            QMessageBox.critical(
                self,
                dialog_title,
                "Falta la dependencia 'openpyxl'. Agrega 'openpyxl' a requirements e instálala para exportar.",
            )
            return None
        return Workbook, Font, PatternFill, Alignment

    def _ask_excel_export_path(self, dialog_title, default_filename):
        save_dir = self.working_dir or os.getcwd()
        default_path = os.path.join(save_dir, default_filename)
        path, _ = QFileDialog.getSaveFileName(
            self,
            dialog_title,
            default_path,
            "Excel (*.xlsx)",
        )
        return path

    def _save_excel_workbook(self, workbook, path, dialog_title, success_message):
        try:
            workbook.save(path)
            QMessageBox.information(self, dialog_title, f"{success_message}\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, dialog_title, f"No se pudo guardar el archivo:\n{exc}")

    def _write_codebook_sheet(self, worksheet, rows, title_text="Libro de códigos", frequency_label="Frecuencia"):
        _, Font, PatternFill, Alignment = self._load_excel_export_dependencies(title_text)
        header = [title_text, "", "", "", "Memo", frequency_label]
        worksheet.append(header)

        header_fill = PatternFill(start_color="5d9bd3", end_color="5d9bd3", fill_type="solid")
        data_fill = PatternFill(start_color="f6f8fb", end_color="f6f8fb", fill_type="solid")
        bold = Font(bold=True)
        memo_col = 5
        freq_col = 6

        for col_idx in range(1, len(header) + 1):
            cell = worksheet.cell(row=1, column=col_idx)
            cell.font = bold
            cell.fill = header_fill
            cell.alignment = Alignment(vertical="center")

        for row_data in rows:
            level = row_data["level"]
            total_cols = max(freq_col, 1 + level)
            row = ["" for _ in range(total_cols)]
            name_col = 1 + level
            row[name_col - 1] = row_data["name"]
            if memo_col - 1 >= len(row):
                row.extend([""] * (memo_col - len(row)))
            row[memo_col - 1] = row_data.get("memo") or ""
            if freq_col - 1 >= len(row):
                row.extend([""] * (freq_col - len(row)))
            row[freq_col - 1] = row_data.get("freq", "")
            worksheet.append(row)
            current_row = worksheet.max_row
            for col_idx in range(1, freq_col + 1):
                cell = worksheet.cell(row=current_row, column=col_idx)
                cell.fill = data_fill
                cell.alignment = Alignment(vertical="top", wrap_text=True)

        for col_name in ("A", "B", "C", "D"):
            worksheet.column_dimensions[col_name].width = 36
        worksheet.column_dimensions["E"].width = 48
        worksheet.column_dimensions["F"].width = 14

        for row in worksheet.iter_rows(min_row=1, max_row=worksheet.max_row, min_col=1, max_col=freq_col):
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)

    def _write_fragments_sheet(self, worksheet, fragment_rows):
        _, Font, PatternFill, Alignment = self._load_excel_export_dependencies("Exportar fragmentos")
        header = ["Código", "Documento", "Fragmento", "Memo"]
        worksheet.append(header)

        header_fill = PatternFill(start_color="5d9bd3", end_color="5d9bd3", fill_type="solid")
        data_fill = PatternFill(start_color="f6f8fb", end_color="f6f8fb", fill_type="solid")
        bold = Font(bold=True)

        for col_idx in range(1, len(header) + 1):
            cell = worksheet.cell(row=1, column=col_idx)
            cell.font = bold
            cell.fill = header_fill
            cell.alignment = Alignment(vertical="center")

        for fragment in fragment_rows:
            worksheet.append([
                fragment.get("code_name", ""),
                fragment.get("document", ""),
                fragment.get("text", ""),
                fragment.get("memo", ""),
            ])
            current_row = worksheet.max_row
            for col_idx in range(1, len(header) + 1):
                cell = worksheet.cell(row=current_row, column=col_idx)
                cell.fill = data_fill
                cell.alignment = Alignment(vertical="top", wrap_text=True)

        worksheet.column_dimensions["A"].width = 28
        worksheet.column_dimensions["B"].width = 28
        worksheet.column_dimensions["C"].width = 100
        worksheet.column_dimensions["D"].width = 48

    def _collect_code_rows_for_export(self, selected_names=None, text_only=False):
        """Devuelve filas del árbol de códigos respetando el orden visual actual."""
        if not self.code_tree:
            return []

        selected_set = set(selected_names or [])
        use_filter = bool(selected_set)
        rows = []

        def memo_for(name):
            if self.memo_manager:
                return self.memo_manager.get_memo(name)
            code_data = self.get_code_data(name)
            return code_data.get("memo") if code_data else ""

        def fragments_for(code_data):
            fragments = list((code_data or {}).get("fragments", []) or [])
            if text_only:
                fragments = [frag for frag in fragments if (frag.get("type") or "text") != "image"]
            return fragments

        def freq_for(code_data):
            if not code_data:
                return ""
            if text_only:
                return len(fragments_for(code_data))
            if "count" in code_data:
                return code_data.get("count")
            return len(fragments_for(code_data))

        def walk(item, level):
            name = self._code_item_name(item)
            code_data = self.get_code_data(name)
            include_row = (not use_filter or name in selected_set) and (not text_only or freq_for(code_data) > 0)
            if include_row:
                rows.append({
                    "level": level,
                    "name": name,
                    "memo": memo_for(name) or "",
                    "freq": freq_for(code_data),
                })
            for idx in range(item.childCount()):
                walk(item.child(idx), level + 1)

        for idx in range(self.code_tree.topLevelItemCount()):
            walk(self.code_tree.topLevelItem(idx), 0)
        return rows

    def _collect_text_fragments_for_export(self, selected_names):
        fragments = []
        for row in self._collect_code_rows_for_export(selected_names=selected_names, text_only=True):
            code_name = row["name"]
            code_data = self.get_code_data(code_name)
            if not code_data:
                continue
            for fragment in code_data.get("fragments", []) or []:
                if (fragment.get("type") or "text") == "image":
                    continue
                fragments.append({
                    "code_name": code_name,
                    "document": fragment.get("document", ""),
                    "text": self._resolve_fragment_export_text(fragment),
                    "memo": row.get("memo", ""),
                })
        return fragments

    def _resolve_fragment_export_text(self, fragment):
        text = fragment.get("text") or ""
        if text and text != "<IMAGE>":
            return text.replace("\u2029", "\n").replace("\u2028", "\n")

        if not self.current_project:
            return ""

        doc_name = fragment.get("document")
        if not doc_name or self._is_image_document(doc_name):
            return ""

        start = fragment.get("start")
        end = fragment.get("end")
        if start is None or end is None or end <= start:
            return ""

        doc_text = self.current_project.read_document(doc_name)
        if end > len(doc_text):
            return ""
        return doc_text[start:end].replace("\u2029", "\n").replace("\u2028", "\n")

    # -------------------- DESTACADO --------------------
    def highlight_selection(self, cursor, color):
        fmt = QTextCharFormat()
        fmt.setBackground(self._adjust_highlight_color(color))
        cursor.mergeCharFormat(fmt)

    def restore_highlights(self):
        """Aplica los fragmentos de self.highlighted en el text_area."""
        if not self.current_doc:
            return
        if self._is_current_doc_image():
            self.image_viewer.set_fragments(self.highlighted)
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
        if self._is_current_doc_image():
            self.image_viewer.set_fragments(doc_fragments)


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

    def _suggest_live_code_name(self, text):
        words = (text or "").split()
        trimmed = " ".join(words[:10]).strip()
        return trimmed if trimmed else "Código in vivo"

    def toggle_code_tree_expansion(self):
        expand = not self._codes_expanded
        self._set_tree_items_expanded(expand)
        self._codes_expanded = expand
        self.btn_toggle_code_expand.setText("Contraer" if expand else "Expandir")

    def _set_tree_items_expanded(self, expand=True):
        def walk(item):
            item.setExpanded(expand)
            for i in range(item.childCount()):
                walk(item.child(i))
        for idx in range(self.code_tree.topLevelItemCount()):
            walk(self.code_tree.topLevelItem(idx))

class ExportCodeSelectionDialog(QDialog):
    def __init__(self, code_rows, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exportar fragmentos")
        self.resize(520, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Selecciona los códigos o subcódigos cuyos fragmentos deseas exportar:"))

        controls = QHBoxLayout()
        btn_select_all = QPushButton("Seleccionar todo")
        btn_clear = QPushButton("Limpiar selección")
        btn_select_all.clicked.connect(lambda: self._set_all_items(Qt.Checked))
        btn_clear.clicked.connect(lambda: self._set_all_items(Qt.Unchecked))
        controls.addWidget(btn_select_all)
        controls.addWidget(btn_clear)
        controls.addStretch()
        layout.addLayout(controls)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        layout.addWidget(self.list_widget, 1)

        for row in code_rows:
            item = QListWidgetItem(f"{'    ' * row['level']}{row['name']} ({row['freq']})")
            item.setData(Qt.UserRole, row["name"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.list_widget.addItem(item)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _set_all_items(self, state):
        for index in range(self.list_widget.count()):
            self.list_widget.item(index).setCheckState(state)

    def selected_code_names(self):
        selected = []
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))
        return selected


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
