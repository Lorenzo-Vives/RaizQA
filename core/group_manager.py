import os
import platform
import subprocess
import logging
from typing import Dict, List
from core.constants import (TEXT_EXTENSIONS, IMAGE_EXTENSIONS) 

logger = logging.getLogger(__name__)

def get_file_extension(file_path: str) -> str:
    return os.path.splitext(file_path)[1].lower()

def hide_directory(path: str) -> str:
    """
    Oculta directorios según el sistema operativo.
    En Linux, renombra con punto al inicio.
    Retorna la ruta final (puede haber cambiado en Linux).
    """
    system = platform.system()
    try:
        if system == "Windows":
            import ctypes

            ctypes.windll.kernel32.SetFileAttributesW(path, 0x02)
        elif system == "Darwin":
            subprocess.run(["chflags", "hidden", path], check=False)
        elif system == "Linux":
            dir_path, dir_name = os.path.split(path)
            if not dir_name.startswith("."):
                new_path = os.path.join(dir_path, f".{dir_name}")
                os.rename(path, new_path)
                return new_path
    except Exception as e:
        logger.warning(f"No se pudo ocultar directorio {path}: {e}")
    return path

# ----------------------------------------------------------------------
# Gestor de Grupos de Documentos
# ----------------------------------------------------------------------
class GroupManager:
    """
    Administra la organización de documentos en grupos en el sistema de archivos.
    """
    def __init__(self):
        self.groups: Dict[str, List[str]] = {"__root__": []}

        if "__root__" not in self.groups:
            self.groups["__root__"] = []
    
    def add_group(self, name: str):
        if name not in self.groups:
            self.groups[name] = []

    def remove_group(self, name: str):
        if name == "__root__":
            return
        docs = self.groups.pop(name, [])
        self.groups.setdefault("__root__", []).extend(docs)

    def add_document_to_group(self, doc_name: str, group_name: str):
        self._remove_document_from_all_groups_internal(doc_name)
        self.groups.setdefault(group_name, []).append(doc_name)

    def remove_document_from_group(self, doc_name: str, group_name: str):
        if group_name in self.groups and doc_name in self.groups[group_name]:
            self.groups[group_name].remove(doc_name)
            self.groups.setdefault("__root__", []).append(doc_name)

    def _remove_document_from_all_groups_internal(self, doc_name: str):
        """
        Quita el documento de cualquier grupo sin reinsertarlo en __root__
        """
        for group_name, docs in self.groups.items():
            if doc_name in docs:
                docs.remove(doc_name)
                break

    def remove_document_from_all_groups(self, doc_name: str):
        for group_name, docs in self.groups.items():
            if doc_name in docs:
                docs.remove(doc_name)
                if group_name != "__root__":
                    self.groups.setdefault("__root__", []).append(doc_name)
                break

    def clean_existing_pointers(self, documents_path: str):        
        with os.scandir(documents_path) as entries:
            for entry in entries:

                if not entry.is_dir():
                    continue
                    
                # 1. Eliminar archivos .raizptr
                with os.scandir(entry.path) as sub_entries:
                    for sub_entry in sub_entries:
                        if sub_entry.name.endswith(".raizptr") and sub_entry.is_file():
                            os.remove(sub_entry.path)
                
                # Eliminar directorio si está vacío y no pertenece a groups
                if entry.name not in self.groups: 
                    try:
                        os.rmdir(entry.path) 
                    except OSError as e:
                        print(f"Error al eliminar el directorio: {e}")
                        pass

    def create_groups_and_pointers(self, documents_path: str):
        
        for group_name, docs in self.groups.items():
            if group_name == "__root__":
                continue
            group_dir = os.path.join(documents_path, group_name)
            os.makedirs(group_dir, exist_ok=True)
            group_dir = hide_directory(group_dir)
            for doc in docs:
                ptr_path = os.path.join(group_dir, f"{doc}.raizptr")
                with open(ptr_path, "w", encoding="utf-8") as f:
                    f.write(f"target=../{doc}")
                    
    
    def scan_from_filesystem(self, documents_path: str) -> dict:
        groups = {"__root__": []}
        if not os.path.exists(documents_path):
            return groups

        for item in os.listdir(documents_path):
            item_path = os.path.join(documents_path, item)
            if os.path.isfile(item_path):
                ext = get_file_extension(item)
                if ext in TEXT_EXTENSIONS or ext in IMAGE_EXTENSIONS:
                    groups["__root__"].append(item)
            elif os.path.isdir(item_path):
                groups[item] = []
                for sub in os.listdir(item_path):
                    if sub.endswith(".raizptr"):
                        groups[item].append(sub[:-8])

        docs_in_groups = {
            d for g, docs in groups.items() if g != "__root__" for d in docs
        }
        groups["__root__"] = [d for d in groups["__root__"] if d not in docs_in_groups]
        return groups