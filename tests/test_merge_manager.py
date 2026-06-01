import os
import json
import pytest
from core.project import Project
from core.merge_manager import MergeManager
from core.export_manager import ExportManager

def create_mock_project(base_path, name):
    proj_dir = base_path / name
    proj_dir.mkdir(parents=True, exist_ok=True)
    proj = Project(name, str(base_path))
    # mock doc
    doc_name = "doc1.txt"
    doc_path = os.path.join(proj.documents_path, doc_name)
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write("Texto común")
    proj._register_document(doc_name)
    proj.texts_dict[doc_name] = "Texto común"
    return proj

def test_merge_documents_rule(tmp_path):
    """
    Regla: Si el documento tiene el mismo nombre, no se duplica.
    Si el documento no existe, se añade.
    """
    proj1 = create_mock_project(tmp_path, "Proj1")
    proj2 = create_mock_project(tmp_path, "Proj2")
    
    # Añadir doc exclusivo a proj2
    doc2_name = "doc2.txt"
    doc2_path = os.path.join(proj2.documents_path, doc2_name)
    with open(doc2_path, 'w', encoding='utf-8') as f:
        f.write("Texto extra")
    proj2._register_document(doc2_name)
    proj2.texts_dict[doc2_name] = "Texto extra"
    
    proj1.save_project_data(list(proj1.texts_dict.keys()), [])
    proj2.save_project_data(list(proj2.texts_dict.keys()), [])
    
    # Merge proj2 into proj1 via RQA
    rqa_path = str(tmp_path / "proj2.rqa")
    ExportManager.export_project_to_rqa(str(tmp_path / "Proj2"), rqa_path)
    MergeManager.merge_projects(proj1, rqa_path, {"merge_docs": True, "merge_codes": True, "merge_themes": True, "merge_memos": True})
    
    # EXPECTATIVA OBJETIVA:
    # 1. doc1.txt no debe estar duplicado (e.g. no doc1_1.txt)
    docs = proj1.list_documents()
    assert len(docs) == 2
    assert "doc1.txt" in docs
    assert "doc2.txt" in docs
    
    # Y el archivo fisico debe existir
    assert os.path.exists(os.path.join(proj1.documents_path, "doc2.txt"))

def test_merge_codes_rule(tmp_path):
    """
    Regla: Códigos con el mismo nombre se fusionan (merge).
    """
    proj1 = create_mock_project(tmp_path, "Proj1")
    proj1.add_code("Comun", "#ff0000", "Memo 1")
    
    proj2 = create_mock_project(tmp_path, "Proj2")
    proj2.add_code("Comun", "#00ff00", "Memo 2")
    proj2.add_code("Nuevo", "#0000ff", "Memo 3")
    
    proj1.save_project_data([], list(proj1.codes_dict.keys()))
    proj2.save_project_data([], list(proj2.codes_dict.keys()))
    
    rqa_path = str(tmp_path / "proj2_codes.rqa")
    ExportManager.export_project_to_rqa(str(tmp_path / "Proj2"), rqa_path)
    MergeManager.merge_projects(proj1, rqa_path, {"merge_docs": True, "merge_codes": True, "merge_themes": True, "merge_memos": True})
    
    # EXPECTATIVA OBJETIVA:
    # 1. "Comun" no se duplica
    assert "Comun" in proj1.codes_dict
    assert "Nuevo" in proj1.codes_dict
    
    # 2. Conserva atributos de proj1 en caso de conflicto, o los concatena
    assert proj1.codes_dict["Comun"]["hexcolor"] == "#ff0000"

def test_merge_fragments_rule(tmp_path):
    """
    Regla: Las codificaciones (fragmentos) del proyecto 2 se añaden al 1.
    Si son codificaciones idénticas (mismo inicio, fin, doc y código), no se duplican.
    """
    proj1 = create_mock_project(tmp_path, "Proj1")
    proj1.add_code("Test", "#ff0000", "")
    proj1.add_fragment("Test", "doc1.txt", {"start": 0, "end": 5, "text": "Texto", "doc": "doc1.txt"})
    
    proj2 = create_mock_project(tmp_path, "Proj2")
    proj2.add_code("Test", "#ff0000", "")
    # Fragmento idéntico
    proj2.add_fragment("Test", "doc1.txt", {"start": 0, "end": 5, "text": "Texto", "doc": "doc1.txt"})
    # Fragmento nuevo
    proj2.add_fragment("Test", "doc1.txt", {"start": 6, "end": 11, "text": "común", "doc": "doc1.txt"})
    
    proj1.save_project_data(list(proj1.texts_dict.keys()), list(proj1.codes_dict.keys()))
    proj2.save_project_data(list(proj2.texts_dict.keys()), list(proj2.codes_dict.keys()))
    
    rqa_path = str(tmp_path / "proj2_frags.rqa")
    ExportManager.export_project_to_rqa(str(tmp_path / "Proj2"), rqa_path)
    MergeManager.merge_projects(proj1, rqa_path, {"merge_docs": True, "merge_codes": True, "merge_themes": True, "merge_memos": True})
    
    fragments = proj1.codes_dict["Test"]["fragments"]["doc1.txt"]
    # EXPECTATIVA OBJETIVA: Debe haber exactamente 2 fragmentos (el idéntico no se duplica)
    assert len(fragments) == 2
    
    starts = [f["start"] for f in fragments]
    assert 0 in starts
    assert 6 in starts

def test_merge_themes_rule(tmp_path):
    """
    Regla: Temas con mismo nombre se fusionan, combinando los códigos que contienen
    sin duplicar el tema.
    """
    proj1 = create_mock_project(tmp_path, "Proj1")
    proj1.add_code_to_theme("Tema 1", "Cod A")
    
    proj2 = create_mock_project(tmp_path, "Proj2")
    proj2.add_code_to_theme("Tema 1", "Cod B")
    proj2.add_code_to_theme("Tema 2", "Cod C")
    
    proj1.save_project_data([], [])
    proj2.save_project_data([], [])
    
    rqa_path = str(tmp_path / "proj2_themes.rqa")
    ExportManager.export_project_to_rqa(str(tmp_path / "Proj2"), rqa_path)
    MergeManager.merge_projects(proj1, rqa_path, {"merge_docs": True, "merge_codes": True, "merge_themes": True, "merge_memos": True})
    
    # EXPECTATIVA OBJETIVA:
    assert "Tema 1" in proj1.themes_dict
    assert "Tema 2" in proj1.themes_dict
    
    tema1_codes = proj1.themes_dict["Tema 1"]["codes"]
    assert "Cod A" in tema1_codes
    assert "Cod B" in tema1_codes
