import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton
from core.project import Project
from gui.dialogs.themes_categories_dialog import ThemesCategoriesDialog
from gui.dialogs.wordcloud_dialog import ReadableArrowSpinBox, WordCloudDialog
from gui.utils import hydrate_codes_dict


def test_delete_fragment_by_code_document_and_index(temp_project):
    temp_project.add_code("Codigo")
    first = {"type": "text", "start": 0, "end": 4}
    second = {"type": "text", "start": 5, "end": 9}
    temp_project.add_fragment("Codigo", "doc.txt", first)
    temp_project.add_fragment("Codigo", "doc.txt", second)

    assert temp_project.delete_fragment("Codigo", "doc.txt", 0) is True
    assert temp_project.codes_dict["Codigo"]["fragments"]["doc.txt"] == [second]
    assert temp_project.delete_fragment("Codigo", "doc.txt", 0) is True
    assert "doc.txt" not in temp_project.codes_dict["Codigo"]["fragments"]
    assert temp_project.delete_fragment("Codigo", "doc.txt", 0) is False


def test_hydrate_codes_dict_is_detached_and_skips_invalid_or_image_fragments(temp_project):
    document = temp_project.documents_path + "/doc.txt"
    with open(document, "w", encoding="utf-8") as handle:
        handle.write("uno dos tres")
    source = {
        "Codigo": {
            "fragments": {
                "doc.txt": [
                    {"type": "text", "start": 0, "end": 3},
                    {"type": "image", "rect": {"x": 1, "y": 2, "w": 3, "h": 4}},
                    {"type": "text", "start": -1, "end": 99},
                ]
            }
        }
    }

    hydrated = hydrate_codes_dict(source, temp_project)

    assert hydrated is not source
    assert hydrated["Codigo"]["fragments"]["doc.txt"][0]["text"] == "uno"
    assert "text" not in hydrated["Codigo"]["fragments"]["doc.txt"][1]
    assert "text" not in hydrated["Codigo"]["fragments"]["doc.txt"][2]
    assert "text" not in source["Codigo"]["fragments"]["doc.txt"][0]


def test_theme_formats_are_synchronized_and_cleaned(temp_project):
    temp_project.add_code("A")
    temp_project.add_code("B")
    temp_project.themes_dict = {"Tema": {"memo": "memo conservado", "codes": ["A"]}}

    normalized = temp_project.sync_themes(
        [{"name": "Tema", "codes": ["B", "B", "inexistente"]}]
    )

    assert normalized == [{"name": "Tema", "memo": "memo conservado", "codes": ["B"]}]
    assert temp_project.themes_dict == {
        "Tema": {"memo": "memo conservado", "codes": ["B"]}
    }

    temp_project.save_project_data([], {}, themes=normalized)
    with open(temp_project.state_path, "r", encoding="utf-8") as handle:
        stored = json.load(handle)
    assert stored["themes"] == normalized
    assert stored["themes_dict"] == temp_project.themes_dict


def test_project_loads_theme_list_only(tmp_path):
    project = Project("ListOnly", str(tmp_path))
    project.add_code("A")
    with open(project.state_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "codes_dict": project.codes_dict,
                "themes": [{"name": "Tema", "memo": "m", "codes": ["A", "A"]}],
            },
            handle,
        )

    loaded = project.load_project_data()
    assert loaded["themes"] == [{"name": "Tema", "memo": "m", "codes": ["A"]}]
    assert project.themes_dict["Tema"]["codes"] == ["A"]


def test_project_loads_theme_dictionary_only(tmp_path):
    project = Project("DictOnly", str(tmp_path))
    project.add_code("A")
    with open(project.state_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "codes_dict": project.codes_dict,
                "themes_dict": {"Tema": {"memo": "m", "codes": ["A", "A", "ausente"]}},
            },
            handle,
        )

    loaded = project.load_project_data()
    assert loaded["themes"] == [{"name": "Tema", "memo": "m", "codes": ["A"]}]
    assert project.themes_dict == {"Tema": {"memo": "m", "codes": ["A"]}}


