"""
Módulo del panel de acciones principal.
Contiene el widget ActionsPanelWidget que agrupa todas las opciones
de navegación y exportación de RaizQA.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ActionsPanelWidget(QFrame):
    """
    Panel modular que contiene todas las acciones principales de la app.
    Agrupa funcionalidades y emite señales para que main_window.py
    las intercepte y ejecute.
    """

    # Señales: Comunicación hacia el controlador principal
    sig_working_dir = Signal()
    sig_create_project = Signal()
    sig_open_project = Signal()
    sig_merge_projects = Signal()
    sig_import_doc = Signal()
    sig_export_rqa = Signal()
    sig_import_rqa = Signal()
    sig_export_rex = Signal()
    sig_import_rex = Signal()

    sig_add_code = Signal()
    sig_view_codes = Signal()
    sig_themes_categories = Signal()
    sig_diary = Signal()

    # Señales de exportación
    sig_export_code_tree = Signal()
    sig_export_fragments = Signal()
    sig_export_diary = Signal()

    # Señales de análisis
    sig_compare = Signal()
    sig_code_matrix = Signal()
    sig_wordcloud = Signal()
    sig_themes_analysis = Signal()
    sig_case_study = Signal()

    sig_toggle_theme = Signal()

    def __init__(self, parent=None):
        """Inicializa el panel de acciones."""
        super().__init__(parent)
        self.setObjectName("ActionsFrame")
        self._setup_ui()

    def _setup_ui(self):
        """Configura el layout y los componentes principales."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # --- BARRA DE NAVEGACIÓN ---
        nav_row = QHBoxLayout()
        nav_row.setSpacing(8)

        self.btn_nav_home = QPushButton("Inicio")
        self.btn_nav_codes = QPushButton("Códigos")
        self.btn_nav_analysis = QPushButton("Análisis")
        self.btn_toggle_theme = QPushButton("☀️")

        nav_buttons = (
            self.btn_nav_home,
            self.btn_nav_codes,
            self.btn_nav_analysis,
            self.btn_toggle_theme,
        )

        for btn in nav_buttons:
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(30)
            btn.setProperty("navButton", True)
            if btn is not self.btn_toggle_theme:
                btn.setCheckable(True)
            nav_row.addWidget(btn)

        nav_row.addStretch()
        layout.addLayout(nav_row)

        # --- CONTENEDORES DE VISTAS ---
        self.actions_home = QWidget()
        self._setup_home_view()

        self.actions_codes = QWidget()
        self._setup_codes_view()

        self.actions_analysis = QWidget()
        self._setup_analysis_view()

        layout.addWidget(self.actions_home)
        layout.addWidget(self.actions_codes)
        layout.addWidget(self.actions_analysis)

        # --- CONEXIONES INTERNAS ---
        self.btn_nav_home.clicked.connect(lambda: self._set_view("home"))
        self.btn_nav_codes.clicked.connect(lambda: self._set_view("codes"))
        self.btn_nav_analysis.clicked.connect(
            lambda: self._set_view("analysis")
        )
        self.btn_toggle_theme.clicked.connect(self.sig_toggle_theme.emit)

        self._set_view("home")

    def _add_action_row(self, target_layout, buttons):
        """Agrega una fila horizontal de botones a un layout."""
        row = QHBoxLayout()
        row.setSpacing(8)
        for btn in buttons:
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(32)
            btn.setProperty("actionButton", True)
            row.addWidget(btn)
        row.addStretch()
        target_layout.addLayout(row)

    def _setup_home_view(self):
        """Configura los botones de la vista Inicio."""
        layout = QVBoxLayout(self.actions_home)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        btn_working_dir = QPushButton("Seleccionar Working Directory")
        
        # --- BOTÓN DESPLEGABLE DE PROYECTO ---
        self.btn_project = QPushButton("📁 Proyecto ▼")
        project_menu = QMenu(self.btn_project)
        
        action_create = QAction("Nuevo proyecto...", self)
        action_open = QAction("Abrir proyecto...", self)
        
        action_create.triggered.connect(self.sig_create_project.emit)
        action_open.triggered.connect(self.sig_open_project.emit)
        
        project_menu.addAction(action_create)
        project_menu.addAction(action_open)
        
        self.btn_project.setMenu(project_menu)
        
        btn_import_doc = QPushButton("Importar Archivo")
        
        self.btn_teamwork = QPushButton("Colaborar 🫂 ▼")
        teamwork_menu = QMenu(self.btn_teamwork)
        
        action_merge = QAction("Combinar proyectos...", self)
        action_import_rqa = QAction("Importar proyecto (.rqa)...", self)
        action_export_rqa = QAction("Exportar proyecto (.rqa)...", self)
        
        action_merge.triggered.connect(self.sig_merge_projects.emit)
        action_import_rqa.triggered.connect(self.sig_import_rqa.emit)
        action_export_rqa.triggered.connect(self.sig_export_rqa.emit)
        
        teamwork_menu.addAction(action_merge)
        teamwork_menu.addAction(action_import_rqa)
        teamwork_menu.addAction(action_export_rqa)
        self.btn_teamwork.setMenu(teamwork_menu)

        btn_working_dir.clicked.connect(self.sig_working_dir.emit)
        btn_import_doc.clicked.connect(self.sig_import_doc.emit)

        self._add_action_row(
            layout,
            [btn_working_dir, self.btn_project, btn_import_doc, self.btn_teamwork]
        )

    def _setup_codes_view(self):
        """Configura los botones de la vista Códigos."""
        layout = QVBoxLayout(self.actions_codes)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        btn_add_code = QPushButton("Agregar código")
        btn_view_codes = QPushButton("📚 Ver Códigos")
        btn_themes = QPushButton("Temas y categorías")
        btn_diary = QPushButton("📓 Diario de codificación")

        # --- BOTÓN DESPLEGABLE DE EXPORTACIÓN ---
        btn_export = QPushButton("📤 Exportar ▼")
        export_menu = QMenu(btn_export)

        action_export_codes = QAction("Libro de códigos", self)
        action_export_frags = QAction("Fragmentos codificados", self)
        action_export_diary = QAction("Diario de codificación (Word)", self)

        action_export_codes.triggered.connect(self.sig_export_code_tree.emit)
        action_export_frags.triggered.connect(self.sig_export_fragments.emit)
        action_export_diary.triggered.connect(self.sig_export_diary.emit)

        export_menu.addAction(action_export_codes)
        export_menu.addAction(action_export_frags)
        export_menu.addAction(action_export_diary)

        btn_export.setMenu(export_menu)

        btn_add_code.clicked.connect(self.sig_add_code.emit)
        btn_view_codes.clicked.connect(self.sig_view_codes.emit)
        btn_themes.clicked.connect(self.sig_themes_categories.emit)
        btn_diary.clicked.connect(self.sig_diary.emit)

        self._add_action_row(
            layout,
            [btn_add_code, btn_view_codes, btn_themes, btn_diary, btn_export]
        )

    def _setup_analysis_view(self):
        """Configura los botones de la vista Análisis."""
        layout = QVBoxLayout(self.actions_analysis)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        btn_compare = QPushButton("Comparar documentos")
        btn_code_matrix = QPushButton("Code Matrix Browser")
        btn_wordcloud = QPushButton("Nube de palabras")
        btn_themes_analysis = QPushButton("Análisis de temas")
        btn_case_study = QPushButton("Estudio de casos")

        btn_compare.clicked.connect(self.sig_compare.emit)
        btn_code_matrix.clicked.connect(self.sig_code_matrix.emit)
        btn_wordcloud.clicked.connect(self.sig_wordcloud.emit)
        btn_themes_analysis.clicked.connect(self.sig_themes_analysis.emit)
        btn_case_study.clicked.connect(self.sig_case_study.emit)

        self._add_action_row(
            layout,
            [
                btn_compare,
                btn_code_matrix,
                btn_wordcloud,
                btn_themes_analysis,
                btn_case_study,
            ]
        )

    def _set_view(self, view_name):
        """Alterna la visibilidad de las barras de herramientas."""
        self.actions_home.setVisible(view_name == "home")
        self.actions_codes.setVisible(view_name == "codes")
        self.actions_analysis.setVisible(view_name == "analysis")

        self.btn_nav_home.setChecked(view_name == "home")
        self.btn_nav_codes.setChecked(view_name == "codes")
        self.btn_nav_analysis.setChecked(view_name == "analysis")

    def update_theme_icon(self, is_dark_mode):
        """Actualiza el ícono del botón de tema dependiendo del estado."""
        self.btn_toggle_theme.setText("🌙" if is_dark_mode else "☀️")