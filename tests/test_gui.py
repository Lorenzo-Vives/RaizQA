import pytest
from unittest.mock import patch
from PySide6.QtGui import QColor, QPalette, QTextCursor
from PySide6.QtWidgets import QDialog, QFileDialog


def _background_color_at(text_area, position):
    cursor = QTextCursor(text_area.document())
    cursor.setPosition(position)
    cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
    return cursor.charFormat().background().color().name()


def _prepare_text_document(main_window, temp_project, text="Texto para codificar"):
    main_window.current_project = temp_project
    main_window.signal_req_set_project.emit(temp_project)
    main_window.current_doc = "documento.txt"
    main_window.text_area.setPlainText(text)
    main_window.highlighted = []

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
    main_window.signal_req_add_code.emit("GUI_Code", "#00ff00", "GUI Memo", "")
    
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


def test_create_code_highlights_selection_immediately(main_window, temp_project, monkeypatch):
    """El color debe aparecer al aceptar el codigo, sin cambiar de documento."""
    from gui.dialogs.new_code_dialog import NewCodeDialog

    _prepare_text_document(main_window, temp_project)
    color = "#ffcc00"
    monkeypatch.setattr(NewCodeDialog, "exec", lambda self: QDialog.Accepted)
    monkeypatch.setattr(NewCodeDialog, "get_data", lambda self: ("Codigo inmediato", color, ""))

    main_window.create_new_code("Texto", 0, 5)

    expected = main_window._adjust_highlight_color(QColor(color)).name()
    assert _background_color_at(main_window.text_area, 2) == expected
    assert len(main_window.highlighted) == 1
    assert not main_window.text_area.textCursor().hasSelection()


def test_add_to_existing_code_highlights_immediately(main_window, temp_project):
    """Agregar a un codigo existente comparte el mismo repintado inmediato."""
    _prepare_text_document(main_window, temp_project)
    color = "#4db6ac"
    main_window.signal_req_add_code.emit("Codigo existente", color, "", "")

    main_window.add_to_existing_code("Codigo existente", "Texto", 0, 5)

    expected = main_window._adjust_highlight_color(QColor(color)).name()
    assert _background_color_at(main_window.text_area, 2) == expected
    assert len(main_window.highlighted) == 1


def test_subcode_in_vivo_path_highlights_immediately(main_window, temp_project, monkeypatch):
    """La ruta compartida por subcodigos e in vivo conserva el repintado inmediato."""
    from gui.dialogs.new_code_dialog import NewCodeDialog

    _prepare_text_document(main_window, temp_project)
    main_window.signal_req_add_code.emit("Codigo padre", "#ff7043", "", "")
    main_window.populate_code_tree()
    parent_item = main_window.find_tree_item("Codigo padre")
    color = "#9575cd"
    monkeypatch.setattr(NewCodeDialog, "exec", lambda self: QDialog.Accepted)
    monkeypatch.setattr(NewCodeDialog, "get_data", lambda self: ("Subcodigo in vivo", color, ""))

    main_window.create_new_code("Texto", 0, 5, parent_item=parent_item, code_label="Texto")

    assert main_window.codes_dict["Subcodigo in vivo"]["parent"] == "Codigo padre"
    expected = main_window._adjust_highlight_color(QColor(color)).name()
    assert _background_color_at(main_window.text_area, 2) == expected
    assert len(main_window.highlighted) == 1


def test_highlight_survives_theme_and_document_changes(
    main_window, temp_project, monkeypatch, tmp_path
):
    """Repintar o volver al documento no pierde ni duplica el fragmento."""
    from gui.dialogs.new_code_dialog import NewCodeDialog

    source_a = tmp_path / "documento_a.txt"
    source_b = tmp_path / "documento_b.txt"
    source_a.write_text("Texto para codificar", encoding="utf-8")
    source_b.write_text("Documento alternativo", encoding="utf-8")
    doc_a, _ = temp_project.import_document(str(source_a))
    doc_b, _ = temp_project.import_document(str(source_b))

    main_window.current_project = temp_project
    main_window.signal_req_set_project.emit(temp_project)
    item_a = main_window._add_doc_item(doc_a)
    item_b = main_window._add_doc_item(doc_b)
    main_window.display_document(item_a)

    color = "#64b5f6"
    monkeypatch.setattr(NewCodeDialog, "exec", lambda self: QDialog.Accepted)
    monkeypatch.setattr(NewCodeDialog, "get_data", lambda self: ("Codigo persistente", color, ""))
    main_window.create_new_code("Texto", 0, 5)

    assert len(main_window.highlighted) == 1
    main_window.toggle_theme()
    expected_dark = main_window._adjust_highlight_color(QColor(color)).name()
    assert _background_color_at(main_window.text_area, 2) == expected_dark

    main_window.display_document(item_b)
    assert main_window.highlighted == []
    main_window.display_document(item_a)

    assert len(main_window.highlighted) == 1
    assert _background_color_at(main_window.text_area, 2) == expected_dark