def test_theme_dialog_assigns_without_duplicates_and_preserves_memo(qapp):
    dialog = ThemesCategoriesDialog(
        ["A"], [{"name": "Tema", "memo": "nota", "codes": []}]
    )
    theme_item = dialog.theme_tree.topLevelItem(0)
    dialog.theme_tree.setCurrentItem(theme_item)
    dialog._assign_codes_to_theme(theme_item, ["A", "A"])

    assert dialog.get_themes_data() == [
        {"name": "Tema", "memo": "nota", "codes": ["A"]}
    ]


def test_wordcloud_uses_integrated_readable_arrow_spinbox(qapp):
    class EmptyProject:
        def read_document(self, _name):
            return ""

    dialog = WordCloudDialog(EmptyProject(), [])
    assert isinstance(dialog.spin_min_len, ReadableArrowSpinBox)
    assert not hasattr(dialog, "btn_min_len_up")
    assert not hasattr(dialog, "btn_min_len_down")


def test_menu_buttons_use_one_thin_chevron(main_window):
    menu_buttons = [
        button
        for button in main_window.findChildren(QPushButton)
        if button.menu() is not None
    ]

    assert len(menu_buttons) == 5
    assert all(button.text().endswith("⌄") for button in menu_buttons)
    assert all("▼" not in button.text() for button in menu_buttons)
    assert "QPushButton::menu-indicator" in main_window.styleSheet()
    assert "image: none" in main_window.styleSheet()


def test_projection_mode_restores_geometry_and_scales_dialog(main_window, qapp, monkeypatch):
    main_window.show()
    main_window.setGeometry(90, 80, 900, 560)
    qapp.processEvents()
    original_geometry = main_window.geometry()
    original_size = qapp.font().pointSizeF()

    main_window.toggle_projection_mode(True)
    assert main_window._projection_mode is True
    assert main_window.action_projection_mode.isChecked()
    assert qapp.font().pointSizeF() > original_size

    dialog = ThemesCategoriesDialog([], [], parent=main_window)
    monkeypatch.setattr(dialog, "exec", lambda: 0)
    main_window._exec_dialog(dialog)
    assert dialog.windowState() & Qt.WindowMaximized

    main_window.toggle_projection_mode(False)
    assert main_window._projection_mode is False
    assert qapp.font().pointSizeF() == original_size
    assert main_window.size() == original_geometry.size()
    assert main_window.y() == original_geometry.y()


def test_edd_update_rebuilds_highlights_and_avoids_visual_duplicates(main_window, temp_project):
    doc_name = "doc.txt"
    with open(temp_project.documents_path + "/" + doc_name, "w", encoding="utf-8") as handle:
        handle.write("texto marcado")
    fragment = {"type": "text", "start": 0, "end": 5}
    temp_project.add_code("Hijo", "#00ff00")
    temp_project.add_fragment("Hijo", doc_name, fragment)
    main_window.current_project = temp_project
    main_window.current_doc = doc_name
    main_window.text_area.setPlainText("texto marcado")
    main_window.code_themes = []

    main_window.handle_edds_updated(temp_project.codes_dict, temp_project.themes_dict)
    assert len(main_window.highlighted) == 1
    assert main_window.highlighted[0]["color"] == "#00ff00"

    main_window._display_fragment_immediately(fragment, "#00ff00")
    assert len(main_window.highlighted) == 1


def test_fragment_delete_signal_updates_edd_and_current_highlights(main_window, temp_project):
    doc_name = "doc.txt"
    with open(temp_project.documents_path + "/" + doc_name, "w", encoding="utf-8") as handle:
        handle.write("texto marcado")
    temp_project.add_code("Codigo", "#ff0000")
    temp_project.add_fragment("Codigo", doc_name, {"type": "text", "start": 0, "end": 5})
    main_window.current_project = temp_project
    main_window.current_doc = doc_name
    main_window.text_area.setPlainText("texto marcado")
    main_window.signal_req_set_project.emit(temp_project)
    main_window.handle_edds_updated(temp_project.codes_dict, temp_project.themes_dict)

    main_window.signal_req_delete_fragment.emit("Codigo", doc_name, 0)

    assert doc_name not in temp_project.codes_dict["Codigo"]["fragments"]
    assert main_window.highlighted == []
