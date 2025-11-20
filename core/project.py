import os
import json
from docx import Document as DocxDocument
from PyPDF2 import PdfReader

from core.memos import MemoManager


class Project:
    """Administra la estructura y persistencia de un proyecto de análisis cualitativo."""

    def __init__(self, name, base_path):
        self.name = name
        self.base_path = base_path
        self.path = os.path.join(base_path, name)
        self.documents_path = os.path.join(self.path, "documentos")
        self.codes_path = os.path.join(self.path, "codigos")
        self.metadata_path = os.path.join(self.path, "metadata.json")
        self.state_path = os.path.join(self.path, "project_data.json")
        self.project_path = self.path  # alias por compatibilidad
        self.memo_manager = MemoManager(self.path)
        self._ensure_structure()

    # ------------------------------------------------------------------
    # ESTRUCTURA Y PERSISTENCIA
    # ------------------------------------------------------------------
    def _ensure_structure(self):
        """Crea carpetas y archivos base si no existen."""
        os.makedirs(self.documents_path, exist_ok=True)
        os.makedirs(self.codes_path, exist_ok=True)
        if not os.path.exists(self.metadata_path):
            meta = {"name": self.name, "documents": []}
            with open(self.metadata_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=4, ensure_ascii=False)

    def save_state(self, codes, documents, highlights):
        """Persiste el estado principal del proyecto."""
        data = {
            "codes": codes,
            "documents": documents,
            "highlights": highlights,
        }
        os.makedirs(self.path, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_state(self):
        """Carga el estado guardado (si existe)."""
        if not os.path.exists(self.state_path):
            return {"codes": [], "documents": [], "highlights": {}}
        with open(self.state_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # DIARIO DE CODIFICACIÓN
    # ------------------------------------------------------------------
    def get_diary_path(self):
        return os.path.join(self.path, "diario.txt")

    def load_diary(self):
        diary_path = self.get_diary_path()
        if not os.path.exists(diary_path):
            return ""
        with open(diary_path, "r", encoding="utf-8") as f:
            return f.read()

    def save_diary(self, text):
        diary_path = self.get_diary_path()
        os.makedirs(self.path, exist_ok=True)
        with open(diary_path, "w", encoding="utf-8") as f:
            f.write(text or "")

    # ------------------------------------------------------------------
    # DOCUMENTOS
    # ------------------------------------------------------------------
    def import_document(self, file_path):
        """Importa un archivo TXT, DOCX o PDF y devuelve (nombre, texto)."""
        ext = os.path.splitext(file_path)[1].lower()
        filename = os.path.splitext(os.path.basename(file_path))[0]
        dest_name = f"{filename}.txt"
        dest_path = os.path.join(self.documents_path, dest_name)

        if ext == ".docx":
            text = self._read_docx(file_path)
        elif ext == ".pdf":
            text = self._read_pdf(file_path)
        elif ext == ".txt":
            text = self._read_txt(file_path)
        else:
            raise ValueError("Solo se admiten archivos .txt, .docx o .pdf")

        self._write_text(dest_path, text)
        self._register_document(dest_name)
        return dest_name, text

    def _register_document(self, document_name):
        """Añade el documento al metadata.json para compatibilidad."""
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        else:
            meta = {"name": self.name, "documents": []}

        if document_name not in meta["documents"]:
            meta["documents"].append(document_name)
            with open(self.metadata_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=4, ensure_ascii=False)

    def list_documents(self):
        """Devuelve los documentos almacenados en la carpeta del proyecto."""
        if not os.path.exists(self.documents_path):
            return []
        return sorted(f for f in os.listdir(self.documents_path) if f.lower().endswith(".txt"))

    def get_document_path(self, document_name):
        return os.path.join(self.documents_path, document_name)

    def read_document(self, document_name):
        """Lee el texto plano almacenado para un documento."""
        doc_path = self.get_document_path(document_name)
        if not os.path.exists(doc_path):
            return ""
        with open(doc_path, "r", encoding="utf-8") as f:
            return f.read()

    def _write_text(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    # ------------------------------------------------------------------
    # LECTORES DE FORMATOS
    # ------------------------------------------------------------------
    def _read_txt(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as f:
                return f.read()

    def _read_docx(self, file_path):
        doc = DocxDocument(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    def _read_pdf(self, file_path):
        reader = PdfReader(file_path)
        text = []
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text.append(content)
        return "\n".join(text)

    # ------------------------------------------------------------------
    # EXPORTES POR DOCUMENTO (RESERVADO)
    # ------------------------------------------------------------------
    def save_document_codes(self, document):
        """Guarda los códigos de un documento en un archivo JSON independiente."""
        os.makedirs(self.codes_path, exist_ok=True)
        codes_file = os.path.join(self.codes_path, f"{document.title}_codes.json")
        with open(codes_file, "w", encoding="utf-8") as f:
            json.dump(document.codes, f, indent=4, ensure_ascii=False)

    def load_document_codes(self, document_title):
        """Carga códigos previamente exportados para un documento."""
        codes_file = os.path.join(self.codes_path, f"{document_title}_codes.json")
        if not os.path.exists(codes_file):
            return []
        with open(codes_file, "r", encoding="utf-8") as f:
            return json.load(f)
