import os
import json
import shutil
import logging
from typing import Dict, List, Optional, Tuple


from typing import Dict, List, Optional
from core.constants import (TEXT_EXTENSIONS, IMAGE_EXTENSIONS,
                            ALLOWED_EXTENSIONS)

from core.document_parser import DocumentParser 
                            
logger = logging.getLogger(__name__)



def get_file_extension(file_path: str) -> str:
    return os.path.splitext(file_path)[1].lower()


def get_file_name(file_path: str) -> str:
    basename = os.path.basename(file_path)
    return os.path.splitext(basename)[0]


def file_extension_allowed(file_path: str) -> bool:
    return get_file_extension(file_path) in ALLOWED_EXTENSIONS

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

    def __init__(self, documents_path: str, metadata_path: str, project_name: Optional[str] = None):
        self.documents_path = documents_path
        self.metadata_path = metadata_path
        self.project_name = project_name
        self.documents: List[dict] = []
        self.text_cache: Dict[str, str] = {}

        os.makedirs(self.documents_path, exist_ok=True)
        self._init_metadata()

    def _init_metadata(self):
        if not os.path.exists(self.metadata_path):
            self._write_metadata({"name": self.project_name, "documents": []})
        else:
            meta = self._read_metadata()
            self.documents = [{"name": d} for d in meta.get("documents", [])]
            # Backfill de "name" para proyectos creados antes de este fix
            # (import_manager.py y MergeManager dependen de esta clave para
            # identificar el proyecto dentro de un .rqa).
            if not meta.get("name") and self.project_name:
                self._write_metadata({**meta, "name": self.project_name})

    def _read_metadata(self) -> dict:
        try:
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"documents": []}

    def _write_metadata(self, meta: dict):
        if self.project_name and "name" not in meta:
            meta = {**meta, "name": self.project_name}
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
            logger.warning(f"No existe la ruta: {doc_path}")
            return ""
        ext = get_file_extension(doc_name)
        if ext in self.IMAGE_EXTENSIONS:
            logger.warning(f"")
            
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

    def register_document(self, document_name: str):
        self._register_in_metadata(document_name)
