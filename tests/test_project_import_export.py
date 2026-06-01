import os
import zipfile
import pytest
import tempfile
import json
from pathlib import Path

from core.export_manager import ExportManager
from core.import_manager import ImportManager

def test_export_project_to_rqa(tmp_path):
    """Prueba que un directorio de proyecto se empaquete correctamente en formato .rqa."""
    # 1. Crear un proyecto simulado
    project_name = "DummyProject"
    project_dir = tmp_path / project_name
    project_dir.mkdir()
    
    (project_dir / "documentos").mkdir()
    (project_dir / "codigos").mkdir()
    
    # Archivos simulados
    metadata_path = project_dir / "metadata.json"
    metadata_path.write_text(json.dumps({"name": project_name}), encoding="utf-8")
    
    (project_dir / "documentos" / "doc1.txt").write_text("contenido", encoding="utf-8")
    
    # 2. Exportar
    export_path = tmp_path / "exportado.rqa"
    result_path = ExportManager.export_project_to_rqa(str(project_dir), str(export_path))
    
    # 3. Validar
    assert os.path.exists(result_path)
    assert zipfile.is_zipfile(result_path)
    
    # Comprobar el contenido del zip
    with zipfile.ZipFile(result_path, 'r') as zf:
        namelist = zf.namelist()
        # En Windows o Linux los paths dentro del zip usan forward slash
        assert any(n.endswith("metadata.json") for n in namelist)
        assert any("documentos/doc1.txt" in n or "documentos\\doc1.txt" in n for n in namelist)

def test_import_project_from_rqa(tmp_path):
    """Prueba que un archivo .rqa válido se extraiga correctamente en el directorio destino."""
    # 1. Crear el .rqa simulado manualmente
    project_name = "ImportMe"
    rqa_path = tmp_path / "valido.rqa"
    
    with zipfile.ZipFile(str(rqa_path), 'w') as zf:
        zf.writestr("metadata.json", json.dumps({"name": project_name}))
        zf.writestr("documentos/doc_import.txt", "Texto de importación")
        
    dest_base_path = tmp_path / "workdir"
    dest_base_path.mkdir()
    
    # 2. Importar
    imported_proj_path = ImportManager.import_project_from_rqa(str(rqa_path), str(dest_base_path))
    
    # 3. Validar
    assert os.path.exists(imported_proj_path)
    assert os.path.basename(imported_proj_path) == project_name
    assert os.path.exists(os.path.join(imported_proj_path, "metadata.json"))
    assert os.path.exists(os.path.join(imported_proj_path, "documentos", "doc_import.txt"))

def test_import_missing_file(tmp_path):
    """Prueba que se lance FileNotFoundError si el archivo no existe."""
    with pytest.raises(FileNotFoundError):
        ImportManager.import_project_from_rqa(str(tmp_path / "no_existe.rqa"), str(tmp_path))

def test_import_invalid_zip(tmp_path):
    """Prueba que se lance ValueError si el archivo no es un zip válido."""
    invalid_rqa = tmp_path / "invalido.rqa"
    invalid_rqa.write_text("Esto no es un zip")
    
    with pytest.raises(ValueError, match="no es un formato válido"):
        ImportManager.import_project_from_rqa(str(invalid_rqa), str(tmp_path))

def test_import_missing_metadata(tmp_path):
    """Prueba que se lance ValueError si el zip no contiene metadata.json."""
    rqa_path = tmp_path / "sin_metadata.rqa"
    with zipfile.ZipFile(str(rqa_path), 'w') as zf:
        zf.writestr("documentos/dummy.txt", "texto")
        
    with pytest.raises(ValueError, match="no contiene 'metadata.json'"):
        ImportManager.import_project_from_rqa(str(rqa_path), str(tmp_path))
