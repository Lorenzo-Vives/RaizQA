# models/project.py
import os
import json
from docx import Document as DocxDocument
from PyPDF2 import PdfReader

class Project:
    def __init__(self, name, base_path):
        self.name = name
        self.base_path = base_path
        self.path = os.path.join(base_path, name)
        self.documents_path = os.path.join(self.path, "documentos")
        self.codes_path = os.path.join(self.path, "codigos")
        self.metadata_path = os.path.join(self.path, "metadata.json")
        self.project_path = self.path  # alias por compatibilidad
        self._ensure_structure()

    def _ensure_structure(self):
        """Crea la estructura de carpetas si no existe"""
        os.makedirs(self.documents_path, exist_ok=True)
        os.makedirs(self.codes_path, exist_ok=True)

        # Si no existe el archivo metadata.json, lo crea
        if not os.path.exists(self.metadata_path):
            with open(self.metadata_path, "w", encoding="utf-8") as f:
                json.dump({"name": self.name, "documents": []}, f, indent=4)

    def import_document(self, file_path):
        """Importa un documento Word o PDF, lo convierte a texto y lo guarda"""
        ext = os.path.splitext(file_path)[1].lower()
        filename = os.path.splitext(os.path.basename(file_path))[0]
        txt_path = os.path.join(self.documents_path, f"{filename}.txt")

        if ext == ".docx":
            text = self._read_docx(file_path)
        elif ext == ".pdf":
            text = self._read_pdf(file_path)
        else:
            raise ValueError("Solo se admiten archivos .docx o .pdf")

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        # Registrar en metadata
        with open(self.metadata_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["documents"].append(f"{filename}.txt")
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=4, ensure_ascii=False)

        print(f"✅ Documento '{filename}' importado correctamente.")

    def _read_docx(self, file_path):
        """Extrae texto de un archivo Word (.docx)"""
        doc = DocxDocument(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    def _read_pdf(self, file_path):
        """Extrae texto de un archivo PDF"""
        reader = PdfReader(file_path)
        text = []
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text.append(content)
        return "\n".join(text)

    def save_document_codes(self, document):
        """Guarda los códigos de un documento en un archivo JSON"""
        os.makedirs(self.codes_path, exist_ok=True)
        codes_file = os.path.join(self.codes_path, f"{document.title}_codes.json")
        with open(codes_file, "w", encoding="utf-8") as f:
            json.dump(document.codes, f, indent=4, ensure_ascii=False)
        print(f"✅ Códigos de '{document.title}' guardados en {codes_file}")
    
    def load_document_codes(self, document_title):
        """Carga los códigos guardados de un documento"""
        codes_file = os.path.join(self.codes_path, f"{document_title}_codes.json")
        if not os.path.exists(codes_file):
            print(f"⚠️ No se encontraron códigos para '{document_title}'")
            return []
        with open(codes_file, "r", encoding="utf-8") as f:
            codes = json.load(f)
        return codes      
        