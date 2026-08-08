import os
import json
import threading
import logging
import functools
from typing import Dict, List, Optional, Tuple
from diff_match_patch import diff_match_patch

from core import (CodeManager, DiaryManager, DocumentManager,
                GroupManager, MemoManager, StorageManager,
                ThemeManager)
logger = logging.getLogger(__name__)

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


class CaseStudyManager:
    def __init__(self):
        self.case_studies: List[dict] = []

    def load(self, case_studies: List[dict]):
        self.case_studies = case_studies or []

    def get_all(self) -> List[dict]:
        return list(self.case_studies)





def autosave(method):
    
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):

        resultado = method(self, *args, **kwargs)
        
        self.save_state()
        

        return resultado
    return wrapper

class Project:
    def __init__(
        self,
        name: str,
        base_path: str,
        doc_manager: Optional[DocumentManager] = None,
        code_manager: Optional[CodeManager] = None,
        theme_manager: Optional[ThemeManager] = None,
        group_manager: Optional[GroupManager] = None,
        annotation_manager: Optional[AnnotationManager] = None,
        case_study_manager: Optional[CaseStudyManager] = None,
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
            project_name=name,
        )
        self.code_manager = code_manager or CodeManager()
        self.theme_manager = theme_manager or ThemeManager()
        self.group_manager = group_manager or GroupManager()
        self.annotation_manager = annotation_manager or AnnotationManager()
        self.case_study_manager = case_study_manager or CaseStudyManager()
        self.storage = storage or StorageManager()
        self.memo_manager = memo_manager or MemoManager({})
        self.diary_manager = diary_manager or DiaryManager(self.path)

        self._ensure_structure()
        # Protege save_state
        self._state_lock = threading.RLock()
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
        self.case_study_manager.load(data.get("case_studies", []))

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
        with self._state_lock:
            state = {
                "documents": self.doc_manager.documents,
                "highlights": self.annotation_manager.get_highlights(),
                "codes_dict": self.code_manager.get_all_codes(),
                "themes_dict": self.theme_manager.get_all_themes(),
                "case_studies": self.case_study_manager.get_all(),
                "memos_dict": self.memo_manager.memos,
                "doc_groups": self.group_manager.groups,
            }
            ok = self.storage.save(self.path, state)
            if not ok:
                # No lo tragamos en silencio: un fallo de disco debe ser visible
                # de inmediato, no descubierto 30s después por un timer que ya no existe.
                raise IOError(
                    f"No se pudo guardar el estado del proyecto '{self.name}' en disco."
                )
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
    def remove_document_from_all_groups(self, doc_name: str):
        self.group_manager.remove_document_from_all_groups(doc_name)

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

    def get_fragments_for_document(self, doc_name: str) -> List[dict]:
        return self.code_manager.get_fragments_for_document(doc_name)

    def get_hydrated_codes(self) -> Dict[str, dict]:
        """Copia de codes_dict con el texto real de cada fragmento inyectado."""
        hydrated = self.code_manager.get_all_codes()
        for code_name, data in hydrated.items():
            for doc_name, frags in data.get("fragments", {}).items():
                doc_text = self.get_document_text(doc_name)
                for frag in frags:
                    if frag.get("type") == "image":
                        continue
                    if "text" not in frag:
                        start, end = frag.get("start", 0), frag.get("end", 0)
                        frag["text"] = doc_text[start:end]
        return hydrated

    def locate_fragment_by_text(self, doc_name: str, snippet: str, hint_start: int = 0):
        """Relocaliza un fragmento de texto por coincidencia aproximada (diff_match_patch)
        cuando no existen offsets persistidos confiables."""
        if not snippet:
            return None, None
        doc_text = self.doc_manager.get_document_text(doc_name)
        dmp = diff_match_patch()
        dmp.Match_Threshold = 0.3
        start = dmp.match_main(doc_text, snippet, hint_start)
        if start == -1:
            return None, None
        return start, start + len(snippet)

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

    @autosave
    def sync_code_hierarchy(self, hierarchy: Dict[str, Optional[str]]):
        self.code_manager.sync_hierarchy(hierarchy)

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

    @autosave
    def sync_themes(self, themes_data: List[dict]):
        converted = {
            t.get("name", "Tema sin nombre"): {
                "memo": t.get("memo", ""),
                "codes": t.get("codes", []),
            }
            for t in themes_data
        }
        self.theme_manager.load_themes(converted)

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

    @autosave
    def sync_doc_groups(self, doc_groups: Dict[str, List[str]]):
        """Reemplaza la estructura completa de grupos (usado por drag-and-drop en la Vista)."""
        self.group_manager.groups = doc_groups

    # ------------------------------------------------------------------
    # Delegación: Estudios de Caso
    # ------------------------------------------------------------------
    @autosave
    def save_case_studies(self, case_studies: List[dict]):
        self.case_study_manager.load(case_studies)

    def get_case_studies(self) -> List[dict]:
        return self.case_study_manager.get_all()

    # ------------------------------------------------------------------
    # Delegación: Memos
    # ------------------------------------------------------------------
    @autosave
    def set_memo(self, code_name: str, memo_text: str):
        self.memo_manager.add_or_update_memo(code_name, memo_text)

    @autosave
    def delete_memo(self, code_name: str):
        self.memo_manager.delete_memo(code_name)

    # ------------------------------------------------------------------
    # Delegación: Diario
    # ------------------------------------------------------------------
    def get_diary_path(self) -> str:
        return os.path.join(self.path, "diario.json")