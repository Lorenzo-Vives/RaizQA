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
        
        # UI -> Backend (Gestión de Códigos y EDDs)
        self.ventana.signal_req_add_code.connect(self.logica.req_add_code)
        self.ventana.signal_req_delete_code.connect(self.logica.req_delete_code)
        self.ventana.signal_req_update_code.connect(self.logica.req_update_code)
        self.ventana.signal_req_add_fragment.connect(self.logica.req_add_fragment)
        self.ventana.signal_req_set_project.connect(self.logica.req_set_project)
        self.ventana.signal_req_update_document.connect(self.logica.req_update_document)

        # 2. Backend -> UI (La lógica emite resultados, la ventana los muestra)
        self.logica.edds_updated.connect(self.ventana.handle_edds_updated)
        self.logica.error_occurred.connect(self.ventana.handle_error)
        
        self.logica.search_completed.connect(self.ventana.handle_search_completed)
        self.logica.search_failed.connect(self.ventana.handle_search_failed)
        
        self.logica.export_success.connect(self.ventana.handle_export_success)
        self.logica.export_error.connect(self.ventana.handle_export_error)

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
