from pathlib import Path
import copy
import os
import json


def hydrate_codes_dict(codes_dict, project):
    """Return a detached copy of the code EDD with valid text snippets filled in.

    Image fragments and text fragments with invalid coordinates are left untouched.
    The project EDD is never mutated.
    """
    hydrated = copy.deepcopy(codes_dict or {})
    if project is None:
        return hydrated

    for code_data in hydrated.values():
        for doc_name, fragments in code_data.get("fragments", {}).items():
            try:
                document_text = project.get_document_text(doc_name)
            except Exception:
                continue
            if not isinstance(document_text, str):
                continue

            for fragment in fragments:
                if not isinstance(fragment, dict) or fragment.get("type", "text") == "image":
                    continue
                start = fragment.get("start")
                end = fragment.get("end")
                if (
                    not isinstance(start, int)
                    or isinstance(start, bool)
                    or not isinstance(end, int)
                    or isinstance(end, bool)
                    or start < 0
                    or end < start
                    or end > len(document_text)
                ):
                    continue
                fragment["text"] = document_text[start:end]

    return hydrated

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
