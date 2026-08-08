from PySide6.QtCore import QObject, Signal, QRunnable, Slot
from core.search_manager import SearchManager
from core.export_manager import ExportManager
from core.import_manager import ImportManager
from core.merge_manager import MergeManager
import traceback

class BuscadorWorkerSignals(QObject):
    """
    Señales dedicadas para comunicarse con el ControladorLogico.
    Se necesita esta clase intermedia porque QRunnable no hereda de QObject
    y no puede tener señales propias nativas.
    """
    finished = Signal(dict)
    error = Signal(str)


class BuscadorWorker(QRunnable):
    """
    Worker encapsulado que ejecuta la búsqueda global en un hilo
    del QThreadPool, manteniendo la interfaz gráfica responsiva.
    """
    def __init__(self, term, project, codes, memo_manager):
        super().__init__()
        self.term = term
        self.project = project
        self.codes = codes
        self.memo_manager = memo_manager
        self.signals = BuscadorWorkerSignals()

    @Slot()
    def run(self):
        try:
            # Invoca al administrador de búsquedas en este hilo secundario
            results = SearchManager.run_global_search(
                self.term, self.project, self.codes, self.memo_manager
            )
            
            # Validar si hubo alguna coincidencia
            if results and any([
                results["search_matches"], 
                results["doc_matches"], 
                results["code_matches"], 
                results["memo_matches"]
            ]):
                self.signals.finished.emit(results)
            else:
                self.signals.error.emit("Sin coincidencias en documentos, códigos o memos.")
                 
        except Exception as e:
            self.signals.error.emit(f"Error en búsqueda: {e}")


class ImportExportWorkerSignals(QObject):
    finished = Signal(str)  # Devuelve la ruta resultante
    error = Signal(str)

class ExportWorker(QRunnable):
    def __init__(self, project_path, export_path):
        super().__init__()
        self.project_path = project_path
        self.export_path = export_path
        self.signals = ImportExportWorkerSignals()

    @Slot()
    def run(self):
        try:
            result_path = ExportManager.export_project_to_rqa(self.project_path, self.export_path)
            self.signals.finished.emit(result_path)
        except Exception as e:
            self.signals.error.emit(f"Error al exportar el proyecto: {e}")

class ImportWorker(QRunnable):
    def __init__(self, rqa_path, dest_base_path):
        super().__init__()
        self.rqa_path = rqa_path
        self.dest_base_path = dest_base_path
        self.signals = ImportExportWorkerSignals()

    @Slot()
    def run(self):
        try:
            result_path = ImportManager.import_project_from_rqa(self.rqa_path, self.dest_base_path)
            self.signals.finished.emit(result_path)
        except Exception as e:
            self.signals.error.emit(f"Error en importación de proyecto: {e}")

class ExportExchangeWorker(QRunnable):
    """
    Worker que ejecuta la exportación de archivos de intercambio (.rex)
    en un hilo separado para no bloquear la interfaz gráfica.
    """
    def __init__(self, project, docs, codes, options, export_path):
        super().__init__()
        self.project = project
        self.docs = docs
        self.codes = codes
        self.options = options
        self.export_path = export_path
        self.signals = ImportExportWorkerSignals()

    @Slot()
    def run(self):
        try:
            path = ExportManager.export_exchange_to_rex(
                self.project, self.docs, self.codes, self.options, self.export_path
            )
            self.signals.finished.emit(path)
        except Exception as e:
            self.signals.error.emit(f"Error al exportar archivo de intercambio: {e}")

class ImportExchangeWorker(QRunnable):
    """
    Worker que ejecuta la importación de archivos de intercambio (.rex)
    en un hilo separado para evitar que la interfaz de usuario se congele.
    """
    def __init__(self, rex_path, target_project, import_data):
        super().__init__()
        self.rex_path = rex_path
        self.target_project = target_project
        self.import_data = import_data
        self.signals = ImportExportWorkerSignals()

    @Slot()
    def run(self):
        try:
            ImportManager.import_exchange_from_rex(
                self.rex_path, self.target_project, self.import_data
            )
            self.signals.finished.emit(self.target_project.path)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.signals.error.emit(f"Error al importar archivo de intercambio: {e}")

class MergeWorkerSignals(QObject):
    finished = Signal()
    error = Signal(str)

class MergeWorker(QRunnable):
    """
    Worker que ejecuta la combinación (merge) de dos proyectos
    en un hilo separado.
    """
    def __init__(self, target_project, rqa_path, settings):
        super().__init__()
        self.target_project = target_project
        self.rqa_path = rqa_path
        self.settings = settings
        self.signals = MergeWorkerSignals()

    @Slot()
    def run(self):
        try:
            # El lock protege save_state() de una carrera con el hilo principal
            with self.target_project._state_lock:
                summary = MergeManager.merge_projects(self.target_project, self.rqa_path, self.settings)
            self.signals.finished.emit(summary)
        except Exception as e:
            traceback.print_exc()
            self.signals.error.emit(f"Error al combinar proyectos: {str(e)}")