def test_new_code_dialog_fields_are_readable_in_dark_mode(main_window, qapp):
    """Los campos del dialogo deben usar fondo, texto y placeholder del tema oscuro."""
    from gui.dialogs.new_code_dialog import NewCodeDialog
    from gui.theme import get_theme

    main_window.is_dark_mode = True
    main_window.apply_theme()
    dialog = NewCodeDialog(main_window.COLOR_PALETTE, parent=main_window)
    dialog.show()
    qapp.processEvents()

    theme = get_theme(True)
    for field in (dialog.name_input, dialog.memo_input):
        palette = field.palette()
        assert palette.color(QPalette.Base).name() == theme["text_bg"]
        assert palette.color(QPalette.Text).name() == theme["text_fg"]
        assert palette.color(QPalette.PlaceholderText).name() == theme["muted_text"]

    dialog.close()


def test_image_context_menu_routes_selection_to_new_code(main_window, monkeypatch):
    """El menu contextual de imagen debe crear un codigo para la zona elegida."""
    import gui.main_window as main_window_module

    class FakeAction:
        def __init__(self, text):
            self._text = text

        def text(self):
            return self._text

    class FakeMenu:
        def __init__(self, parent=None):
            self._actions = []

        def addAction(self, text):
            action = FakeAction(text)
            self._actions.append(action)
            return action

        def addSeparator(self):
            return None

        def actions(self):
            return self._actions

        def exec(self, position):
            return next(
                action for action in self._actions if action.text() == "Crear nuevo codigo para zona"
            )

    selection = {
        "rect": {"x": 10, "y": 20, "w": 100, "h": 80},
        "image_size": {"w": 800, "h": 600},
    }
    captured = {}

    monkeypatch.setattr(main_window, "_image_selection_payload", lambda: selection)
    monkeypatch.setattr(main_window, "_prompt_image_note", lambda *args, **kwargs: "Zona de imagen")
    monkeypatch.setattr(
        main_window,
        "create_new_code",
        lambda *args, **kwargs: captured.update({"args": args, "kwargs": kwargs}),
    )
    monkeypatch.setattr(main_window_module, "QMenu", FakeMenu)

    main_window._image_context_menu()

    assert captured["kwargs"]["is_image"] is True
    assert captured["kwargs"]["note"] == "Zona de imagen"
    assert captured["kwargs"]["image_selection"] == selection


def test_create_image_code_persists_and_renders_fragment(
    main_window, temp_project, monkeypatch
):
    """Crear el codigo debe guardar y enviar la zona al visor de imagen."""
    from gui.dialogs.new_code_dialog import NewCodeDialog

    selection = {
        "rect": {"x": 10, "y": 20, "w": 100, "h": 80},
        "image_size": {"w": 800, "h": 600},
    }
    rendered = []
    color = "#ff7043"
    main_window.current_project = temp_project
    main_window.signal_req_set_project.emit(temp_project)
    main_window.current_doc = "imagen.jpeg"
    monkeypatch.setattr(NewCodeDialog, "exec", lambda self: QDialog.Accepted)
    monkeypatch.setattr(NewCodeDialog, "get_data", lambda self: ("Codigo de imagen", color, ""))
    monkeypatch.setattr(
        main_window.image_viewer,
        "set_fragments",
        lambda fragments: rendered.append(list(fragments)),
    )

    main_window.create_new_code(
        "",
        None,
        None,
        is_image=True,
        note="Zona de imagen",
        image_selection=selection,
    )

    stored = main_window.codes_dict["Codigo de imagen"]["fragments"]["imagen.jpeg"]
    assert stored == [{"type": "image", **selection, "note": "Zona de imagen"}]
    assert len(main_window.highlighted) == 1
    assert rendered[-1] == main_window.highlighted


def test_create_code_for_whole_image_uses_full_image_rect(
    main_window, temp_project, monkeypatch
):
    """Sin zona seleccionada, el fragmento debe cubrir la imagen completa."""
    from gui.dialogs.new_code_dialog import NewCodeDialog

    image_size = {"w": 640, "h": 480}
    main_window.current_project = temp_project
    main_window.signal_req_set_project.emit(temp_project)
    main_window.current_doc = "imagen_completa.jpeg"
    monkeypatch.setattr(NewCodeDialog, "exec", lambda self: QDialog.Accepted)
    monkeypatch.setattr(NewCodeDialog, "get_data", lambda self: ("Imagen completa", "#ffcc00", ""))
    monkeypatch.setattr(main_window.image_viewer, "image_size", lambda: image_size)

    main_window.create_new_code(
        "",
        None,
        None,
        is_image=True,
        note="Imagen completa",
        image_selection=None,
    )

    stored = main_window.codes_dict["Imagen completa"]["fragments"]["imagen_completa.jpeg"]
    assert stored == [{
        "type": "image",
        "rect": {"x": 0, "y": 0, "w": 640, "h": 480},
        "image_size": image_size,
        "note": "Imagen completa",
    }]
