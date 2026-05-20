from PySide6.QtCore import QObject, Signal

from core.search_manager import SearchManager
from core.export_manager import ExportManager
from core.worker_objects import BuscadorWorker  

class ControladorLogico(QObject):
    """
    Cerebro del backend. Mantiene el estado del programa y realiza la lógica pesada.
    No conoce nada de QWidgets, solo emite señales con datos.
    """
    # ==========================================
    # SEÑALES (Backend -> Interfaz Gráfica)
    # ==========================================
    project_loaded = Signal(object)      # Emite el objeto Project cuando carga
    
    search_completed = Signal(dict)      # Emite resultados de la búsqueda
    search_failed = Signal(str)          # Emite un mensaje si no hay resultados o error

    export_success = Signal(str, str)    # Emite (Tipo de exportación, Ruta del archivo)
    export_error = Signal(str, str)      # Emite (Tipo de exportación, Error)

    edds_updated = Signal(dict, dict)    # Emite (codes_dict, themes_dict) cada vez que cambian
    error_occurred = Signal(str)         # Emite mensajes de error generales

    def __init__(self):
        super().__init__()
        # Aquí vivirá el estado global (La instancia del proyecto activo)
        self.current_project = None

    # ==========================================
    # SLOTS/MÉTODOS (Interfaz Gráfica -> Backend)
    # ==========================================
    def req_global_search(self, term, project, codes, memo_manager):
        """Petición asíncrona de la interfaz para iniciar la búsqueda."""
        if not term:
            self.search_failed.emit("El término de búsqueda está vacío.")
            return
             
        # 1. Instanciar el worker externo
        worker = BuscadorWorker(term, project, codes, memo_manager)
        
        # 2. Conectar sus señales a los métodos internos de redirección
        worker.signals.finished.connect(self._on_search_finished)
        worker.signals.error.connect(self._on_search_error)
        
        # 3. Ordenar al ThreadPool que lo ejecute en segundo plano
        self.threadpool.start(worker)

    def req_export_diary(self, diary_text, project_name, export_path):
        """Petición de la UI para exportar el diario."""
        try:
            ExportManager.export_diary(diary_text, project_name, export_path)
            self.export_success.emit("Diario", export_path)
        except Exception as e:
            self.export_error.emit("Diario", str(e))

    def req_export_code_tree(self, rows, export_path):
        """Petición de la UI para exportar el libro de códigos."""
        try:
            ExportManager.export_code_tree(rows, export_path)
            self.export_success.emit("Libro de códigos", export_path)
        except Exception as e:
            self.export_error.emit("Libro de códigos", str(e))

    def req_export_code_fragments(self, selected_rows, fragment_rows, export_path):
        """Petición de la UI para exportar fragmentos de códigos."""
        try:
            ExportManager.export_code_fragments(selected_rows, fragment_rows, export_path)
            self.export_success.emit("Fragmentos de códigos", export_path)
        except Exception as e:
            self.export_error.emit("Fragmentos de códigos", str(e))

    # ==========================================
    # SLOTS/MÉTODOS (Gestión de EDDs)
    # ==========================================
    def req_open_project(self, project_path):
        """Petición para abrir o crear un proyecto y cargar sus EDDs."""
        try:
            from core.project import Project
            import os
            name = os.path.basename(project_path)
            base = os.path.dirname(project_path)
            self.current_project = Project(name, base)
            self.current_project.load_edds()
            self.project_loaded.emit(self.current_project)
            self.edds_updated.emit(self.current_project.codes_dict, self.current_project.themes_dict)
        except Exception as e:
            self.error_occurred.emit(f"Error al abrir proyecto: {str(e)}")

    def req_set_project(self, project):
        """Sincroniza el proyecto abierto en la interfaz con el backend."""
        self.current_project = project

    def req_save_project(self):
        """Petición para guardar el estado de las EDDs."""
        if not self.current_project: return
        try:
            self.current_project.save_edds()
        except Exception as e:
            self.error_occurred.emit(f"Error al guardar proyecto: {str(e)}")

    def req_add_code(self, code_name, hexcolor, memo):
        if not self.current_project: return
        self.current_project.add_code(code_name, hexcolor, memo)
        self.current_project.save_edds()
        self.edds_updated.emit(self.current_project.codes_dict, self.current_project.themes_dict)

    def req_delete_code(self, code_name):
        if not self.current_project: return
        self.current_project.delete_code(code_name)
        self.current_project.save_edds()
        self.edds_updated.emit(self.current_project.codes_dict, self.current_project.themes_dict)
        
    def req_update_code(self, old_name, new_name, hexcolor, memo):
        if not self.current_project: return
        self.current_project.update_code(old_name, new_name, hexcolor, memo)
        self.current_project.save_edds()
        self.edds_updated.emit(self.current_project.codes_dict, self.current_project.themes_dict)

# En logica.py
    def req_add_fragment(self, code_name, doc_name, fragment_data):
        if not self.current_project: return
        self.current_project.add_fragment(code_name, doc_name, fragment_data)
        self.current_project.save_edds()
        self.edds_updated.emit(self.current_project.codes_dict, self.current_project.themes_dict)