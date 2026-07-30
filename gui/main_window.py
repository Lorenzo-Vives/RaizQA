import os
import shutil
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox, QInputDialog, QFrame, QLineEdit, QSizeGrip,
    QTreeWidget, QTreeWidgetItem, QMenu, QDialog, QHeaderView, QTreeWidgetItemIterator,
    QGridLayout, QDialogButtonBox, QFileIconProvider, QAbstractItemView, QTextEdit,
    QStackedWidget
)
from PySide6.QtGui import (QAction, QColor, QTextCursor, QTextCharFormat, QPainter, QPixmap, QIcon, QPalette,
                           QShortcut, QKeySequence)
from PySide6.QtCore import Qt, QTimer, QPoint, QEvent, Signal
from docx import Document

from gui.widgets.local_search import LocalSearchWidget
from gui.widgets.document_editor import DocumentEditorController
from gui.widgets.actions_panel import ActionsPanelWidget

from gui.dialogs.memo_dialog import MemoDialog
from gui.dialogs.fragments_dialog import CodeFragmentsDialog
from gui.dialogs.diary_dialog import DiaryDialog
from gui.dialogs.compare_dialog import CompareDialog
from gui.dialogs.code_matrix_dialog import CodeMatrixDialog
from gui.dialogs.wordcloud_dialog import WordCloudDialog
from gui.dialogs.themes_categories_dialog import ThemesCategoriesDialog
from gui.dialogs.themes_analysis_dialog import ThemesAnalysisDialog
from gui.dialogs.case_study_dialog import CaseStudyDialog
from gui.dialogs.new_code_dialog import NewCodeDialog
from gui.dialogs.loading_dialog import LoadingDialog

from gui.document_tree import DocumentTree
from gui.code_tree import CodeTree
from gui.image_viewer import ImageDocumentViewer
from gui.dialogs.code_viewer_window import CodeViewerWindow  # Absolute import desde root
from core.project import Project
from gui.theme import get_theme

