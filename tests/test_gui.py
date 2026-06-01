import pytest
from unittest.mock import patch
from PySide6.QtWidgets import QFileDialog

def test_window_initialization(main_window):
    """Prueba que la ventana principal inicialice correctamente."""
    assert main_window.windowTitle() == "RaizQA 🌱"
    assert main_window.current_project is None
    assert main_window.lbl_project.text() == "Proyecto: Ninguno"

def test_create_project_gui(main_window, monkeypatch, tmp_path):
    """Prueba el flujo de crear un proyecto desde la GUI usando Mocks para QInputDialog."""
    from PySide6.QtWidgets import QInputDialog, QMessageBox
    
    # 1. Necesita working dir
    main_window.working_dir = str(tmp_path)
    
    # 2. Mockear inputs
    monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("NuevoGuiProject", True))
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    
    main_window.create_project()
    
    assert main_window.current_project is not None
    assert main_window.current_project.name == "NuevoGuiProject"
    assert "NuevoGuiProject" in main_window.lbl_project.text()

def test_add_code_updates_ui(main_window, temp_project):
    """Prueba que al añadir un código, el árbol de códigos en la UI se refresque."""
    # Sincronizar UI con el backend simulado
    main_window.current_project = temp_project
    main_window.signal_req_set_project.emit(temp_project)
    
    # Emitimos señal para añadir código (UI -> Backend)
    main_window.signal_req_add_code.emit("GUI_Code", "#00ff00", "GUI Memo")
    
    # Revisamos que main_window.codes_dict se actualizó a través de handle_edds_updated
    assert "GUI_Code" in main_window.codes_dict
    
    # Se asume que populate_code_tree funciona si handle_edds_updated actualizó el estado.

def test_search_ui(main_window, temp_project):
    """Prueba el comportamiento visual del buscador global."""
    main_window.signal_req_set_project.emit(temp_project)
    
    # Ingresar término en QLineEdit
    main_window.search_field.setText("prueba")
    
    # Mockear la señal search_completed del backend enviando resultados directos
    fake_results = {
        "search_matches": [{"doc": "doc1.txt", "start": 0}],
        "doc_matches": ["doc1.txt"],
        "code_matches": [],
        "memo_matches": []
    }
    
    # Usamos handle_search_completed directamente
    # Para evitar que el QMessageBox con el resumen frene el test, mockeamos QMessageBox
    from PySide6.QtWidgets import QMessageBox
    with patch.object(QMessageBox, 'information'):
        main_window.handle_search_completed(fake_results)
        
    # Verificar que las etiquetas de conteo se actualizan
    assert "1/1" in main_window.lbl_search_count.text()
