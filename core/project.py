import os
import json
import shutil
import platform
import subprocess
import time
import logging
import copy
import functools
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from docx import Document as DocxDocument

import pymupdf

from diff_match_patch import diff_match_patch

from core.memos import MemoManager
from core.diary_manager import DiaryManager

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Constantes y Utilidades
# ----------------------------------------------------------------------
TEXT_EXTENSIONS = {".txt", ".docx", ".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff"}
ALLOWED_EXTENSIONS = tuple(TEXT_EXTENSIONS | IMAGE_EXTENSIONS)


def get_file_extension(file_path: str) -> str:
    return os.path.splitext(file_path)[1].lower()


def get_file_name(file_path: str) -> str:
    basename = os.path.basename(file_path)
    return os.path.splitext(basename)[0]


def file_extension_allowed(file_path: str) -> bool:
    return get_file_extension(file_path) in ALLOWED_EXTENSIONS


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
# Modelos de Dominio (Dataclasses)
# ----------------------------------------------------------------------
@dataclass(slots=True)
class Fragment:
    """
    Representar una porción de texto seleccionada dentro de un documento.
    """
    start: int
    end: int
    type: str = "text"

    def to_dict(self) -> dict:
        return {"start": self.start, "end": self.end, "type": self.type}

    
    @classmethod
    def from_dict(cls, data) -> "Fragment":
        # Formato lista/tupla legacy: [0, 10] o (0, 10)
        if isinstance(data, list) and len(data) >= 2:
            return cls(start=int(data[0]), end=int(data[1]), type="text")
        
        # Formato dict (actual o legacy con claves abreviadas)
        if isinstance(data, dict):
            start = data.get("start", 0)
            end = data.get("end", 0)
            frag_type = data.get("type", "text")
            return cls(start=int(start), end=int(end), type=frag_type)
        
        # Fallback: valores por defecto si el formato es desconocido
        logger.warning(f"Formato de fragmento desconocido: {type(data)} - {data}")
        return cls(start=0, end=0, type="text")


@dataclass(slots=True)
class Code:
    """
    Modelar un código de análisis, su jerarquía y los fragmentos asociados.
    """

    hexcolor: str = "#5d9bd3"
    memo: str = ""
    fragments: Dict[str, List[Fragment]] = field(default_factory=dict)
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "hexcolor": self.hexcolor,
            "memo": self.memo,
            "fragments": {
                doc: [f.to_dict() for f in frags]
                for doc, frags in self.fragments.items()
            },
            "parent": self.parent,
            "children": list(self.children),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Code":
        fragments = {}
        for doc, frags in data.get("fragments", {}).items():
            fragments[doc] = [Fragment.from_dict(f) for f in frags]
        return cls(
            hexcolor=data.get("hexcolor", "#5d9bd3"),
            memo=data.get("memo", ""),
            fragments=fragments,
            parent=data.get("parent"),
            children=data.get("children", []),
        )


@dataclass(slots=True)
class Theme:
    """
    Modelar un tema que puede agrupar múltiples códigos.
    """
    memo: str = ""
    codes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"memo": self.memo, "codes": list(self.codes)}

    @classmethod
    def from_dict(cls, data: dict) -> "Theme":
        return cls(
            memo=data.get("memo", ""),
            codes=data.get("codes", []),
        )


