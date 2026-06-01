import pytest
import os
from PySide6.QtWidgets import QApplication

from core.logica import ControladorLogico
from core.project import Project
from gui.main_window import RaizQAGUI

@pytest.fixture
def temp_project(tmp_path):
    """Crea un proyecto temporal para pruebas que involucran modificaciones reales en disco."""
    project = Project("TestProject", str(tmp_path))
    # load_project_data will create necessary dirs if they don't exist
    project.load_project_data()
    return project

@pytest.fixture
def logica(qapp):
    """Fixture para la lógica base."""
    return ControladorLogico()

@pytest.fixture
def main_window(qapp, logica):
    """Fixture para la ventana principal instanciada limpia."""
    window = RaizQAGUI()
    
    # We wire up the essential signals just like in main.py
    # UI -> Backend
    window.signal_req_global_search.connect(logica.req_global_search)
    window.signal_req_set_project.connect(logica.req_set_project)
    window.signal_req_save_all.connect(logica.req_save_all)
    window.signal_req_add_code.connect(logica.req_add_code)
    window.signal_req_delete_code.connect(logica.req_delete_code)
    window.signal_req_update_code.connect(logica.req_update_code)
    window.signal_req_add_fragment.connect(logica.req_add_fragment)
    window.signal_req_update_document.connect(logica.req_update_document)
    window.signal_req_export_project.connect(logica.req_export_project)
    window.signal_req_import_project.connect(logica.req_import_project)
    window.signal_req_export_exchange.connect(logica.req_export_exchange)
    window.signal_req_import_exchange.connect(logica.req_import_exchange)
    window.signal_req_merge_projects.connect(logica.req_merge_projects)
    
    # Backend -> UI
    logica.search_completed.connect(window.handle_search_completed)
    logica.search_failed.connect(window.handle_search_failed)
    logica.edds_updated.connect(window.handle_edds_updated)
    logica.error_occurred.connect(lambda e: print(f"Error signal: {e}"))
    
    return window
