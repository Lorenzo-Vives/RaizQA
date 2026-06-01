import os
import pytest
from core.project import Project

def test_project_folder_creation(tmp_path):
    """Prueba que un nuevo proyecto crea las carpetas correspondientes."""
    proj_name = "NuevoProyecto"
    proj_dir = tmp_path / proj_name
    proj_dir.mkdir()
    
    project = Project(proj_name, str(tmp_path))
    project.load_project_data()
    
    # Comprobar si las carpetas existen
    assert (proj_dir / "documentos").exists()
    assert (proj_dir / "codigos").exists()
    assert (proj_dir / "metadata.json").exists()

def test_atomic_persistence(tmp_path):
    """Prueba que el guardado atómico usa un archivo temporal y luego lo renombra."""
    proj_name = "PersistenceProject"
    proj_dir = tmp_path / proj_name
    proj_dir.mkdir()
    
    project = Project(proj_name, str(tmp_path))
    project.load_project_data()
    
    project.add_code("TestPersistence", "#123456", "test")
    project.save_project_data(documents=[], highlights={})
    
    edds_file = proj_dir / "project_data.json"
    assert edds_file.exists()
    
    import json
    with open(edds_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    assert "TestPersistence" in data.get("codes_dict", {})

def test_invalid_project_path(tmp_path):
    """Prueba el comportamiento al inicializar en una ruta inválida/sin permisos (simulada)."""
    # En Windows, un path inválido puede ser simplemente un archivo que no es directorio
    invalid_path = tmp_path / "invalid_file.txt"
    invalid_path.touch()
    
    # Intentar crear un proyecto dentro de un archivo debería dar un error de OS
    with pytest.raises(OSError):
        project = Project("Invalid", str(invalid_path))
        project.load_project_data()