class RaizQAGUI(QMainWindow):
    # ==========================================
    # SEÑALES DE LA UI AL BACKEND
    # ==========================================
    signal_req_global_search = Signal(str, object, list, object)
    signal_req_export_diary = Signal(str, str, str)
    signal_req_export_code_tree = Signal(list, str)
    signal_req_export_code_fragments = Signal(list, list, str)
    signal_req_set_project = Signal(object)
    
    signal_req_export_project = Signal(str)
    signal_req_import_project = Signal(str, str)
    signal_req_export_exchange = Signal(list, list, dict, str)
    signal_req_import_exchange = Signal(str, dict)
    signal_req_merge_projects = Signal(str, dict)

    # SEÑALES CRUD EDDs
    signal_req_add_code = Signal(str, str, str, str) # code_label, hexcolor, memo, parent_name
    signal_req_delete_code = Signal(str, bool) # code_name, cascade
    signal_req_update_code = Signal(str, str, str, str)
    signal_req_add_fragment = Signal(str, str, object)
    signal_req_update_document = Signal(str, str)
    signal_req_save_all = Signal(dict)
    
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
        self._apply_initial_geometry() # en lugar de setear un tamaño fijo
                                       # se consulta tamaño de pantalla y se centra la ventana
        self.current_project = None
        self.memo_manager = None
        self.working_dir = None
        self.current_doc = None
        
        # Cachés locales de las EDDs para que los diálogos los lean rápido
        self.codes_dict = {}
        self.themes_dict = {}
        
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

        self.has_unsaved_changes = False

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
        self.actions_panel = ActionsPanelWidget(self)
        
        # Conexiones Inicio
        self.actions_panel.sig_working_dir.connect(self.select_working_dir)
        self.actions_panel.sig_create_project.connect(self.create_project)
        self.actions_panel.sig_open_project.connect(self.open_project)
        self.actions_panel.sig_merge_projects.connect(self.merge_projects)
        self.actions_panel.sig_import_doc.connect(self.import_file)
        self.actions_panel.sig_export_rqa.connect(self.export_project_rqa)
        self.actions_panel.sig_import_rqa.connect(self.import_project_rqa)
        self.actions_panel.sig_export_rex.connect(self.export_project_rex)
        self.actions_panel.sig_import_rex.connect(self.import_project_rex)
        
        # Conexiones Códigos
        self.actions_panel.sig_add_code.connect(self.add_code_from_toolbar)
        self.actions_panel.sig_view_codes.connect(self.open_code_viewer)
        self.actions_panel.sig_themes_categories.connect(self.open_themes_categories)
        self.actions_panel.sig_diary.connect(self.open_diary)
        
        # Conexiones Exportaciones (Menú Desplegable)
        self.actions_panel.sig_export_code_tree.connect(self.export_code_tree)
        self.actions_panel.sig_export_fragments.connect(self.export_code_fragments)
        self.actions_panel.sig_export_diary.connect(self.export_diary)
        
        # Conexiones Análisis
        self.actions_panel.sig_compare.connect(self.open_compare_dialog)
        self.actions_panel.sig_code_matrix.connect(self.open_code_matrix)
        self.actions_panel.sig_wordcloud.connect(self.open_wordcloud_dialog)
        self.actions_panel.sig_themes_analysis.connect(self.open_themes_analysis)
        self.actions_panel.sig_case_study.connect(self.open_case_study)
        
        self.actions_panel.sig_toggle_theme.connect(self.toggle_theme)
        
        content_wrapper_layout.addWidget(self.actions_panel)

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
        self.doc_tree.setObjectName("DocTree")
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
        self.code_tree.setObjectName("CodeTree")
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
        
        # NUEVO: Botones para la edición del documento
        self.btn_edit_doc = QPushButton("✏️ Editar")
        self.btn_save_doc = QPushButton("💾 Guardar")
        self.btn_cancel_doc = QPushButton("❌ Cancelar")

        for btn in [self.btn_edit_doc, self.btn_save_doc, self.btn_cancel_doc]:
            btn.setObjectName("GhostButton")
            btn.setCursor(Qt.PointingHandCursor)
            tab_bar_layout.addWidget(btn)
            
        tab_bar_layout.addStretch()
        text_layout.addWidget(tab_bar)

        self.viewer_stack = QStackedWidget()

        self.text_area = QTextEdit()
        self.text_area.setObjectName("TextArea")
        self.text_area.setReadOnly(True)
        self.text_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_area.customContextMenuRequested.connect(self.text_context_menu)
        self.text_area.installEventFilter(self)
        self.viewer_stack.addWidget(self.text_area)

        # NUEVO: Inicializar el controlador del editor
        self.doc_editor_controller = DocumentEditorController(
            self.text_area, self.btn_edit_doc, self.btn_save_doc, self.btn_cancel_doc
        )
        self.doc_editor_controller.signal_save_requested.connect(self.signal_req_update_document.emit)

        self.image_viewer = ImageDocumentViewer(self)
        self.image_viewer.selectionChanged.connect(self._on_image_selection_changed)
        self.image_viewer.contextMenuRequested.connect(self._image_context_menu)
        self.viewer_stack.addWidget(self.image_viewer)

        text_layout.addWidget(self.viewer_stack, 1)
        content_layout.addWidget(text_card, 62)

        # -------------------- BUSCADOR LOCAL MODULAR (CTRL+F) --------------------
        self.local_search_widget = LocalSearchWidget(self.text_area, parent=self)
        self.local_search_widget.setVisible(False)
        text_layout.addWidget(self.local_search_widget)
        
        # Conectar las señales
        self.local_search_widget.selections_updated.connect(self._update_all_extra_selections)
        self.local_search_widget.closed.connect(lambda: self.text_area.setFocus())
        
        self._ls_extra_selections = [] # Guardará las selecciones del buscador

        # Atajo de teclado nativo (Cmd+F o Ctrl+F)
        self.shortcut_find = QShortcut(QKeySequence.Find, self)
        self.shortcut_find.activated.connect(self._invoke_local_search)

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

    def export_project_rqa(self):
        if not self.current_project:
            QMessageBox.warning(self, "Exportar Proyecto", "Primero abre o crea un proyecto.")
            return
            
        default_name = f"{self.current_project.name}.rqa"
        default_path = os.path.join(self.working_dir or os.path.expanduser("~"), default_name)
        
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Proyecto (.rqa)", default_path, "RaizQA Project (*.rqa)")
        if not path:
            return
            
        self.signal_req_export_project.emit(path)
        self.actions_panel.btn_teamwork.setText("⏳ Exportando...")
        self.actions_panel.btn_teamwork.setEnabled(False)
        self._show_loading_dialog("Exportar Proyecto", "Comprimiendo y exportando proyecto, por favor espera...")

    def import_project_rqa(self):
        if not self.working_dir:
            QMessageBox.warning(self, "Importar Proyecto", "Primero debes seleccionar un Working Directory (WD).")
            return
            
        reply = QMessageBox.warning(
            self, 
            "Importar Proyecto", 
            "El proyecto importado reemplazará cualquier proyecto existente con el mismo nombre en tu directorio de trabajo.\n\n¿Deseas continuar?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
            
        path, _ = QFileDialog.getOpenFileName(self, "Importar Proyecto (.rqa)", self.working_dir, "RaizQA Project (*.rqa)")
        if not path:
            return
            
        self.signal_req_import_project.emit(path, self.working_dir)
        self.actions_panel.btn_teamwork.setText("⏳ Importando...")
        self.actions_panel.btn_teamwork.setEnabled(False)
        self._show_loading_dialog("Importar Proyecto", "Extrayendo y cargando proyecto, por favor espera...")

    def merge_projects(self):
        if not self.working_dir or not self.current_project:
            QMessageBox.warning(self, "Combinar Proyectos", "Primero debes abrir o crear un proyecto base.")
            return
            
        path, _ = QFileDialog.getOpenFileName(self, "Combinar Proyecto (.rqa)", self.working_dir, "RaizQA Project (*.rqa)")
        if not path:
            return
            
        try:
            import zipfile
            import tempfile
            import json
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(path, 'r') as zip_ref:
                    zip_ref.extract("metadata.json", temp_dir)
                with open(os.path.join(temp_dir, "metadata.json"), 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    imported_name = metadata.get("name", "Desconocido")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer el archivo .rqa:\\n{str(e)}")
            return
            
        from gui.dialogs.merge_dialog import MergeDialog
        dialog = MergeDialog(self.current_project.name, imported_name, self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.signal_req_merge_projects.emit(path, settings)
            self.actions_panel.btn_teamwork.setText("⏳ Combinando...")
            self.actions_panel.btn_teamwork.setEnabled(False)
            self._show_loading_dialog("Combinar Proyectos", "Respaldando y combinando proyectos, por favor espera...")

    def handle_project_merged(self):
        self._close_loading_dialog()
        self.actions_panel.btn_teamwork.setText("Colaborar 🫂 ▼")
        self.actions_panel.btn_teamwork.setEnabled(True)
        
        QMessageBox.information(self, "Combinar Proyectos", "Los proyectos se combinaron exitosamente.")
        
        self.signal_req_set_project.emit(self.current_project)
        self.load_project()

    def export_project_rex(self):
        if not self.current_project:
            QMessageBox.warning(self, "Exportar Archivo", "Primero abre o crea un proyecto.")
            return
            
        self._rebuild_doc_groups_from_tree()
        from gui.dialogs.export_exchange_wizard import ExportExchangeWizard
        wizard = ExportExchangeWizard(self.current_project, self.doc_groups, self.code_themes, self)
        if wizard.exec():
            data = wizard.get_export_data()
            if not data["documents"] and not data["codes"]:
                QMessageBox.warning(self, "Exportar Archivo", "No se seleccionó ningún dato para exportar.")
                return
                
            path, _ = QFileDialog.getSaveFileName(self, "Guardar Archivo de Intercambio", self.current_project.name, "RaizQA Exchange (*.rex)")
            if path:
                options = {
                    "include_memos": data["include_memos"],
                    "code_themes": data["code_themes"]
                }
                self.signal_req_export_exchange.emit(data["documents"], data["codes"], options, path)
                self.actions_panel.btn_teamwork.setText("⏳ Exportando...")
                self.actions_panel.btn_teamwork.setEnabled(False)
                self._show_loading_dialog("Exportar Exchange", "Comprimiendo y exportando archivo, por favor espera...")

    def import_project_rex(self):
        if not self.working_dir or not self.current_project:
            QMessageBox.warning(self, "Importar Archivo", "Debes tener un proyecto abierto para importar un archivo de intercambio.")
            return
            
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo de Intercambio", self.working_dir, "RaizQA Exchange (*.rex)")
        if not path:
            return
            
        try:
            from core.import_manager import ImportManager
            exchange_data = ImportManager.inspect_exchange_file(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer el archivo de intercambio:\n{str(e)}")
            return
            
        from gui.dialogs.import_exchange_wizard import ImportExchangeWizard
        wizard = ImportExchangeWizard(self.current_project, exchange_data, self)
        if wizard.exec():
            import_data = wizard.get_import_data()
            self.signal_req_import_exchange.emit(path, import_data)
            self.actions_panel.btn_teamwork.setText("⏳ Importando...")
            self.actions_panel.btn_teamwork.setEnabled(False)
            self._show_loading_dialog("Importar Exchange", "Extrayendo y fusionando archivo de intercambio, por favor espera...")
        
    def handle_project_exported(self, path):
        self._close_loading_dialog()
        self.actions_panel.btn_teamwork.setText("Colaborar 🫂 ▼")
        self.actions_panel.btn_teamwork.setEnabled(True)

    def handle_project_imported(self, project_path):
        self._close_loading_dialog()
        self.actions_panel.btn_teamwork.setText("Colaborar 🫂 ▼")
        self.actions_panel.btn_teamwork.setEnabled(True)
        
        project_name = os.path.basename(project_path)
        self.current_project = Project(project_name, self.working_dir)
        self.memo_manager = self.current_project.memo_manager
        self.lbl_project.setText(f"Proyecto: {self.current_project.name}")
        self.reset_project_state()
        self.signal_req_set_project.emit(self.current_project)
        self.load_project()

    def _show_loading_dialog(self, title, message):
        self.progress_dialog = LoadingDialog(title, message, self)
        self.progress_dialog.show()
        
    def _close_loading_dialog(self):
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

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

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # -------------------- GEOMETRÍA / PANTALLAS --------------------
    DEFAULT_SIZE = (1000, 600)
    MIN_WINDOW_SIZE = (760, 480)

    def _available_area(self):
        """Área utilizable de la pantalla actual (excluye Dock, barra de menús, etc.)."""
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return None
        return screen.availableGeometry()

    def _apply_initial_geometry(self):
        """
        Dimensiona y centra la ventana dentro de la pantalla disponible.

        La ventana es frameless: los botones de cerrar/minimizar y el QSizeGrip viven
        dentro de ella, así que si la geometría se sale de la pantalla
        quedan inalcanzables. Por eso el tamaño nunca supera el
        área disponible.
        """
        area = self._available_area()
        default_w, default_h = self.DEFAULT_SIZE
        min_w, min_h = self.MIN_WINDOW_SIZE

        if area is None:
            self.setGeometry(100, 100, default_w, default_h)
            return
        
        # aqui se elije entre el tamaño x defecto y el tamaño de la pantalla 
        width = max(min(default_w, area.width()), min(min_w, area.width()))
        height = max(min(default_h, area.height()), min(min_h, area.height()))
        x = area.x() + (area.width() - width) // 2
        y = area.y() + (area.height() - height) // 2
        self.setGeometry(x, y, width, height)

    def _ensure_within_screen(self):
        """Reencuadra la ventana si quedo (parcial o totalmente) fuera del área visible."""
        if self.isMaximized() or self.isFullScreen():
            return
        area = self._available_area()
        if area is None:
            return

        geo = self.frameGeometry()
        width = min(geo.width(), area.width())
        height = min(geo.height(), area.height())
        x = min(max(geo.x(), area.x()), area.x() + area.width() - width)
        y = min(max(geo.y(), area.y()), area.y() + area.height() - height)

        if (x, y, width, height) != (geo.x(), geo.y(), geo.width(), geo.height()):
            self.setGeometry(x, y, width, height)

    def _connect_screen_watchers(self):
        """Reencuadra al conectar/desconectar un proyector o al cambiar la resolución."""
        handle = self.windowHandle()
        if handle is not None:
            handle.screenChanged.connect(self._on_screen_changed)
        self._watch_screen(self.screen())

    def _watch_screen(self, screen):
        previous = getattr(self, "_watched_screen", None)
        if previous is screen:
            return
        if previous is not None:
            try:
                previous.availableGeometryChanged.disconnect(self._on_available_geometry_changed)
            except (RuntimeError, TypeError):
                pass
        self._watched_screen = screen
        if screen is not None:
            screen.availableGeometryChanged.connect(self._on_available_geometry_changed)

    def _on_screen_changed(self, screen):
        self._watch_screen(screen)
        self._ensure_within_screen()

    def _on_available_geometry_changed(self, _geometry):
        self._ensure_within_screen()

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_screen_watchers_ready", False):
            self._screen_watchers_ready = True
            self._connect_screen_watchers()
        self._ensure_within_screen()

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

        # Emitimos señal para que el Backend trabaje
        self.signal_req_global_search.emit(term, self.current_project, self.codes_dict, self.memo_manager)

    def handle_search_completed(self, results):
        self._search_matches = results.get("search_matches", [])
        doc_matches = results.get("doc_matches", [])
        code_matches = results.get("code_matches", [])
        memo_matches = results.get("memo_matches", [])

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

        if summary:
            QMessageBox.information(self, "Buscar", "\n".join(summary))
        self._update_search_label()

    def handle_search_failed(self, message):
        QMessageBox.information(self, "Buscar", message)

    def handle_edds_updated(self, codes_dict, themes_dict):
        """El Backend nos avisa que las EDDs cambiaron. Actualizamos cachés y repintamos la UI."""
        print(f"DEBUG: edds_updated received. codes_dict keys: {list(codes_dict.keys())}")
        for k, v in codes_dict.items():
            print(f"DEBUG: code {k} -> {v}")
        self.codes_dict = codes_dict
        self.themes_dict = themes_dict
        # Deferimos la reconstrucción del árbol al siguiente ciclo del event loop
        # para evitar un Segmentation Fault al limpiar la UI desde un handler de señal activo.
        QTimer.singleShot(0, self.populate_code_tree)
        self.save_project() # Guarda todo el estado en un único JSON

    def populate_code_tree(self):
        """Reconstruye el árbol de códigos aplicando temas/categorías jerárquicamente."""
        if not hasattr(self, "code_tree"): return
        
        self._code_tree_updating = True
        self.code_tree.clear()

        added_codes = set()

        def add_subcodes(parent_item, parent_code_name):
            children = self.codes_dict.get(parent_code_name, {}).get("children", [])
            for child_name in children:
                if child_name in self.codes_dict:
                    child_item = self._create_code_node(child_name, self.codes_dict[child_name])
                    parent_item.addChild(child_item)
                    added_codes.add(child_name)
                    add_subcodes(child_item, child_name)

        # 1. Crear los nodos padre (Carpetas de Temas)
        for theme in getattr(self, "code_themes", []):
            theme_name = theme.get("name", "Tema sin nombre")
            theme_codes = theme.get("codes", [])
            
            theme_item = QTreeWidgetItem([theme_name, "", ""])
            theme_item.setData(0, Qt.UserRole, "theme")  # Marcador para diferenciarlo
            theme_item.setIcon(0, self.icon_provider.icon(QFileIconProvider.Folder))
            
            self.code_tree.addTopLevelItem(theme_item)

            # 2. Añadir los códigos raíz como hijos de esta carpeta
            for code_name in theme_codes:
                if code_name in self.codes_dict and self.codes_dict[code_name].get("parent") is None:
                    if code_name not in added_codes:
                        code_item = self._create_code_node(code_name, self.codes_dict[code_name])
                        theme_item.addChild(code_item)
                        added_codes.add(code_name)
                        add_subcodes(code_item, code_name)

        # 3. Añadir los códigos "huérfanos" (raíz sin tema) en la raíz
        for code_name, code_data in self.codes_dict.items():
            if code_name not in added_codes and code_data.get("parent") is None:
                code_item = self._create_code_node(code_name, code_data)
                self.code_tree.addTopLevelItem(code_item)
                added_codes.add(code_name)
                add_subcodes(code_item, code_name)
                
        if getattr(self, "_codes_expanded", False):
            self.code_tree.expandAll()
            
        if hasattr(self, "code_search_field"):
            self.filter_codes(self.code_search_field.text())
            
        self._code_tree_updating = False

    def _create_code_node(self, code_name, code_data):
        """Método auxiliar para instanciar un nodo visual de código."""
        count = sum(len(frags) for frags in code_data.get("fragments", {}).values())
        code_item = QTreeWidgetItem([code_name, str(count), ""])
        code_item.setData(0, Qt.UserRole + 1, code_name)
        code_item.setData(0, Qt.UserRole, "code")
        
        self._configure_code_item(code_item)
        self.apply_code_item_color(code_item, code_data.get("hexcolor", "#fff59d"))
        
        if code_data.get("memo"):
            code_item.setText(2, "📝")
            
        return code_item

    def handle_error(self, message):
        self._close_loading_dialog()
        if hasattr(self, 'actions_panel') and hasattr(self.actions_panel, 'btn_teamwork') and self.actions_panel.btn_teamwork.text().startswith("⏳"):
            self.actions_panel.btn_teamwork.setText("Colaborar 🫂 ▼")
            self.actions_panel.btn_teamwork.setEnabled(True)
        QMessageBox.critical(self, "Error del Backend", message)

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
        from gui import theme
        theme.apply_theme_to_window(self, self.is_dark_mode)

        current_theme_dict = theme.get_theme(self.is_dark_mode)
        
        if hasattr(self, "actions_panel"):
            self.actions_panel.update_theme_icon(self.is_dark_mode)

        if hasattr(self, "local_search_widget"):
            self.local_search_widget.update_theme(current_theme_dict, self.is_dark_mode)

        self.image_viewer.apply_theme(current_theme_dict)
        
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
        delete_code_action = None
        view_memo_action = None
        add_memo_action = None
        delete_memo_action = None

        if item and self.memo_manager:
            menu.addSeparator()
            rename_action = menu.addAction("Renombrar codigo")
            view_fragments_action = menu.addAction("Ver fragmentos")
            delete_code_action = menu.addAction("🗑️ Eliminar código")
            menu.addSeparator()

            view_memo_action = menu.addAction("👁️ Ver memo")
            add_memo_action = menu.addAction("📝 Agregar / editar memo")
            delete_memo_action = menu.addAction("❌ Eliminar memo")

        action = menu.exec(self.code_tree.viewport().mapToGlobal(pos))
        if action == add_code_action:
            self.prompt_add_code(parent_item=item)
        elif action == rename_action:
            self._start_code_rename(item)
        elif action == delete_code_action:
            children = self.codes_dict.get(code_name, {}).get("children", [])
            if children:
                msgBox = QMessageBox(self)
                msgBox.setWindowTitle("Eliminar código padre")
                msgBox.setText(f"El código '{code_name}' tiene {len(children)} subcódigos.")
                msgBox.setInformativeText("¿Qué deseas hacer con los subcódigos?")
                btn_cascade = msgBox.addButton("Borrar todo (Cascada)", QMessageBox.DestructiveRole)
                btn_keep = msgBox.addButton("Mantener subcódigos", QMessageBox.AcceptRole)
                btn_cancel = msgBox.addButton("Cancelar", QMessageBox.RejectRole)
                msgBox.exec()
                
                if msgBox.clickedButton() == btn_cascade:
                    self.signal_req_delete_code.emit(code_name, True)
                elif msgBox.clickedButton() == btn_keep:
                    self.signal_req_delete_code.emit(code_name, False)
            else:
                reply = QMessageBox.question(self, "Eliminar código", f"¿Seguro que deseas eliminar '{code_name}' y todos sus fragmentos?", QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.signal_req_delete_code.emit(code_name, False)
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
            self.save_project()
            QMessageBox.information(self, "Memo guardado", f"Memo actualizado para '{code_name}'.")

    def delete_memo(self, code_name):
        if not self.memo_manager:
            return
        self.memo_manager.delete_memo(code_name)
        self.update_memo_icon(code_name, has_memo=False)
        self.save_project()

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

        self._rebuild_doc_groups_from_tree()
        self.save_project()
        QMessageBox.information(self, "Eliminar documento", f"Documento '{doc_name}' eliminado del proyecto.")

    # -------------------- DIARIO --------------------
    def open_diary(self):
        if not self.current_project:
            QMessageBox.information(self, "Diario", "Abre o crea un proyecto para usar el diario.")
            return

        dialog = DiaryDialog(self.current_project.diary_manager, parent=self)
        dialog.exec()

    # -------------------- FUNCIONES NUEVAS --------------------
    def _invoke_local_search(self):
        """Despliega el buscador si estamos viendo un documento de texto."""
        if self.viewer_stack.currentWidget() == self.text_area and self.current_doc:
            # Sincronizamos el tema antes de mostrarlo
            self.local_search_widget.update_theme(self._current_theme(), self.is_dark_mode)
            self.local_search_widget.show_search()

    def _update_all_extra_selections(self, search_selections=None):
        """
        Unifica los resaltados: Este método evita que el resaltado de la búsqueda 
        borre el resaltado de la selección de columnas y viceversa.
        """
        if search_selections is not None:
            self._ls_extra_selections = search_selections
            
        # Combinamos las selecciones habituales con las selecciones de la búsqueda
        todas_las_selecciones = self._prev_extra_selections + self._column_extra_selections + self._ls_extra_selections
        self.text_area.setExtraSelections(todas_las_selecciones)

    def show_code_fragments(self, item, column):
        code_name = self._code_item_name(item)
        code = self.get_code_data(code_name)
        if code and "fragments" in code:
            flat_frags = []
            for doc, frags in code["fragments"].items():
                # Leer el documento 
                doc_text = self.current_project.get_document_text(doc) if self.current_project else ""
                
                for f in frags:
                    f_copy = dict(f)
                    f_copy["document"] = doc
                    f_copy["type"] = f.get("type", "text")
                    
                    # INYECTAR EL TEXTO AQUÍ
                    if "text" not in f_copy:
                        start, end = f_copy.get("start", 0), f_copy.get("end", 0)
                        f_copy["text"] = doc_text[start:end]
                        
                    flat_frags.append(f_copy)
                    
            dialog = CodeFragmentsDialog(code_name, flat_frags)
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
            QMessageBox.warning(self, "Renombrar código", "El nombre del código no puede quedar vacío.")
            return

        if new_name in self.codes_dict:
            self._restore_code_item_label(item)
            QMessageBox.warning(self, "Renombrar código", "Ya existe un código con ese nombre.")
            return

        # 1. Recuperar los datos existentes ANTES de emitir la señal para no perderlos
        code_data = self.get_code_data(old_name)
        color_hex = code_data.get("hexcolor", "#fff59d") if code_data else "#fff59d"
        memo_text = code_data.get("memo", "") if code_data else ""
        
        # 2. Sincronizar con el gestor independiente de Memos (si el proyecto lo está usando)
        if self.memo_manager:
            old_memo = self.memo_manager.get_memo(old_name)
            if old_memo:
                memo_text = old_memo
                self.memo_manager.add_or_update_memo(new_name, old_memo)
                self.memo_manager.delete_memo(old_name)

        self._restore_code_item_label(item)
        
        # 3. Emitir la señal con todos los datos intactos (evitando usar None)
        self.signal_req_update_code.emit(old_name, new_name, color_hex, memo_text)

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
            self.signal_req_set_project.emit(self.current_project)
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
            self.signal_req_set_project.emit(self.current_project)
            self.load_project()
            QMessageBox.information(self, "Proyecto abierto", f"Proyecto '{self.current_project.name}' abierto.")

    def reset_project_state(self):
        """Reinicia colecciones y widgets al cambiar de proyecto."""
        self.has_unsaved_changes = False
        if self.current_project:
            self.setWindowTitle(f"RaizQA 🌱 - {self.current_project.name}")
        else:
            self.setWindowTitle("RaizQA 🌱")
        self.codes_dict = {}
        self.themes_dict = {}
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
        documents = self._all_documents()
        state_data = {
            "documents": documents,
            "highlights": self.highlights,
            "doc_groups": self.doc_groups,
            "themes": getattr(self, "code_themes", []),
            "case_studies": getattr(self, "case_studies", [])
        }
        self.signal_req_save_all.emit(state_data)
        self.has_unsaved_changes = False
        if self.current_project:
            self.setWindowTitle(f"RaizQA 🌱 - {self.current_project.name}")

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
        try:
            entries = self.current_project.diary_manager.get_entries()
        except Exception as exc:
            QMessageBox.critical(self, "Exportar diario", f"No se pudo leer el diario:\n{exc}")
            return

        default_dir = self.working_dir or os.getcwd()
        default_path = os.path.join(default_dir, f"{self.current_project.name}_diario.docx")
        
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar diario a Word",
            default_path,
            "Word (*.docx)",
        )
        if not path:
            return

        # Emitimos la señal pasando la lista de 'entries'
        self.signal_req_export_diary.emit(entries, self.current_project.name, path)

    def handle_export_success(self, export_type, path):
        QMessageBox.information(self, f"Exportar {export_type}", f"{export_type} exportado exitosamente en:\n{path}")

    def handle_export_error(self, export_type, error_msg):
        self._close_loading_dialog()
        if export_type == "Proyecto .rqa":
            self.actions_panel.btn_teamwork.setText("Teamwork 🫂 ▼")
            self.actions_panel.btn_teamwork.setEnabled(True)
        QMessageBox.critical(self, f"Exportar {export_type}", f"No se pudo exportar {export_type}:\n{error_msg}")


    def auto_save(self):
        self.save_project()

    def load_project(self):
        if not self.current_project:
            return

        data = self.current_project.load_project_data()

        self.code_themes = data.get("themes", [])
        self.case_studies = data.get("case_studies", [])
        self.highlights = data.get("highlights", {})

        # Los diccionarios ya se cargaron en el proyecto, solo sincronizamos
        self.codes_dict = self.current_project.codes_dict
        self.themes_dict = self.current_project.themes_dict

        # Ahora que los diccionarios tienen datos, limpiamos los árboles
        self.code_tree.clear()
        self.doc_tree.clear()
        
        self.doc_groups = data.get("doc_groups")
        if not self.doc_groups:
            documents = data.get("documents") or self.current_project.list_documents()
            self.doc_groups = {"__root__": documents}
            
        # Al ejecutar esto, display_document() se llamará para el primer archivo
        # y ya podrá leer correctamente los fragmentos desde self.codes_dict
        self._populate_doc_tree()

        # Poblar el árbol de códigos visualmente
        self.populate_code_tree()

        if self.memo_manager:
            for code_name, memo_text in self.memo_manager.memos.items():
                if memo_text.strip():
                    self.update_memo_icon(code_name, True)

        self._color_index = max(self._color_index, len(self.codes_dict))
        if hasattr(self, "code_search_field"):
            self.filter_codes(self.code_search_field.text())


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
        pass

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

    def _restore_code_item_label(self, item):
        if not item:
            return
        code_name = self._code_item_name(item)
        code_data = self.get_code_data(code_name)
        self._code_tree_updating = True
        if code_data:
            self.apply_code_item_color(item, code_data.get("hexcolor", "#fff59d"))
        else:
            item.setText(0, code_name)
        self._code_tree_updating = False

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
                # Evita dejar la barra de título (y sus botones) fuera de la pantalla
                self._ensure_within_screen()
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
        self._update_all_extra_selections()

    def _clear_column_selection(self):
        if self._column_selecting:
            self._column_selecting = False
        if self._prev_extra_selections:
            self._update_all_extra_selections()
        else:
            self._update_all_extra_selections()
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
                # Desactivar editor si es imagen
                self.doc_editor_controller.load_document(None, "") 
                self._show_image_document(doc_path)
            else:
                self._show_text_viewer()
                text = self.current_project.read_document(self.current_doc)
                self.text_area.setPlainText(text)
                
                self.doc_editor_controller.load_document(self.current_doc, text)
        else:
            self.text_area.clear()
            self.image_viewer.clear_image()
            self.doc_editor_controller.load_document(None, "")

        #  3. Restaurar los subrayados del documento nuevo DIRECTAMENTE desde codes_dict
        self.highlighted = []
        for code_name, data in self.codes_dict.items():
            for frag in data.get("fragments", {}).get(self.current_doc, []):
                f_copy = dict(frag)
                f_copy["color"] = data.get("hexcolor", "#fff59d")
                f_copy["document"] = self.current_doc
                f_copy["type"] = frag.get("type", "text")
                self.highlighted.append(f_copy)

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

            if self.codes_dict:
                add_to_existing = menu.addMenu("📎 Agregar a código existente")
                for code_name in self.codes_dict:
                    act = add_to_existing.addAction(code_name)
                    act.triggered.connect(
                        lambda checked=False, name=code_name, text=selected_text,
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
        if self.codes_dict:
            add_to_existing = menu.addMenu("Agregar a codigo existente")
            for code_name in self.codes_dict:
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
            item = iterator.value()
            name = self._code_item_name(item)
            if name and self.codes_dict.get(name, {}).get("parent") is None:
                code_names.append(name)
            iterator += 1
        if not code_names:
            QMessageBox.warning(self, "Subcódigo", "Primero crea un código principal (no se permiten subcódigos de subcódigos).")
            return

        parent_name, ok = QInputDialog.getItem(self, "Subcódigo", "Selecciona código padre:", code_names, 0, False)
        if not ok or not parent_name:
            return

        selection = image_selection or self._image_selection_payload()
        has_selection = bool(selection and selection.get("rect"))
        note = self._prompt_image_note(
            "Nuevo fragmento (imagen)",
            "Descripción del fragmento (opcional):",
            default_text="Zona de imagen" if has_selection else "Imagen completa",
        )
        if note is None:
            return

        parent_item = self.find_tree_item(parent_name)
        if parent_item:
            self.create_new_code("", None, None, parent_item, is_image=True, note=note, image_selection=selection)

    def add_code_from_toolbar(self):
        self.prompt_add_code()

    def prompt_add_code(self, parent_item=None):
        if not self.current_project:
            QMessageBox.warning(self, "Agregar código", "Primero abre o crea un proyecto.")
            return

        # Calcular el color sugerido
        default_color = self.COLOR_PALETTE[self._color_index % len(self.COLOR_PALETTE)][1]
        
        # Abrir ventana unificada
        dialog = NewCodeDialog(self.COLOR_PALETTE, default_color=default_color, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return

        code_label, color_hex, memo = dialog.get_data()

        if not code_label:
            QMessageBox.warning(self, "Agregar código", "El nombre del código no puede quedar vacío.")
            return

        if code_label in self.codes_dict:
            QMessageBox.warning(self, "Agregar código", "Ya existe un código con ese nombre.")
            return

        self._color_index += 1
        
        parent_name = ""
        if parent_item and parent_item.data(0, Qt.UserRole) == "code":
            parent_name = parent_item.data(0, Qt.UserRole + 1)
            # Solo permitir un nivel de anidamiento
            if self.codes_dict.get(parent_name, {}).get("parent") is not None:
                parent_name = self.codes_dict[parent_name]["parent"]
        
        # Emitir señal al backend con el memo incluido
        self.signal_req_add_code.emit(code_label, color_hex, memo, parent_name)


    def create_new_code(self, selected_text, start, end, parent_item=None, code_label=None, is_image=False, note=None, image_selection=None):
        if not self.current_doc:
            QMessageBox.warning(self, "Nuevo código", "Selecciona un documento antes de codificar.")
            return

        if not is_image and (start is None or end is None or start == end):
            return

        # Calcular el color sugerido
        default_color = self.COLOR_PALETTE[self._color_index % len(self.COLOR_PALETTE)][1]
        
        # Abrir ventana unificada (si es "in vivo", code_label ya trae un texto sugerido)
        dialog = NewCodeDialog(self.COLOR_PALETTE, default_name=code_label or "", default_color=default_color, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return

        code_label, color_hex, memo = dialog.get_data()

        if not code_label:
            QMessageBox.warning(self, "Nuevo código", "El nombre del código no puede quedar vacío.")
            return
            
        if code_label in self.codes_dict:
            QMessageBox.warning(self, "Nuevo código", "Ya existe un código con ese nombre. Usa 'Agregar a código existente'.")
            return

        self._color_index += 1

        # 1. Crear el código en el backend
        parent_name = ""
        if parent_item and parent_item.data(0, Qt.UserRole) == "code":
            parent_name = parent_item.data(0, Qt.UserRole + 1)
            # Solo permitir un nivel de anidamiento
            if self.codes_dict.get(parent_name, {}).get("parent") is not None:
                parent_name = self.codes_dict[parent_name]["parent"]
        self.signal_req_add_code.emit(code_label, color_hex, memo, parent_name)
        
        # 2. Construir el paquete de datos del fragmento
        if is_image and image_selection:
            fragment_data = {
                "type": "image",
                "rect": image_selection["rect"],
                "image_size": image_selection["image_size"],
                "note": note
            }
        else:
            fragment_data = {
                "type": "text",
                "start": start,
                "end": end
            }

        # 3. Emitir el fragmento al backend
        self.signal_req_add_fragment.emit(code_label, self.current_doc, fragment_data)

        # 4. Dibujar localmente de inmediato
        fragment_visual = fragment_data.copy()
        fragment_visual["color"] = color_hex
        fragment_visual["document"] = self.current_doc
        self.highlight_fragment(fragment_visual, QColor(color_hex))


    def add_to_existing_code(self, code_name, selected_text, start, end, is_image=False, note=None, image_selection=None):
        if not self.current_doc or code_name not in self.codes_dict:
            return

        # Construir el paquete de datos del fragmento
        if is_image and image_selection:
            fragment_data = {
                "type": "image",
                "rect": image_selection["rect"],
                "image_size": image_selection["image_size"],
                "note": note
            }
        else:
            fragment_data = {
                "type": "text",
                "start": start,
                "end": end
            }

        # 1. Petición MVC: Agregar fragmento
        self.signal_req_add_fragment.emit(code_name, self.current_doc, fragment_data)

        # 2. Dibujarlo localmente
        color_hex = self.codes_dict[code_name].get("hexcolor", "#fff59d")
        fragment_visual = fragment_data.copy()
        fragment_visual["color"] = color_hex
        fragment_visual["document"] = self.current_doc
        self.highlight_fragment(fragment_visual, QColor(color_hex))

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
        for code_name, data in self.codes_dict.items():
            for doc, frags in data.get("fragments", {}).items():
                if fragment in frags:
                    return data.get("hexcolor", "#fff59d")
        return fragment.get("color", "#fff59d")

    def create_subcode(self, selected_text, start, end):
        iterator = QTreeWidgetItemIterator(self.code_tree)
        code_names = []
        while iterator.value():
            item = iterator.value()
            name = self._code_item_name(item)
            if name and self.codes_dict.get(name, {}).get("parent") is None:
                code_names.append(name)
            iterator += 1
        if not code_names:
            QMessageBox.warning(self, "Subcódigo", "Primero crea un código principal (no se permiten subcódigos de subcódigos).")
            return

        parent_name, ok = QInputDialog.getItem(self, "Subcódigo", "Selecciona código padre:", code_names, 0, False)
        if not ok or not parent_name:
            return

        parent_item = self.find_tree_item(parent_name)
        if parent_item:
            self.create_new_code(selected_text, start, end, parent_item=parent_item)

    def find_tree_item(self, code_name):
        iterator = QTreeWidgetItemIterator(self.code_tree)
        while iterator.value():
            item = iterator.value()
            if self._code_item_name(item) == code_name:
                return item
            iterator += 1
        return None

    def get_hydrated_codes_dict(self):
            """Genera una copia de codes_dict inyectando el texto real de los fragmentos, 
            para que los módulos externos puedan mostrar el texto sin fallar."""
            import copy
            hydrated = copy.deepcopy(self.codes_dict)
            
            if not self.current_project:
                return hydrated
                
            for code_name, data in hydrated.items():
                for doc_name, frags in data.get("fragments", {}).items():
                    # Cargamos el texto completo del documento (con caché en memoria gracias a project.py)
                    doc_text = self.current_project.get_document_text(doc_name)
                    
                    for frag in frags:
                        if "text" not in frag:
                            start = frag.get("start", 0)
                            end = frag.get("end", 0)
                            # Cortamos el string y creamos la llave "text" que espera la UI
                            frag["text"] = doc_text[start:end]
                            
            return hydrated


    # -------------------- VER CÓDIGOS --------------------
    def open_code_viewer(self):
        if not self.codes_dict:
            QMessageBox.information(self, "Códigos", "No hay códigos creados aún.")
            return
        if not self.current_doc:
            QMessageBox.information(self, "Códigos", "Primero selecciona un documento.")
            return
            
        doc_path = self.current_project.get_document_path(self.current_doc)
        
        # 1. Obtenemos el diccionario con los textos ya inyectados
        hydrated_codes = self.get_hydrated_codes_dict()
        
        # 2. Se lo pasamos al módulo externo en lugar de self.codes_dict
        viewer = CodeViewerWindow(
            doc_path,
            hydrated_codes,  # <--- Cambio clave aquí
            theme=self._current_theme(),
            dark_mode=self.is_dark_mode,
        )
        viewer.exec()

    def open_themes_categories(self):
        if not self.current_project:
            QMessageBox.information(self, "Temas y categorÃ­as", "Primero abre o crea un proyecto.")
            return
        
        # Solo enviar códigos principales a la ventana de temas, 
        # ya que los subcódigos heredan el tema de su padre implícitamente
        codes = [name for name, data in self.codes_dict.items() if data.get("parent") is None]
        
        dialog = ThemesCategoriesDialog(codes, self.code_themes, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.code_themes = dialog.get_themes_data()
            self.save_project()

            self.populate_code_tree()

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
        dialog = CompareDialog(self.current_project, self.codes_dict, left_doc=left, right_doc=right, parent=self)
        dialog.exec()

    def open_code_matrix(self):
        if not self.current_project:
            QMessageBox.information(self, "Code Matrix", "Primero abre o crea un proyecto.")
            return
        docs = self._all_documents()
        if not docs:
            QMessageBox.information(self, "Code Matrix", "No hay documentos para mostrar.")
            return
        if not self.codes_dict:
            QMessageBox.information(self, "Code Matrix", "No hay códigos creados aún.")
            return
        dialog = CodeMatrixDialog(docs, self.codes_dict, current_doc=self.current_doc, parent=self)
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
        dialog = ThemesAnalysisDialog(self.codes_dict, self.code_themes, self.current_project, parent=self)
        dialog.exec()

    def open_case_study(self):
        if not self.current_project:
            QMessageBox.information(self, "Estudio de casos", "Primero abre o crea un proyecto.")
            return
        docs = self._all_documents()
        if not docs:
            QMessageBox.information(self, "Estudio de casos", "No hay documentos para analizar.")
            return
        if not self.codes_dict:
            QMessageBox.information(self, "Estudio de casos", "No hay cÃ³digos creados aÃºn.")
            return
        dialog = CaseStudyDialog(
            self.current_project,
            self.codes_dict,
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
        if not self.codes_dict:
            QMessageBox.information(self, "Exportar libro de códigos", "No hay códigos para exportar.")
            return

        path = self._ask_excel_export_path("Guardar libro de códigos", "libro_de_codigos.xlsx")
        if not path:
            return

        rows = self._collect_code_rows_for_export()
        if not rows:
            QMessageBox.information(self, "Exportar libro de códigos", "No se encontraron códigos en el árbol.")
            return

        # Emitimos señal al backend
        self.signal_req_export_code_tree.emit(rows, path)

    def export_code_fragments(self):
        if not self.codes_dict:
            QMessageBox.information(self, "Exportar fragmentos", "No hay códigos para exportar.")
            return

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
        # Emitimos señal al backend
        self.signal_req_export_code_fragments.emit(selected_rows, fragment_rows, path)

    # (Dependencies load removed)

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

    # (Export writing helpers moved to core.export_manager)

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
            fragments = []
            for doc, frags in (code_data or {}).get("fragments", {}).items():
                for f in frags:
                    f_copy = dict(f)
                    f_copy["document"] = doc
                    f_copy["type"] = f.get("type", "text")
                    fragments.append(f_copy)
            if text_only:
                fragments = [frag for frag in fragments if frag.get("type") != "image"]
            return fragments

        def freq_for(code_data):
            if not code_data:
                return 0
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
            for doc, frags in code_data.get("fragments", {}).items():
                for fragment in frags:
                    if fragment.get("type", "text") == "image":
                        continue
                    f_copy = dict(fragment)
                    f_copy["document"] = doc
                    fragments.append({
                        "code_name": code_name,
                        "document": doc,
                        "text": self._resolve_fragment_export_text(f_copy),
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
        """Metodo obsoleto. Las EDDs se encargan de persistir los fragmentos nativamente."""
        pass


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
                self.apply_code_item_color(item, code.get("hexcolor", "#fff59d"))
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
        return self.codes_dict.get(code_name)

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

    def mark_as_dirty(self, *args, **kwargs):
        """Marca el proyecto como modificado (con cambios sin guardar)."""
        self.has_unsaved_changes = True
        if self.current_project and not self.windowTitle().endswith("*"):
            self.setWindowTitle(f"RaizQA 🌱 - {self.current_project.name} *")

    def closeEvent(self, event):
        """Intercepta el evento de cierre si hay cambios sin guardar."""
        if self.has_unsaved_changes:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Cambios sin guardar")
            msg_box.setText("Hay cambios sin guardar en el proyecto actual.")
            msg_box.setInformativeText("¿Deseas guardar los cambios antes de salir?")
            
            btn_save = msg_box.addButton("Guardar y salir", QMessageBox.AcceptRole)
            btn_discard = msg_box.addButton("Salir sin guardar", QMessageBox.DestructiveRole)
            btn_cancel = msg_box.addButton("Cancelar", QMessageBox.RejectRole)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == btn_save:
                self.save_project()
                event.accept()
            elif msg_box.clickedButton() == btn_discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

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
