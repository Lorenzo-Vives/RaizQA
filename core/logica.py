from PySide6.QtCore import QObject, Signal, QThreadPool

from core.search_manager import SearchManager
from core.export_manager import ExportManager
from core.worker_objects import (
    BuscadorWorker,
    ExportWorker,
    ImportWorker,
    ExportExchangeWorker,
    ImportExchangeWorker,
    MergeWorker,
)
from core.project import Project


class ControladorLogico(QObject):
    """
    Cerebro del backend. Mantiene el estado del programa y orquesta
    operaciones pesadas sin conocer detalles de la interfaz gráfica.
    """

    # ==========================================
    # SEÑALES (Backend -> Interfaz Gráfica)
    # ==========================================
    project_saved = Signal()                
    project_loaded = Signal(object)      # Emite el objeto Project cuando carga
    search_completed = Signal(dict)      # Emite resultados de la búsqueda
    search_failed = Signal(str)          # Emite un mensaje si no hay resultados o error

    export_success = Signal(str, str)    # Emite (Tipo de exportación, Ruta del archivo)
    export_error = Signal(str, str)      # Emite (Tipo de exportación, Error)

    edds_updated = Signal(dict, dict)    # Emite (codes_dict, themes_dict) cada vez que cambian
    error_occurred = Signal(str)         # Emite mensajes de error generales

    project_exported = Signal(str)       # Emite la ruta donde se guardó el .rqa
    project_imported = Signal(str)       # Emite la ruta de la carpeta del proyecto extraído
    project_merged = Signal(dict)        # Emite el resumen de la fusión al finalizar

    # SEÑALES DE GESTIÓN DE PROYECTO / DOCUMENTOS / GRUPOS / MEMOS
    document_imported = Signal(str, str, dict)   # file_name, folder, doc_groups
    group_added = Signal(str, dict)              # group_name, doc_groups
    document_moved = Signal(str, str, dict)      # doc_name, target_folder, doc_groups
    memo_updated = Signal(str, str)              # code_name, memo_text ("" si fue eliminado)

    def __init__(self):
        super().__init__()
        self.current_project = None
        self._workers = set()
        self._threadpool = QThreadPool.globalInstance()

    # ==========================================
    # ORQUESTACIÓN DE WORKERS (DRY)
    # ==========================================
    def _dispatch_worker(self, worker, on_finished, on_error=None):
        """
        Ejecuta un worker en segundo plano y conecta sus señales
        de forma segura, evitando duplicación de código.
        """
        self._workers.add(worker)

        def _cleanup_and_emit(callback, *args):
            self._workers.discard(worker)
            if callback:
                callback(*args)

        worker.signals.finished.connect(
            lambda *args, cb=on_finished: _cleanup_and_emit(cb, *args)
        )
        if on_error:
            worker.signals.error.connect(
                lambda *args, cb=on_error: _cleanup_and_emit(cb, *args)
            )

        self._threadpool.start(worker)

    # ==========================================
    # BÚSQUEDA
    # ==========================================
    def req_global_search(self, term, project, codes, memo_manager):
        """Petición asíncrona de la interfaz para iniciar la búsqueda."""
        if not term:
            self.search_failed.emit("El término de búsqueda está vacío.")
            return

        worker = BuscadorWorker(term, project, codes, memo_manager)
        self._dispatch_worker(
            worker,
            on_finished=lambda res: self.search_completed.emit(res),
            on_error=lambda err: self.search_failed.emit(err),
        )

    # ==========================================
    # EXPORTACIONES SÍNCRONAS
    # ==========================================
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
    # EXPORTACIONES / IMPORTACIONES ASÍNCRONAS
    # ==========================================
    def req_export_project(self, export_path):
        """Petición asíncrona para empaquetar el proyecto actual en un .rqa."""
        if not self.current_project:
            self.error_occurred.emit("No hay proyecto abierto para exportar.")
            return

        worker = ExportWorker(self.current_project.path, export_path)
        self._dispatch_worker(
            worker,
            on_finished=lambda path: self.project_exported.emit(path),
            on_error=lambda e: self.export_error.emit("Proyecto .rqa", e),
        )

    def req_import_project(self, rqa_path, dest_base_path):
        """Petición asíncrona para desempaquetar un archivo .rqa."""
        worker = ImportWorker(rqa_path, dest_base_path)
        self._dispatch_worker(
            worker,
            on_finished=lambda path: self.project_imported.emit(path),
            on_error=lambda e: self.error_occurred.emit(f"Error al importar proyecto: {e}"),
        )

    def req_export_exchange(self, docs, codes, options, export_path):
        """Petición asíncrona para exportar un paquete de intercambio .rex."""
        if not self.current_project:
            self.error_occurred.emit("No hay proyecto abierto para exportar.")
            return

        worker = ExportExchangeWorker(self.current_project, docs, codes, options, export_path)
        self._dispatch_worker(
            worker,
            on_finished=lambda path: self.project_exported.emit(path),
            on_error=lambda e: self.error_occurred.emit(f"Error al exportar intercambio: {e}"),
        )

    def req_import_exchange(self, rex_path, import_data):
        """Petición asíncrona para importar un paquete de intercambio .rex."""
        if not self.current_project:
            self.error_occurred.emit("No hay proyecto abierto para importar.")
            return

        worker = ImportExchangeWorker(rex_path, self.current_project, import_data)
        self._dispatch_worker(
            worker,
            on_finished=lambda path: self.project_imported.emit(path),
            on_error=lambda e: self.error_occurred.emit(f"Error al importar intercambio: {e}"),
        )

    def req_merge_projects(self, rqa_path, settings):
        """Petición asíncrona para combinar un proyecto .rqa en el actual."""
        if not self.current_project:
            self.error_occurred.emit("No hay proyecto abierto para combinar.")
            return

        worker = MergeWorker(self.current_project, rqa_path, settings)
        self._dispatch_worker(
            worker,
            on_finished=lambda summary: self.project_merged.emit(summary),
            on_error=lambda e: self.error_occurred.emit(f"Error al combinar proyectos: {e}"),
        )

    # ==========================================
    # GESTIÓN DE PROYECTO
    # ==========================================
    
    def req_save_project(self):
        if not self.current_project:
            return
        try:
            self.current_project.save_state()
            self.project_saved.emit()
        except Exception:
            self.error_occurred.emit(f"No se pudo guardar el proyecto:\n{str(e)}")
            return
    
    def req_create_project(self, name, working_dir):
        """Petición para crear un proyecto nuevo. El controlador es el único dueño de current_project."""
        try:
            self.current_project = Project(name, working_dir)
        except Exception as e:
            self.error_occurred.emit(f"Error al crear proyecto: {str(e)}")
            return
        self.project_loaded.emit(self.current_project)

    def req_open_project(self, name, working_dir):
        """Petición para abrir un proyecto existente y cargar sus EDDs."""
        try:
            self.current_project = Project(name, working_dir)
        except Exception as e:
            self.error_occurred.emit(f"Error al abrir proyecto: {str(e)}")
            return
        self.project_loaded.emit(self.current_project)

    def req_import_document(self, file_path, folder):
        """Petición para importar un documento y ubicarlo en la carpeta indicada."""
        if not self.current_project:
            self.error_occurred.emit("No hay proyecto abierto para importar.")
            return
        try:
            file_name, _ = self.current_project.import_document(file_path)
            if folder != "__root__":
                self.current_project.add_document_to_group(file_name, folder)
            self.document_imported.emit(file_name, folder, self.current_project.group_manager.groups)
        except ValueError as e:
            self.error_occurred.emit(str(e))
        except Exception as e:
            self.error_occurred.emit(f"No se pudo procesar el archivo: {str(e)}")

    def req_add_group(self, name):
        """Petición para crear una carpeta/grupo de documentos nueva."""
        if not self.current_project:
            return
        try:
            self.current_project.add_group(name)
            self.group_added.emit(name, self.current_project.group_manager.groups)
        except Exception as e:
            self.error_occurred.emit(f"Error al crear carpeta: {str(e)}")

    def req_move_document(self, doc_name, target_folder):
        """Petición para mover un documento a otra carpeta (o a la raíz)."""
        if not self.current_project:
            return
        try:
            if target_folder == "__root__":
                self.current_project.group_manager.remove_document_from_all_groups(doc_name)
                self.current_project.save_state()
            else:
                self.current_project.add_document_to_group(doc_name, target_folder)
            self.document_moved.emit(
                doc_name, target_folder, self.current_project.group_manager.groups
            )
        except Exception as e:
            self.error_occurred.emit(f"Error al mover documento: {str(e)}")

    def req_sync_doc_groups(self, doc_groups):
        """Petición para reemplazar la estructura completa de grupos (drag-and-drop)."""
        if not self.current_project:
            return
        try:
            self.current_project.sync_doc_groups(doc_groups)
        except Exception as e:
            self.error_occurred.emit(f"Error al sincronizar carpetas: {str(e)}")

    def req_sync_code_hierarchy(self, hierarchy):
        """Petición para reasignar la jerarquía padre/hijo de los códigos (drag-and-drop)."""
        if not self.current_project:
            return
        try:
            self.current_project.sync_code_hierarchy(hierarchy)
            self.edds_updated.emit(
                self.current_project.code_manager.get_all_codes(),
                self.current_project.theme_manager.get_all_themes(),
            )
        except Exception as e:
            self.error_occurred.emit(f"Error al reorganizar códigos: {str(e)}")

    def req_sync_themes(self, themes_data):
        """Petición para sincronizar temas/categorías desde el diálogo de temas."""
        if not self.current_project:
            return
        try:
            self.current_project.sync_themes(themes_data)
            self.edds_updated.emit(
                self.current_project.code_manager.get_all_codes(),
                self.current_project.theme_manager.get_all_themes(),
            )
        except Exception as e:
            self.error_occurred.emit(f"Error al sincronizar temas: {str(e)}")

    def req_save_case_studies(self, case_studies):
        """Petición para guardar la lista de estudios de caso."""
        if not self.current_project:
            return
        try:
            self.current_project.save_case_studies(case_studies)
        except Exception as e:
            self.error_occurred.emit(f"Error al guardar estudios de caso: {str(e)}")

    def req_set_memo(self, code_name, memo_text):
        """Petición para crear o actualizar el memo de un código."""
        if not self.current_project:
            return
        try:
            self.current_project.set_memo(code_name, memo_text)
            self.memo_updated.emit(code_name, memo_text)
        except Exception as e:
            self.error_occurred.emit(f"Error al guardar memo: {str(e)}")

    def req_delete_memo(self, code_name):
        """Petición para eliminar el memo de un código."""
        if not self.current_project:
            return
        try:
            self.current_project.delete_memo(code_name)
            self.memo_updated.emit(code_name, "")
        except Exception as e:
            self.error_occurred.emit(f"Error al eliminar memo: {str(e)}")

    # ==========================================
    # GESTIÓN DE CÓDIGOS
    # ==========================================
    def req_add_code(self, code_name, hexcolor, memo, parent_name=""):
        if not self.current_project:
            return
        try:
            p_name = parent_name if parent_name else None
            self.current_project.add_code(code_name, hexcolor, memo, parent_name=p_name)

            if memo and hasattr(self.current_project.memo_manager, "add_or_update_memo"):
                try:
                    self.current_project.memo_manager.add_or_update_memo(code_name, memo)
                except Exception:
                    pass

            self.edds_updated.emit(
                self.current_project.code_manager.get_all_codes(),
                self.current_project.theme_manager.get_all_themes(),
            )
        except Exception as e:
            self.error_occurred.emit(f"Error al agregar código: {str(e)}")

    def req_delete_code(self, code_name, cascade=False):
        if not self.current_project:
            return
        try:
            self.current_project.delete_code(code_name, cascade=cascade)
            self.edds_updated.emit(
                self.current_project.code_manager.get_all_codes(),
                self.current_project.theme_manager.get_all_themes(),
            )
        except Exception as e:
            self.error_occurred.emit(f"Error al eliminar código: {str(e)}")

    def req_update_code(self, old_name, new_name, hexcolor, memo):
        if not self.current_project:
            return
        try:
            self.current_project.update_code(old_name, new_name, hexcolor, memo)
            self.edds_updated.emit(
                self.current_project.code_manager.get_all_codes(),
                self.current_project.theme_manager.get_all_themes(),
            )
        except Exception as e:
            self.error_occurred.emit(f"Error al actualizar código: {str(e)}")

    def req_add_fragment(self, code_name, doc_name, fragment_data):
        if not self.current_project:
            return
        try:
            self.current_project.add_fragment(code_name, doc_name, fragment_data)
            self.edds_updated.emit(
                self.current_project.code_manager.get_all_codes(),
                self.current_project.theme_manager.get_all_themes(),
            )
        except Exception as e:
            self.error_occurred.emit(f"Error al agregar fragmento: {str(e)}")

    # ==========================================
    # GESTIÓN DE DOCUMENTOS
    # ==========================================
    def req_update_document(self, doc_name, new_text):
        """Petición de la UI para sobrescribir un documento editado."""
        if not self.current_project:
            return
        try:
            self.current_project.update_document_text(doc_name, new_text)
            self.edds_updated.emit(
                self.current_project.code_manager.get_all_codes(),
                self.current_project.theme_manager.get_all_themes(),
            )
        except Exception as e:
            self.error_occurred.emit(f"Error al guardar el documento editado: {str(e)}")