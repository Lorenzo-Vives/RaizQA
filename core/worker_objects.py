from PySide6.QtCore import QObject, Signal, QRunnable, Slot
from core.search_manager import SearchManager

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
            self.signals.error.emit(f"Error en búsqueda: {str(e)}")