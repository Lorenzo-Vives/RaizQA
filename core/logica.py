from PySide6.QtCore import QObject, Signal

from core.search_manager import SearchManager
from core.export_manager import ExportManager
from core.worker_objects import BuscadorWorker, ExportWorker, ImportWorker  

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

    project_exported = Signal(str)       # Emite la ruta donde se guardó el .rqa
    project_imported = Signal(str)       # Emite la ruta de la carpeta del proyecto extraído
    project_merged = Signal()            # Emite cuando la combinación finaliza

    def __init__(self):
        super().__init__()
        # Aquí vivirá el estado global (La instancia del proyecto activo)
        self.current_project = None
        self._workers = set()

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
        self._workers.add(worker)
        
        # 2. Conectar sus señales a los métodos internos de redirección
        worker.signals.finished.connect(lambda res: self._handle_worker_finish(worker, self.search_completed, res))
        worker.signals.error.connect(lambda err: self._handle_worker_finish(worker, self.search_failed, err))
        
        # 3. Ordenar al ThreadPool que lo ejecute en segundo plano
        if not hasattr(self, 'threadpool'):
            from PySide6.QtCore import QThreadPool
            self.threadpool = QThreadPool.globalInstance()
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

    def _handle_worker_finish(self, worker, signal_to_emit, *args):
        self._workers.discard(worker)
        signal_to_emit.emit(*args)
        
    def _handle_worker_error_with_type(self, worker, export_type, error_msg):
        self._workers.discard(worker)
        self.export_error.emit(export_type, error_msg)

    def req_export_project(self, export_path):
        """Petición asíncrona para empaquetar el proyecto actual en un .rqa."""
        if not self.current_project: return
        
        worker = ExportWorker(self.current_project.path, export_path)
        self._workers.add(worker)
        
        worker.signals.finished.connect(lambda path: self._handle_worker_finish(worker, self.project_exported, path))
        worker.signals.error.connect(lambda e: self._handle_worker_error_with_type(worker, "Proyecto .rqa", e))
        
        if not hasattr(self, 'threadpool'):
            from PySide6.QtCore import QThreadPool
            self.threadpool = QThreadPool.globalInstance()
            
        self.threadpool.start(worker)

    def req_import_project(self, rqa_path, dest_base_path):
        """Petición asíncrona para desempaquetar un archivo .rqa."""
        worker = ImportWorker(rqa_path, dest_base_path)
        self._workers.add(worker)
        
        worker.signals.finished.connect(lambda path: self._handle_worker_finish(worker, self.project_imported, path))
        worker.signals.error.connect(lambda e: self._handle_worker_finish(worker, self.error_occurred, e))
        
        if not hasattr(self, 'threadpool'):
            from PySide6.QtCore import QThreadPool
            self.threadpool = QThreadPool.globalInstance()
            
        self.threadpool.start(worker)

    def req_export_exchange(self, docs, codes, options, export_path):
        from core.worker_objects import ExportExchangeWorker
        worker = ExportExchangeWorker(self.current_project, docs, codes, options, export_path)
        self._workers.add(worker)
        
        worker.signals.finished.connect(lambda path: self._handle_worker_finish(worker, self.project_exported, path))
        worker.signals.error.connect(lambda e: self._handle_worker_finish(worker, self.error_occurred, e))
        
        if not hasattr(self, 'threadpool'):
            from PySide6.QtCore import QThreadPool
            self.threadpool = QThreadPool.globalInstance()
            
        self.threadpool.start(worker)

    def req_import_exchange(self, rex_path, import_data):
        from core.worker_objects import ImportExchangeWorker
        worker = ImportExchangeWorker(rex_path, self.current_project, import_data)
        self._workers.add(worker)
        
        worker.signals.finished.connect(lambda path: self._handle_worker_finish(worker, self.project_imported, path))
        worker.signals.error.connect(lambda e: self._handle_worker_finish(worker, self.error_occurred, e))
        
        if not hasattr(self, 'threadpool'):
            from PySide6.QtCore import QThreadPool
            self.threadpool = QThreadPool.globalInstance()
            
        self.threadpool.start(worker)

    def req_merge_projects(self, rqa_path, settings):
        """Petición asíncrona para combinar un proyecto .rqa en el actual."""
        if not self.current_project: return
        
        from core.worker_objects import MergeWorker
        worker = MergeWorker(self.current_project, rqa_path, settings)
        self._workers.add(worker)
        
        worker.signals.finished.connect(lambda: self._handle_worker_finish(worker, self.project_merged))
        worker.signals.error.connect(lambda e: self._handle_worker_finish(worker, self.error_occurred, e))
        
        if not hasattr(self, 'threadpool'):
            from PySide6.QtCore import QThreadPool
            self.threadpool = QThreadPool.globalInstance()
            
        self.threadpool.start(worker)

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
            self.current_project.load_project_data()
            self.project_loaded.emit(self.current_project)
            self.edds_updated.emit(self.current_project.codes_dict, self.current_project.themes_dict)
        except Exception as e:
            self.error_occurred.emit(f"Error al abrir proyecto: {str(e)}")

    def req_set_project(self, project):
        """Sincroniza el proyecto abierto en la interfaz con el backend."""
        self.current_project = project

    def req_save_all(self, state_data):
        """Petición para guardar el estado completo del proyecto."""
        if not self.current_project: return
        try:
            self.current_project.save_project_data(
                documents=state_data.get("documents", []),
                highlights=state_data.get("highlights", {}),
                doc_groups=state_data.get("doc_groups"),
                themes=state_data.get("themes"),
                case_studies=state_data.get("case_studies")
            )
        except Exception as e:
            self.error_occurred.emit(f"Error al guardar proyecto: {str(e)}")

    def req_add_code(self, code_name, hexcolor, memo, parent_name=""):
        if not self.current_project: return
        p_name = parent_name if parent_name else None
        self.current_project.add_code(code_name, hexcolor, memo, parent_name=p_name)

        if memo and hasattr(self.current_project, 'memo_manager'):
            self.current_project.memo_manager.add_or_update_memo(code_name, memo)

        self.edds_updated.emit(self.current_project.codes_dict, self.current_project.themes_dict)

    def req_delete_code(self, code_name, cascade=False):
        if not self.current_project: return
        self.current_project.delete_code(code_name, cascade=cascade)
        self.edds_updated.emit(self.current_project.codes_dict, self.current_project.themes_dict)
        
    def req_update_code(self, old_name, new_name, hexcolor, memo):
        if not self.current_project: return
        self.current_project.update_code(old_name, new_name, hexcolor, memo)
        self.edds_updated.emit(self.current_project.codes_dict, self.current_project.themes_dict)

    def req_add_fragment(self, code_name, doc_name, fragment_data):
        if not self.current_project: return
        self.current_project.add_fragment(code_name, doc_name, fragment_data)
        self.edds_updated.emit(self.current_project.codes_dict, self.current_project.themes_dict)

    def req_update_document(self, doc_name, new_text):
        """Petición de la UI para sobrescribir un documento editado."""
        if not self.current_project: return
        try:
            # 1. El proyecto actualiza el archivo y resincroniza los índices
            self.current_project.update_document_text(doc_name, new_text)
            
            # 2. Emitimos la señal para que la UI repinte los subrayados 
            # en sus nuevas posiciones exactas.
            self.edds_updated.emit(self.current_project.codes_dict, self.current_project.themes_dict)
            
        except Exception as e:
            self.error_occurred.emit(f"Error al guardar el documento editado: {str(e)}")