from pathlib import Path
import os
import json

def get_memos_dir(project):
    """Devuelve la ruta al directorio de memos del proyecto (como objeto Path)."""
    memos_dir = Path(project.path) / "memos"
    memos_dir.mkdir(exist_ok=True)
    return memos_dir

def load_memos(project):
    """Carga todos los memos guardados en disco como un diccionario {codigo: texto}"""
    memos_dir = get_memos_dir(project)
    memos = {}
    if memos_dir.exists():
        for file_path in memos_dir.glob("*.txt"):
            code_name = file_path.stem  # nombre sin extensión
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    memos[code_name] = f.read()
            except Exception as e:
                print(f"ADVERTENCIA No se pudo cargar memo {file_path.name}: {e}")
    return memos
