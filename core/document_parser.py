from docx import Document as DocxDocument
import logging

import pymupdf
"""
OBSERVACION:
La licencia de pymupdf no permite uso comercial gratuito
"""

logger = logging.getLogger(__name__)




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
