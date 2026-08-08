import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from gui.main_window import RaizQAGUI
from core.logica import ControladorLogico
from gui.dialogs.readme_dialog import ReadmeDialog


class RaizQA:
    def __init__(self):
        self.logica = ControladorLogico()
        self.ventana = RaizQAGUI()
        self.conectar()
    
    def conectar(self):
        # 1. UI -> Backend (La ventana emite peticiones, la lógica las atrapa)
        self.ventana.signal_req_global_search.connect(self.logica.req_global_search)
        self.ventana.signal_req_export_diary.connect(self.logica.req_export_diary)
        self.ventana.signal_req_export_code_tree.connect(self.logica.req_export_code_tree)
        self.ventana.signal_req_export_code_fragments.connect(self.logica.req_export_code_fragments)
        self.ventana.signal_req_export_project.connect(self.logica.req_export_project)
        self.ventana.signal_req_import_project.connect(self.logica.req_import_project)
        self.ventana.signal_req_export_exchange.connect(self.logica.req_export_exchange)
        self.ventana.signal_req_import_exchange.connect(self.logica.req_import_exchange)
        self.ventana.signal_req_merge_projects.connect(self.logica.req_merge_projects)

        # UI -> Backend (Gestión de Proyecto / Documentos / Grupos / Temas / Memos)
        self.ventana.signal_req_create_project.connect(self.logica.req_create_project)
        self.ventana.signal_req_open_project.connect(self.logica.req_open_project)
        self.ventana.signal_req_import_document.connect(self.logica.req_import_document)
        self.ventana.signal_req_add_group.connect(self.logica.req_add_group)
        self.ventana.signal_req_move_document.connect(self.logica.req_move_document)
        self.ventana.signal_req_sync_doc_groups.connect(self.logica.req_sync_doc_groups)
        self.ventana.signal_req_sync_code_hierarchy.connect(self.logica.req_sync_code_hierarchy)
        self.ventana.signal_req_sync_themes.connect(self.logica.req_sync_themes)
        self.ventana.signal_req_save_case_studies.connect(self.logica.req_save_case_studies)
        self.ventana.signal_req_set_memo.connect(self.logica.req_set_memo)
        self.ventana.signal_req_delete_memo.connect(self.logica.req_delete_memo)

        # UI -> Backend (Gestión de Códigos y EDDs)
        self.ventana.signal_req_add_code.connect(self.logica.req_add_code)
        self.ventana.signal_req_delete_code.connect(self.logica.req_delete_code)
        self.ventana.signal_req_update_code.connect(self.logica.req_update_code)
        self.ventana.signal_req_add_fragment.connect(self.logica.req_add_fragment)
        self.ventana.signal_req_update_document.connect(self.logica.req_update_document)

        # 2. Backend -> UI (La lógica emite resultados, la ventana los muestra)
        self.logica.edds_updated.connect(self.ventana.handle_edds_updated)
        self.logica.error_occurred.connect(self.ventana.handle_error)

        self.logica.search_completed.connect(self.ventana.handle_search_completed)
        self.logica.search_failed.connect(self.ventana.handle_search_failed)

        self.logica.export_success.connect(self.ventana.handle_export_success)
        self.logica.export_error.connect(self.ventana.handle_export_error)

        self.logica.project_saved.connect(self.ventana.handle_project_saved)
        self.logica.project_loaded.connect(self.ventana.handle_project_loaded)
        self.logica.project_exported.connect(self.ventana.handle_project_exported)
        self.logica.project_imported.connect(self.ventana.handle_project_imported)
        self.logica.project_merged.connect(self.ventana.handle_project_merged)

        self.logica.document_imported.connect(self.ventana.handle_document_imported)
        self.logica.group_added.connect(self.ventana.handle_group_added)
        self.logica.document_moved.connect(self.ventana.handle_document_moved)
        self.logica.memo_updated.connect(self.ventana.handle_memo_updated)

# Asegura que el directorio raíz esté en sys.path (por si se ejecuta desde fuera)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # App/window icon (works in dev and PyInstaller)
    base_path = getattr(sys, "_MEIPASS", BASE_DIR)
    icon_path = os.path.join(base_path, "logo1.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Pantalla de bienvenida
    readme = ReadmeDialog()
    readme.exec()

    # Inicializar arquitectura MVC
    app_controller = RaizQA()
    if os.path.exists(icon_path):
        app_controller.ventana.setWindowIcon(QIcon(icon_path))
    
    app_controller.ventana.show()

    sys.exit(app.exec())