# ----------------------------------------------------------------------
# Parseo de Documentos
# ----------------------------------------------------------------------
class DocumentParser:
    """
    Extraer texto plano desde archivos de formatos específicos.
    """
    @staticmethod
    def read_docx(file_path: str) -> str:
        doc = DocxDocument(file_path)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

    @staticmethod
    def read_pdf(file_path: str) -> str:
        try:
            with pymupdf.open(file_path) as doc:
                
                if not doc.is_encrypted:
                    return "\n".join(text for page in doc if (text := page.get_text().strip()))

        except FileNotFoundError:
            logger.error(f"El archivo no fue encontrado: {file_path}")
            return ""
    
        except pymupdf.FileDataError:
            logger.error(f"El archivo está corrupto o no es un PDF válido: {file_path}")
            return ""
        
        except PermissionError:
            logger.error(f"Sin permisos para leer el archivo: {file_path}")
            return ""
            
        except Exception as e:
            # Captura cualquier otro error inesperado (ej. problemas de memoria)
            logger.error(f"Error inesperado al leer {file_path}: {str(e)}")
            return ""

    @staticmethod
    def read_txt(file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as f:
                return f.read()


# ----------------------------------------------------------------------
# Gestor de Documentos
# ----------------------------------------------------------------------
class DocumentManager:
    """
    Administra el ciclo de vida completo de los documentos dentro de un
    proyecto: importación, lectura, escritura, eliminación y cacheo de textos.
    """

    TEXT_EXTENSIONS = TEXT_EXTENSIONS
    IMAGE_EXTENSIONS = IMAGE_EXTENSIONS

    def __init__(self, documents_path: str, metadata_path: str):
        self.documents_path = documents_path
        self.metadata_path = metadata_path
        self.documents: List[dict] = []
        self.text_cache: Dict[str, str] = {}

        os.makedirs(self.documents_path, exist_ok=True)
        self._init_metadata()

    def _init_metadata(self):
        if not os.path.exists(self.metadata_path):
            self._write_metadata({"documents": []})
        else:
            meta = self._read_metadata()
            self.documents = [{"name": d} for d in meta.get("documents", [])]

    def _read_metadata(self) -> dict:
        try:
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"documents": []}

    def _write_metadata(self, meta: dict):
        try:
            with open(self.metadata_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def _register_in_metadata(self, document_name: str):
        meta = self._read_metadata()
        if document_name not in meta.get("documents", []):
            meta.setdefault("documents", []).append(document_name)
            self._write_metadata(meta)
        if document_name not in [d.get("name") for d in self.documents]:
            self.documents.append({"name": document_name})

    def _remove_from_metadata(self, document_name: str):
        meta = self._read_metadata()
        docs = meta.get("documents", [])
        if document_name in docs:
            docs.remove(document_name)
            self._write_metadata(meta)
        self.documents = [d for d in self.documents if d.get("name") != document_name]

    def list_documents(self) -> List[str]:
        if not os.path.exists(self.documents_path):
            return []
        return sorted(
            f
            for f in os.listdir(self.documents_path)
            if f.lower().endswith(ALLOWED_EXTENSIONS)
        )

    def import_document(self, file_path: str) -> Tuple[str, str]:
        ext = get_file_extension(file_path)
        filename = get_file_name(file_path)
        dest_name = f"{filename}{ext if ext in self.IMAGE_EXTENSIONS else '.txt'}"
        dest_path = os.path.join(self.documents_path, dest_name)

        if ext in self.IMAGE_EXTENSIONS:
            shutil.copy2(file_path, dest_path)
            text = ""
        elif ext == ".docx":
            text = DocumentParser.read_docx(file_path)
        elif ext == ".pdf":
            text = DocumentParser.read_pdf(file_path)
        elif ext == ".txt":
            text = DocumentParser.read_txt(file_path)
        else:
            raise ValueError(
                "Solo se admiten archivos .txt, .docx, .pdf o imágenes "
                "(png, jpg, jpeg, bmp, gif, tiff)"
            )

        if ext in self.TEXT_EXTENSIONS:
            self.write_text(dest_name, text)

        self._register_in_metadata(dest_name)
        self.text_cache[dest_name] = text
        return dest_name, text

    def delete_document(self, doc_name: str):
        doc_path = self.get_document_path(doc_name)
        if os.path.exists(doc_path):
            try:
                os.remove(doc_path)
            except OSError:
                pass
        self.text_cache.pop(doc_name, None)
        self._remove_from_metadata(doc_name)

    def read_document(self, doc_name: str) -> str:
        doc_path = self.get_document_path(doc_name)
        if not os.path.exists(doc_path):
            return ""
        ext = get_file_extension(doc_name)
        if ext in self.IMAGE_EXTENSIONS:
            return ""
        return DocumentParser.read_txt(doc_path)

    def write_text(self, doc_name: str, text: str):
        path = self.get_document_path(doc_name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def get_document_text(self, doc_name: str) -> str:
        if doc_name not in self.text_cache:
            self.text_cache[doc_name] = self.read_document(doc_name)
        return self.text_cache[doc_name]

    def load_all_texts_to_memory(self):
        for doc_name in self.list_documents():
            self.get_document_text(doc_name)

    def get_document_path(self, doc_name: str) -> str:
        return os.path.join(self.documents_path, doc_name)

    def document_exists(self, doc_name: str) -> bool:
        return os.path.exists(self.get_document_path(doc_name))


# ----------------------------------------------------------------------
# Sincronizador de Fragmentos
# ----------------------------------------------------------------------
class FragmentSynchronizer:
    """
    Reubica los fragmentos de código cuando el texto de un documento ha sido editado.
    """
    def __init__(self, match_threshold: float = 0.3):
        self.match_threshold = match_threshold

    def sync_fragments(
        self, old_text: str, new_text: str, fragments: List[dict]
    ) -> List[dict]:
        dmp = diff_match_patch()
        dmp.Match_Threshold = self.match_threshold
        updated = []

        for frag in fragments:
            if (
                frag.get("type") != "text"
                or frag.get("start") is None
                or frag.get("end") is None
            ):
                updated.append(frag)
                continue

            start, end = frag["start"], frag["end"]
            frag_text = old_text[start:end]
            new_start = dmp.match_main(new_text, frag_text, start)

            if new_start != -1:
                frag["start"] = new_start
                frag["end"] = new_start + len(frag_text)
                updated.append(frag)
            else:
                logger.warning(
                    "Fragmento eliminado automáticamente por edición destructiva."
                )
        return updated


# ----------------------------------------------------------------------
# Gestor de Códigos
# ----------------------------------------------------------------------
class CodeManager:
    """
    Gestiona el conjunto de códigos, su jerarquía y la asignación de fragmentos.
    """
    def __init__(self, fragment_sync: Optional[FragmentSynchronizer] = None):
        self.codes_dict: Dict[str, Code] = {}
        self.fragment_sync = fragment_sync or FragmentSynchronizer()

    def add_code(
        self,
        code_name: str,
        hexcolor: str = "#5d9bd3",
        memo: str = "",
        parent_name: Optional[str] = None,
    ):
        if code_name in self.codes_dict:
            return
        if parent_name and parent_name not in self.codes_dict:
            parent_name = None

        self.codes_dict[code_name] = Code(
            hexcolor=hexcolor,
            memo=memo,
            parent=parent_name,
        )
        if parent_name:
            self.codes_dict[parent_name].children.append(code_name)

    def delete_code(self, code_name: str, cascade: bool = False) -> List[str]:
        if code_name not in self.codes_dict:
            return []
        deleted = [code_name]
        children = list(self.codes_dict[code_name].children)

        if cascade:
            for child in children:
                deleted.extend(self.delete_code(child, cascade=True))
        else:
            for child in children:
                if child in self.codes_dict:
                    self.codes_dict[child].parent = None

        parent = self.codes_dict[code_name].parent
        if (
            parent
            and parent in self.codes_dict
            and code_name in self.codes_dict[parent].children
        ):
            self.codes_dict[parent].children.remove(code_name)

        del self.codes_dict[code_name]
        return deleted

    def update_code(
        self,
        old_name: str,
        new_name: Optional[str] = None,
        hexcolor: Optional[str] = None,
        memo: Optional[str] = None,
    ):
        if old_name not in self.codes_dict:
            return
        target_name = old_name

        if new_name and new_name != old_name:
            self.codes_dict[new_name] = self.codes_dict.pop(old_name)
            target_name = new_name
            for child in self.codes_dict[new_name].children:
                if child in self.codes_dict:
                    self.codes_dict[child].parent = new_name
            parent = self.codes_dict[new_name].parent
            if parent and parent in self.codes_dict:
                pc = self.codes_dict[parent].children
                for i, name in enumerate(pc):
                    if name == old_name:
                        pc[i] = new_name

        if hexcolor is not None:
            self.codes_dict[target_name].hexcolor = hexcolor
        if memo is not None:
            self.codes_dict[target_name].memo = memo

    def add_fragment(self, code_name: str, doc_name: str, fragment_data: dict):
        if code_name not in self.codes_dict:
            self.add_code(code_name)
        frag = Fragment(
            start=fragment_data["start"],
            end=fragment_data["end"],
            type=fragment_data.get("type", "text"),
        )
        self.codes_dict[code_name].fragments.setdefault(doc_name, []).append(frag)

    def remove_fragments_for_document(self, doc_name: str):
        for code in self.codes_dict.values():
            code.fragments.pop(doc_name, None)

    def get_fragments_for_code(
        self, code_name: str, get_text_fn: Callable[[str], str]
    ) -> List[dict]:
        if code_name not in self.codes_dict:
            return []
        results = []
        for doc_name, fragments in self.codes_dict[code_name].fragments.items():
            full_text = get_text_fn(doc_name)
            for frag in fragments:
                results.append(
                    {
                        "doc": doc_name,
                        "start": frag.start,
                        "end": frag.end,
                        "text": full_text[frag.start : frag.end],
                    }
                )
        return results

    def sync_fragments_for_document(self, doc_name: str, old_text: str, new_text: str):
        for code in self.codes_dict.values():
            fragments = code.fragments.get(doc_name, [])
            if not fragments:
                continue
            frag_dicts = [f.to_dict() for f in fragments]
            updated_dicts = self.fragment_sync.sync_fragments(
                old_text, new_text, frag_dicts
            )
            code.fragments[doc_name] = [Fragment.from_dict(f) for f in updated_dicts]

    def get_all_codes(self) -> Dict[str, dict]:
        """Retorna los códigos como dicts planos para serialización."""
        return {k: v.to_dict() for k, v in self.codes_dict.items()}

    def load_codes(self, codes_dict: Dict[str, dict]):
        self.codes_dict = {k: Code.from_dict(v) for k, v in codes_dict.items()}


# ----------------------------------------------------------------------
# Gestor de Temas
# ----------------------------------------------------------------------
class ThemeManager:
    """
    Gestiona el conjunto de temas y su relación con los códigos.
    """
    def __init__(self):
        self.themes_dict: Dict[str, Theme] = {}

    def add_theme(self, theme_name: str, memo: str = ""):
        if theme_name not in self.themes_dict:
            self.themes_dict[theme_name] = Theme(memo=memo)

    def delete_theme(self, theme_name: str):
        self.themes_dict.pop(theme_name, None)

    def add_code_to_theme(self, theme_name: str, code_name: str):
        self.add_theme(theme_name)
        if code_name not in self.themes_dict[theme_name].codes:
            self.themes_dict[theme_name].codes.append(code_name)

    def remove_code_from_theme(self, theme_name: str, code_name: str):
        if (
            theme_name in self.themes_dict
            and code_name in self.themes_dict[theme_name].codes
        ):
            self.themes_dict[theme_name].codes.remove(code_name)

    def remove_code_from_all_themes(self, code_name: str):
        for theme in self.themes_dict.values():
            if code_name in theme.codes:
                theme.codes.remove(code_name)

    def rename_code_in_themes(self, old_name: str, new_name: str):
        for theme in self.themes_dict.values():
            for i, name in enumerate(theme.codes):
                if name == old_name:
                    theme.codes[i] = new_name

    def get_all_themes(self) -> Dict[str, dict]:
        return {k: v.to_dict() for k, v in self.themes_dict.items()}

    def load_themes(self, themes_dict: Dict[str, dict]):
        self.themes_dict = {k: Theme.from_dict(v) for k, v in themes_dict.items()}


# ----------------------------------------------------------------------
# Gestor de Grupos de Documentos
# ----------------------------------------------------------------------
class GroupManager:
    """
    Administra la organización lógica de documentos en grupos mediante
    directorios y punteros en el sistema de archivos.
    """
    def __init__(self):
        self._groups: Dict[str, List[str]] = {"__root__": []}

    @property
    def groups(self) -> dict:
        return copy.deepcopy(self._groups)             

    @groups.setter
    def groups(self, new_groups: Dict[str, List[str]]):
        self._groups = copy.deepcopy(new_groups)
        
        if "__root__" not in self._groups:
            self._groups["__root__"] = []
    
    def add_group(self, name: str):
        if name not in self.groups:
            self.groups[name] = []

    def remove_group(self, name: str):
        if name == "__root__":
            return
        docs = self.groups.pop(name, [])
        self.groups.setdefault("__root__", []).extend(docs)

    def add_document_to_group(self, doc_name: str, group_name: str):
        self.remove_document_from_all_groups(doc_name)
        self.groups.setdefault(group_name, []).append(doc_name)

    def remove_document_from_group(self, doc_name: str, group_name: str):
        if group_name in self.groups and doc_name in self.groups[group_name]:
            self.groups[group_name].remove(doc_name)
            self.groups.setdefault("__root__", []).append(doc_name)

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
            hide_directory(group_dir)
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


# ----------------------------------------------------------------------
# Gestor de Anotaciones
# ----------------------------------------------------------------------
class AnnotationManager:
    def __init__(self):
        self.highlights: dict = {}

    def load_highlights(self, highlights: dict):
        self.highlights = highlights

    def get_highlights(self) -> dict:
        return self.highlights


# ----------------------------------------------------------------------
# Persistencia
# ----------------------------------------------------------------------
class StorageManager:
    """
    Administra la persistencia atómica de datos del estado del proyecto,
    considerando respaldos (.bak).
    """

    def __init__(self, state_filename: str = "project_data.json"):
        self.state_filename = state_filename
        
    def save(self, project_path: str, state: dict):
        """
        Escribe el estado en un archivo temporal, 
        respalda el archivo actual como .bak y reemplaza
        el archivo principal usando os.replace
        """
        state_path = os.path.join(project_path, self.state_filename)
        bak_path = state_path + ".bak"
        
        tmp_path = os.path.join(
            project_path, f"{self.state_filename}.{os.getpid()}.{time.time_ns()}.tmp"
        )

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4, ensure_ascii=False)

            if os.path.exists(state_path):
                shutil.copy2(state_path, bak_path)

            os.replace(tmp_path, state_path)
            return True

        except OSError as e:
            logger.error(f"Error al guardar el estado del proyecto en {state_path}: {e}")
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            return False

            
            
    def load(self, project_path: str) -> dict:
        """
        Carga el estado persistido. Si el archivo principal no existe
        o está corrupto, intenta recuperarlo desde el respaldo (.bak).
        Si ambos fallan, retorna un estado vacío.
        """
        state_path = os.path.join(project_path, self.state_filename)
        bak_path = state_path + ".bak"

        for path in (state_path, bak_path):
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"No se pudo leer {path}: {e}")
                continue
            
        return {}




