import os
import pytest
from docx import Document

def test_import_txt(temp_project, tmp_path):
    """Prueba importar un archivo TXT."""
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Contenido de prueba TXT", encoding="utf-8")
    
    filename, text = temp_project.import_document(str(txt_file))
    
    assert filename == "test.txt"
    assert "Contenido de prueba TXT" in text
    # EXPECTATIVA OBJETIVA: Tras importar, el documento debe estar disponible en la memoria del proyecto
    assert filename in temp_project.texts_dict
    assert temp_project.texts_dict[filename] == text

def test_import_docx(temp_project, tmp_path):
    """Prueba importar un archivo DOCX."""
    docx_file = tmp_path / "test.docx"
    doc = Document()
    doc.add_paragraph("Contenido de prueba DOCX")
    doc.save(str(docx_file))
    
    filename, text = temp_project.import_document(str(docx_file))
    
    # EXPECTATIVA OBJETIVA: El nombre del archivo debe conservar su extensión o reflejar el archivo original.
    assert filename == "test.docx"
    assert "Contenido de prueba DOCX" in text
    assert filename in temp_project.texts_dict

def test_import_unsupported_format(temp_project, tmp_path):
    """Prueba importar un formato no soportado (ej. .xyz)."""
    unsupported_file = tmp_path / "test.xyz"
    unsupported_file.write_text("dummy")
    
    with pytest.raises(ValueError, match="Solo se admiten archivos"):
        temp_project.import_document(str(unsupported_file))

def test_import_missing_file(temp_project, tmp_path):
    """Prueba importar un archivo que no existe."""
    missing_file = tmp_path / "no_existe.txt"
    
    with pytest.raises(Exception):
        temp_project.import_document(str(missing_file))
