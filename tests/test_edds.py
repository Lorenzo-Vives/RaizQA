import pytest
from core.project import Project

def test_initial_edds(temp_project):
    """Prueba que los diccionarios EDD inicialicen correctamente."""
    assert isinstance(temp_project.codes_dict, dict)
    assert isinstance(temp_project.themes_dict, dict)
    assert isinstance(temp_project.texts_dict, dict)
    assert len(temp_project.codes_dict) == 0
    assert len(temp_project.themes_dict) == 0

def test_add_code_updates_edd(temp_project):
    """Añadir un código debe actualizar el EDD."""
    temp_project.add_code("MiCodigo", "#ff0000", "Memo de prueba")
    
    assert "MiCodigo" in temp_project.codes_dict
    assert temp_project.codes_dict["MiCodigo"]["hexcolor"] == "#ff0000"
    assert temp_project.codes_dict["MiCodigo"]["memo"] == "Memo de prueba"
    assert temp_project.codes_dict["MiCodigo"]["fragments"] == {}

def test_update_code_renames_in_edd(temp_project):
    """Renombrar un código debe cambiar la llave en el EDD."""
    temp_project.add_code("Viejo", "#000000", "")
    temp_project.update_code("Viejo", "Nuevo", "#ffffff", "Memo nuevo")
    
    assert "Viejo" not in temp_project.codes_dict
    assert "Nuevo" in temp_project.codes_dict
    assert temp_project.codes_dict["Nuevo"]["hexcolor"] == "#ffffff"
    assert temp_project.codes_dict["Nuevo"]["memo"] == "Memo nuevo"

def test_delete_code_removes_from_edd(temp_project):
    """Eliminar un código debe quitarlo del EDD."""
    temp_project.add_code("Eliminar", "#000000", "")
    temp_project.delete_code("Eliminar")
    
    assert "Eliminar" not in temp_project.codes_dict

def test_add_fragment_updates_edd(temp_project):
    """Añadir un fragmento debe registrarlo bajo el código en el EDD."""
    temp_project.add_code("Codigo1", "#000000", "")
    
    # Creamos un documento falso en el EDD de textos para que el validador no falle si existe.
    temp_project.texts_dict["doc1.txt"] = {"text": "Hola mundo este es un texto de prueba"}
    
    fragment_data = {
        "text": "Hola mundo",
        "start": 0,
        "end": 10,
        "date": "2026-05-31",
        "doc": "doc1.txt"
    }
    temp_project.add_fragment("Codigo1", "doc1.txt", fragment_data)
    
    fragments = temp_project.codes_dict["Codigo1"]["fragments"]
    assert "doc1.txt" in fragments
    assert len(fragments["doc1.txt"]) == 1
    assert fragments["doc1.txt"][0]["text"] == "Hola mundo"
    assert fragments["doc1.txt"][0]["start"] == 0

def test_add_duplicate_code(temp_project):
    """Añadir un código duplicado no debe sobreescribir si ya existe,
    o en su defecto el sistema lo ignora."""
    temp_project.add_code("Duplicado", "#111111", "Original")
    temp_project.add_code("Duplicado", "#222222", "Nuevo")
    
    # Si la logica no lo permite o simplemente ignora
    # Asumiendo que RaizQA conserva el primero o lo actualiza (veremos comportamiento)
    # Por lo normal, un diccionario sobreescribirá si la logica lo hace.
    # En Project.add_code, chequea if code_name not in self.codes_dict
    assert temp_project.codes_dict["Duplicado"]["hexcolor"] == "#111111"
    assert temp_project.codes_dict["Duplicado"]["memo"] == "Original"