# ----------------------------------------------------------------------
# Fachada Principal
# ----------------------------------------------------------------------

def autosave(method):
    """
    Automatiza la persistencia del estado.
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        # Ejecutamos el método original y guardamos su resultado
        resultado = method(self, *args, **kwargs)
        
        # Ejecutamos el guardado de estado usando el mismo 'self'
        self.save_state()
        
        # Retornamos el resultado original para no romper el flujo
        return resultado
    return wrapper

class Project:
    """
    Orquesta todos los gestores especializados y 
    expone la API unificada del backend.
    """
    def __init__(
        self,
        name: str,
        base_path: str,
        doc_manager: Optional[DocumentManager] = None,
        code_manager: Optional[CodeManager] = None,
        theme_manager: Optional[ThemeManager] = None,
        group_manager: Optional[GroupManager] = None,
        annotation_manager: Optional[AnnotationManager] = None,
        storage: Optional[StorageManager] = None,
        memo_manager: Optional[MemoManager] = None,
        diary_manager: Optional[DiaryManager] = None,
    ):
        self.name = name
        self.base_path = base_path
        self.path = os.path.join(base_path, name)

        # Dependencias inyectables (con valores por defecto)
        self.doc_manager = doc_manager or DocumentManager(
            documents_path=os.path.join(self.path, "documentos"),
            metadata_path=os.path.join(self.path, "metadata.json"),
        )
        self.code_manager = code_manager or CodeManager()
        self.theme_manager = theme_manager or ThemeManager()
        self.group_manager = group_manager or GroupManager()
        self.annotation_manager = annotation_manager or AnnotationManager()
        self.storage = storage or StorageManager()
        self.memo_manager = memo_manager or MemoManager({})
        self.diary_manager = diary_manager or DiaryManager(self.path)

        self._ensure_structure()
        self._load_state()
        

    def _ensure_structure(self):
        """
        Nos aseguramos de que esten los directorios necesarios creados
        """
        os.makedirs(self.path, exist_ok=True)

    def _load_state(self):

        data = self.storage.load(self.path)

        self.annotation_manager.load_highlights(data.get("highlights", {}))
        self.code_manager.load_codes(data.get("codes_dict", {}))
        self.theme_manager.load_themes(data.get("themes_dict", {}))

        # Migración de memos antiguos
        memos = data.get("memos_dict", {})
        if not memos:
            old_memos_path = os.path.join(self.path, "memos.json")
            if os.path.exists(old_memos_path):
                try:
                    with open(old_memos_path, "r", encoding="utf-8") as f:
                        memos = json.load(f)
                except Exception:
                    pass
        self.memo_manager.memos = memos

        # Grupos de documentos
        doc_groups = data.get("doc_groups")
        if doc_groups:
            self.group_manager.groups = doc_groups
        else:
            fs_groups = self.group_manager.scan_from_filesystem(
                self.doc_manager.documents_path
            )
            if fs_groups and (
                len(fs_groups.get("__root__", [])) > 0 or len(fs_groups) > 1
            ):
                self.group_manager.groups = fs_groups

        # Asegurar estructura de árbol en códigos cargados
        for code in self.code_manager.codes_dict.values():
            if (
                code.parent is not None
                and code.parent not in self.code_manager.codes_dict
            ):
                code.parent = None

    def save_state(self):
        state = {
            "documents": self.doc_manager.documents,
            "highlights": self.annotation_manager.get_highlights(),
            "codes_dict": self.code_manager.get_all_codes(),
            "themes_dict": self.theme_manager.get_all_themes(),
            "memos_dict": self.memo_manager.memos,
            "doc_groups": self.group_manager.groups,
        }
        self.storage.save(self.path, state)
        documents_path = self.doc_manager.documents_path
        self.group_manager.clean_existing_pointers(documents_path)
        self.group_manager.create_groups_and_pointers(documents_path)

    @autosave
    def import_document(self, file_path: str) -> Tuple[str, str]:
        doc_name, text = self.doc_manager.import_document(file_path)
        return doc_name, text

    @autosave
    def delete_document(self, doc_name: str):
        self.doc_manager.delete_document(doc_name)
        self.code_manager.remove_fragments_for_document(doc_name)
        self.group_manager.remove_document_from_all_groups(doc_name)

    @autosave
    def update_document_text(self, doc_name: str, new_text: str):
        old_text = self.doc_manager.get_document_text(doc_name)
        self.doc_manager.write_text(doc_name, new_text)
        self.doc_manager.text_cache[doc_name] = new_text
        self.code_manager.sync_fragments_for_document(doc_name, old_text, new_text)

    @autosave
    def delete_code(self, code_name: str, cascade: bool = False):
        deleted = self.code_manager.delete_code(code_name, cascade)
        for name in deleted:
            self.theme_manager.remove_code_from_all_themes(name)
            self.memo_manager.delete_memo(name)

    def get_fragments_for_code(self, code_name: str) -> List[dict]:
        return self.code_manager.get_fragments_for_code(
            code_name, self.doc_manager.get_document_text
        )

    # ------------------------------------------------------------------
    # Delegación: Documentos
    # ------------------------------------------------------------------
    def list_documents(self) -> List[str]:
        return self.doc_manager.list_documents()

    def get_document_path(self, doc_name: str) -> str:
        return self.doc_manager.get_document_path(doc_name)

    def read_document(self, doc_name: str) -> str:
        return self.doc_manager.read_document(doc_name)

    def get_document_text(self, doc_name: str) -> str:
        return self.doc_manager.get_document_text(doc_name)

    def load_all_texts_to_memory(self):
        self.doc_manager.load_all_texts_to_memory()

    # ------------------------------------------------------------------
    # Delegación: Códigos
    # ------------------------------------------------------------------
    @autosave
    def add_code(
        self,
        code_name: str,
        hexcolor: str = "#5d9bd3",
        memo: str = "",
        parent_name: Optional[str] = None,
    ):
        self.code_manager.add_code(code_name, hexcolor, memo, parent_name)

    @autosave
    def update_code(
        self,
        old_name: str,
        new_name: Optional[str] = None,
        hexcolor: Optional[str] = None,
        memo: Optional[str] = None,
    ):
        self.code_manager.update_code(old_name, new_name, hexcolor, memo)

        if new_name and new_name != old_name:
            self.theme_manager.rename_code_in_themes(old_name, new_name)
            if old_name in self.memo_manager.memos:
                self.memo_manager.memos[new_name] = self.memo_manager.memos.pop(
                    old_name
                )


    @autosave
    def add_fragment(self, code_name: str, doc_name: str, fragment_data: dict):
        self.code_manager.add_fragment(code_name, doc_name, fragment_data)

    # ------------------------------------------------------------------
    # Delegación: Temas
    # ------------------------------------------------------------------
    @autosave
    def add_theme(self, theme_name: str, memo: str = ""):
        self.theme_manager.add_theme(theme_name, memo)

    @autosave
    def delete_theme(self, theme_name: str):
        self.theme_manager.delete_theme(theme_name)

    @autosave
    def add_code_to_theme(self, theme_name: str, code_name: str):
        self.theme_manager.add_code_to_theme(theme_name, code_name)

    @autosave
    def remove_code_from_theme(self, theme_name: str, code_name: str):
        self.theme_manager.remove_code_from_theme(theme_name, code_name)

    # ------------------------------------------------------------------
    # Delegación: Grupos de Documentos
    # ------------------------------------------------------------------
    @autosave
    def add_group(self, group_name: str):
        self.group_manager.add_group(group_name)

    @autosave
    def remove_group(self, group_name: str):
        self.group_manager.remove_group(group_name)

    @autosave
    def add_document_to_group(self, doc_name: str, group_name: str):
        self.group_manager.add_document_to_group(doc_name, group_name)

    @autosave
    def remove_document_from_group(self, doc_name: str, group_name: str):
        self.group_manager.remove_document_from_group(doc_name, group_name)

    # ------------------------------------------------------------------
    # Delegación: Diario
    # ------------------------------------------------------------------
    def get_diary_path(self) -> str:
        return os.path.join(self.path, "diario.json")
