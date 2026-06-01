import pytest
from core.project import Project
import os

def test_update_document_text(temp_project):
    """Prueba que el texto de un documento se pueda actualizar y guarde."""
    # 1. Crear documento virtual y en disco
    doc_name = "test_doc.txt"
    doc_path = os.path.join(temp_project.documents_path, doc_name)
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write("Texto original")
        
    temp_project.texts_dict[doc_name] = "Texto original"
    
    # 2. Actualizar el documento
    nuevo_texto = "Texto modificado"
    temp_project.update_document_text(doc_name, nuevo_texto)
    
    # 3. EXPECTATIVA OBJETIVA: La EDD en memoria debe estar sincronizada.
    assert temp_project.texts_dict[doc_name] == nuevo_texto
    
    # 4. Comprobar que en disco cambió
    with open(doc_path, 'r', encoding='utf-8') as f:
        texto_en_disco = f.read()
    assert texto_en_disco == nuevo_texto

def test_delete_purges_fragments(temp_project):
    """EXPECTATIVA OBJETIVA: Eliminar un documento del proyecto debe purgar 
    automáticamente los fragmentos asociados a ese documento en todos los códigos
    para evitar inconsistencias o 'fragmentos fantasma'."""
    doc_name = "borrar_con_fragmentos.txt"
    doc_path = os.path.join(temp_project.documents_path, doc_name)
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write("Texto de prueba")
    temp_project._register_document(doc_name)
    temp_project.texts_dict[doc_name] = "Texto de prueba"
    
    # Agregar un código y un fragmento
    temp_project.add_code("CodigoPrueba", "#00ff00", "")
    temp_project.add_fragment("CodigoPrueba", doc_name, {
        "text": "Texto", "start": 0, "end": 5, "doc": doc_name
    })
    
    # Eliminar el documento
    temp_project.delete_document(doc_name)
    
    # Verificar que los fragmentos de ese documento fueron purgados
    fragments = temp_project.codes_dict.get("CodigoPrueba", {}).get("fragments", {})
    assert doc_name not in fragments or len(fragments[doc_name]) == 0

def test_delete_document(temp_project):
    """Prueba que el documento se elimine del disco y metadatos."""
    doc_name = "borrar.txt"
    doc_path = os.path.join(temp_project.documents_path, doc_name)
    with open(doc_path, 'w') as f:
        f.write("test")
    
    # Simular que está registrado
    temp_project._register_document(doc_name)
    assert os.path.exists(doc_path)
    
    # Eliminar
    temp_project.delete_document(doc_name)
    
    # Comprobar que no existe
    assert not os.path.exists(doc_path)
