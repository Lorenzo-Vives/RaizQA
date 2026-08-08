import logging
from typing import Dict, List, Optional, Callable

from diff_match_patch import diff_match_patch

from typing import Dict, List, Optional, Callable

from core.data_models import Code, Fragment

logger = logging.getLogger(__name__)


def sync_fragments(
    old_text: str,
    new_text: str,
    fragments: List[dict],
    match_threshold: float = 0.3,
) -> List[dict]:
    """
    Reubica los fragmentos de código cuando el texto de un documento ha sido editado.
    """
    dmp = diff_match_patch()
    dmp.Match_Threshold = match_threshold
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
    
    def __init__(self):
        self.codes_dict: Dict[str, Code] = {}

    def add_code(
        self,
        code_name: str,
        hexcolor: str = "#5d9bd3",
        memo: str = "",
        parent_name: Optional[str] = None,
    ):
        if not code_name:
            logger.warning("Nombre de código vacío o nulo.")
            return
        if code_name in self.codes_dict:
            logger.warning("El código '%s' ya existe.", code_name)
            return
        if parent_name and parent_name not in self.codes_dict:
            logger.warning("El código padre '%s' no existe.", parent_name)
            parent_name = None
        elif parent_name and self.codes_dict[parent_name].parent is not None:
            parent_name = self.codes_dict[parent_name].parent

        self.codes_dict[code_name] = Code(
            hexcolor=hexcolor,
            memo=memo,
            parent=parent_name,
        )
        if parent_name:
            self.codes_dict[parent_name].children.append(code_name)
            
            
    def delete_code(self, code_name: str, cascade: bool = False) -> List[str]:
        if not code_name:
            logger.warning("Nombre de código vacío o nulo.")
            return []
        code = self.codes_dict.pop(code_name, None)
        if not code:
            logger.warning("El código '%s' no existe, no se puede borrar.", code_name)
            return []

        deleted = [code_name]

        if code.children:
            if cascade:
                for child in list(code.children):
                    deleted.extend(self.delete_code(child, cascade=True))
            else:
                for child in code.children:
                    if child in self.codes_dict:
                        self.codes_dict[child].parent = None

        if (
            code.parent
            and code.parent in self.codes_dict
            and code_name in self.codes_dict[code.parent].children
        ):
            self.codes_dict[code.parent].children.remove(code_name)

        return deleted
    

    def update_code(
        self,
        old_name: str,
        new_name: Optional[str] = None,
        hexcolor: Optional[str] = None,
        memo: Optional[str] = None,
    ):
        if not old_name:
            logger.warning("Nombre de código vacío o nulo.")
            return
        if old_name not in self.codes_dict:
            logger.warning("El código '%s' no existe, no se puede actualizar.", old_name)
            return
        if new_name is not None and not new_name:
            logger.warning("El nuevo nombre no puede ser vacío.")
            return

        target_name = old_name

        if new_name:
            if new_name == old_name:
                logger.warning("El nombre nuevo debe ser diferente al actual.")
                return
            if new_name in self.codes_dict:
                logger.warning("El código '%s' ya existe, no se puede renombrar.", new_name)
                return

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
        if not code_name:
            logger.warning("Nombre de código vacío o nulo.")
            return
        if not doc_name:
            logger.warning("Nombre de documento vacío o nulo.")
            return
        if not fragment_data:
            logger.warning("Datos de fragmento vacíos o nulos.")
            return
        if code_name not in self.codes_dict:
            self.add_code(code_name)
        frag = Fragment.from_dict(fragment_data)
        self.codes_dict[code_name].fragments.setdefault(doc_name, []).append(frag)

    def remove_fragments_for_document(self, doc_name: str):
        if not doc_name:
            logger.warning("Nombre de documento vacío o nulo.")
            return
        if not self.codes_dict:
            logger.info("No hay códigos registrados, nada que remover.")
            return
        for code in self.codes_dict.values():
            code.fragments.pop(doc_name, None)

    def get_fragments_for_code(
        self, code_name: str, get_text_fn: Callable[[str], str]
    ) -> List[dict]:
        if not code_name:
            logger.warning("Nombre de código vacío o nulo.")
            return []
        if code_name not in self.codes_dict:
            logger.warning("El código '%s' no existe.", code_name)
            return []
        if not self.codes_dict[code_name].fragments:
            logger.info("El código '%s' no tiene fragmentos asignados.", code_name)
            return []

        results = []
        for doc_name, fragments in self.codes_dict[code_name].fragments.items():
            for frag in fragments:
                if frag.type == "image":
                    results.append({"doc": doc_name, **frag.to_dict()})
                    continue
                full_text = get_text_fn(doc_name)
                if not full_text:
                    logger.warning("El texto del documento '%s' está vacío.", doc_name)
                    continue
                results.append(
                    {
                        "doc": doc_name,
                        "start": frag.start,
                        "end": frag.end,
                        "text": full_text[frag.start : frag.end],
                    }
                )
        return results

    def get_fragments_for_document(self, doc_name: str) -> List[dict]:
        if not doc_name:
            logger.warning("Nombre de documento vacio o nulo.")
            return []
        if not self.codes_dict:
            logger.warning("No hay codigos registrados")
            return []
        result = []
        for code_name, code in self.codes_dict.items():
            for frag in code.fragments.get(doc_name, []):
                f = frag.to_dict()
                f["color"] = code.hexcolor
                f["document"] = doc_name
                result.append(f)
        if not result:
            logger.info("No se encontraron fragmentos para el documento '%s'.", doc_name)
        return result

    def sync_hierarchy(self, hierarchy: Dict[str, Optional[str]]):
        if not hierarchy:
            logger.warning("Jerarquía vacía o nula.")
            return
        if not self.codes_dict:
            logger.warning("No hay códigos registrados para sincronizar jerarquía.")
            return
        for code in self.codes_dict.values():
            code.children = []
        for code_name, parent_name in hierarchy.items():
            if code_name not in self.codes_dict:
                logger.info("Código '%s' en jerarquía no existe, se omite.", code_name)
                continue
            parent_name = parent_name if parent_name in self.codes_dict else None
            self.codes_dict[code_name].parent = parent_name
            if parent_name:
                self.codes_dict[parent_name].children.append(code_name)

    def sync_fragments_for_document(self, doc_name: str, old_text: str, new_text: str):
        if not doc_name:
            logger.warning("Nombre de documento vacío o nulo.")
            return
        if old_text is None or new_text is None:
            logger.warning("Textos de sincronización nulos para '%s'.", doc_name)
            return
        if old_text == new_text:
            logger.info("El texto no cambió para '%s', no se sincronizan fragmentos.", doc_name)
            return
        for code in self.codes_dict.values():
            fragments = code.fragments.get(doc_name, [])
            if not fragments:
                continue
            frag_dicts = [f.to_dict() for f in fragments]
            updated_dicts = sync_fragments(old_text, new_text, frag_dicts)
            code.fragments[doc_name] = [Fragment.from_dict(f) for f in updated_dicts]

    def get_all_codes(self) -> Dict[str, dict]:
        """Retorna los códigos como dicts planos para serialización."""
        return {name: code.to_dict() for name, code in self.codes_dict.items()}

    def load_codes(self, codes_dict: Dict[str, dict]):
        if not codes_dict:
            logger.warning("Diccionario de códigos vacío o nulo, no se carga nada.")
            return
        self.codes_dict = {k: Code.from_dict(v) for k, v in codes_dict.items()}

