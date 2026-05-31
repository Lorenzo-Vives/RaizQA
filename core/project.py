import os
import json
import shutil
import platform
import subprocess
from docx import Document as DocxDocument
from PyPDF2 import PdfReader
from diff_match_patch import diff_match_patch

from core.memos import MemoManager
from core.diary_manager import DiaryManager


class Project:
    """Administra la estructura y persistencia de un proyecto de análisis cualitativo."""

    TEXT_EXTENSIONS = {".txt", ".docx", ".pdf"}
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff"}

    def __init__(self, name, base_path):
        self.name = name
        self.base_path = base_path
        self.path = os.path.join(base_path, name)
        self.documents_path = os.path.join(self.path, "documentos")
        self.codes_path = os.path.join(self.path, "codigos")
        self.metadata_path = os.path.join(self.path, "metadata.json")
        self.state_path = os.path.join(self.path, "project_data.json")
        self.project_path = self.path  # alias por compatibilidad
        self.diary_manager = DiaryManager(self.path)
        self.memos_dict = {}
        self.memo_manager = MemoManager(self.memos_dict)
        
        # Nuevas Estructuras de Datos (EDDs)
        self.codes_dict = {}
        self.themes_dict = {}
        self.texts_dict = {}
        
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

    def save_project_data(self, documents, highlights, doc_groups=None, themes=None, case_studies=None):
        """Persiste todo el estado (EDDs y metadatos) en un único archivo atómico."""
        data = {
            "documents": documents,
            "highlights": highlights,
            "codes_dict": self.codes_dict,
            "themes_dict": self.themes_dict,
            "memos_dict": self.memos_dict,
        }
        if doc_groups is not None:
            data["doc_groups"] = doc_groups
            self.sync_doc_groups_to_fs(doc_groups)
        if themes is not None:
            data["themes"] = themes
        if case_studies is not None:
            data["case_studies"] = case_studies
            
        tmp_path = self.state_path + ".tmp"
        bak_path = self.state_path + ".bak"
        
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            import time
            success = False
            for _ in range(3):
                try:
                    if os.path.exists(self.state_path):
                        os.replace(self.state_path, bak_path)
                    os.replace(tmp_path, self.state_path)
                    success = True
                    break
                except Exception:
                    time.sleep(0.2)
            if not success:
                print(f"Advertencia: No se pudo actualizar atómicamente {self.state_path}")
        except Exception as e:
            print(f"Error fatal al guardar proyecto: {e}")

    def load_project_data(self):
        """Carga el estado único guardado. Si no existe, intenta con el backup."""
        default_state = {"documents": [], "highlights": {}, "codes_dict": {}, "themes_dict": {}}
        
        data = default_state
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                # Si el original está corrupto, usar el backup
                bak_path = self.state_path + ".bak"
                if os.path.exists(bak_path):
                    with open(bak_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        
        self.codes_dict = data.get("codes_dict", {})
        self.themes_dict = data.get("themes_dict", {})
        self.memos_dict = data.get("memos_dict", {})
        
        # Migración: Si memos_dict está vacío, intentar cargar del archivo antiguo memos.json
        if not self.memos_dict:
            old_memos_path = os.path.join(self.path, "memos.json")
            if os.path.exists(old_memos_path):
                try:
                    with open(old_memos_path, "r", encoding="utf-8") as f:
                        self.memos_dict = json.load(f)
                except Exception:
                    pass
                    
        self.memo_manager.memos = self.memos_dict
        
        fs_doc_groups = self.scan_doc_groups_from_fs()
        if fs_doc_groups and (len(fs_doc_groups.get("__root__", [])) > 0 or len(fs_doc_groups) > 1):
            data["doc_groups"] = fs_doc_groups
            
        return data

    def sync_doc_groups_to_fs(self, doc_groups):
        """Refleja la estructura de doc_groups en el sistema de archivos real usando .raizptr."""
        if not doc_groups or not os.path.exists(self.documents_path):
            return
            
        # 1. Eliminar SOLAMENTE los .raizptr existentes (para ser seguros y no borrar archivos del usuario)
        for item in os.listdir(self.documents_path):
            item_path = os.path.join(self.documents_path, item)
            if os.path.isdir(item_path):
                # Eliminar solo .raizptr dentro del directorio
                for sub_item in os.listdir(item_path):
                    if sub_item.endswith(".raizptr"):
                        os.remove(os.path.join(item_path, sub_item))
                
                # Si el directorio quedó vacío y no está en doc_groups, lo borramos
                if not os.listdir(item_path) and item not in doc_groups:
                    try:
                        os.rmdir(item_path)
                    except OSError:
                        pass
                
        # 2. Recrear las subcarpetas según doc_groups y añadir los .raizptr
        for group_name, docs in doc_groups.items():
            if group_name == "__root__":
                continue
                
            group_dir = os.path.join(self.documents_path, group_name)
            os.makedirs(group_dir, exist_ok=True)
            
            # Ocultar la carpeta en Windows y macOS
            if platform.system() == "Windows":
                try:
                    import ctypes
                    FILE_ATTRIBUTE_HIDDEN = 0x02
                    ctypes.windll.kernel32.SetFileAttributesW(group_dir, FILE_ATTRIBUTE_HIDDEN)
                except Exception:
                    pass
            elif platform.system() == "Darwin":
                try:
                    subprocess.run(["chflags", "hidden", group_dir], check=False)
                except Exception:
                    pass
            
            for doc in docs:
                ptr_path = os.path.join(group_dir, f"{doc}.raizptr")
                with open(ptr_path, "w", encoding="utf-8") as f:
                    f.write(f"target=../{doc}")

    def scan_doc_groups_from_fs(self):
        """Reconstruye doc_groups escaneando la carpeta documentos/."""
        doc_groups = {"__root__": []}
        if not os.path.exists(self.documents_path):
            return doc_groups
            
        for item in os.listdir(self.documents_path):
            item_path = os.path.join(self.documents_path, item)
            
            # Documentos en la raíz
            if os.path.isfile(item_path):
                ext = os.path.splitext(item)[1].lower()
                if ext in self.TEXT_EXTENSIONS or ext in self.IMAGE_EXTENSIONS:
                    doc_groups["__root__"].append(item)
                    
            # Subcarpetas
            elif os.path.isdir(item_path):
                group_name = item
                doc_groups[group_name] = []
                for sub_item in os.listdir(item_path):
                    if sub_item.endswith(".raizptr"):
                        doc_name = sub_item[:-8] # quitar .raizptr
                        doc_groups[group_name].append(doc_name)
                        
        # Un documento no debe aparecer en __root__ si ya está en una carpeta
        docs_in_groups = set()
        for group, docs in doc_groups.items():
            if group != "__root__":
                docs_in_groups.update(docs)
                
        doc_groups["__root__"] = [doc for doc in doc_groups["__root__"] if doc not in docs_in_groups]
        
        return doc_groups
    # ------------------------------------------------------------------
    # DIARIO DE CODIFICACIÓN
    # ------------------------------------------------------------------
    def get_diary_path(self):
        return os.path.join(self.path, "diario.json")
    # ------------------------------------------------------------------
    # DOCUMENTOS
    # ------------------------------------------------------------------
    def import_document(self, file_path):
        """Importa un archivo de texto o imagen y devuelve (nombre, texto)."""
        ext = os.path.splitext(file_path)[1].lower()
        filename = os.path.splitext(os.path.basename(file_path))[0]
        dest_name = f"{filename}{ext if ext in self.IMAGE_EXTENSIONS else '.txt'}"
        dest_path = os.path.join(self.documents_path, dest_name)

        if ext in self.IMAGE_EXTENSIONS:
            shutil.copy2(file_path, dest_path)
            text = ""
        elif ext == ".docx":
            text = self._read_docx(file_path)
        elif ext == ".pdf":
            text = self._read_pdf(file_path)
        elif ext == ".txt":
            text = self._read_txt(file_path)
        else:
            raise ValueError("Solo se admiten archivos .txt, .docx, .pdf o imágenes (png, jpg, jpeg, bmp, gif, tiff)")

        if ext in self.TEXT_EXTENSIONS:
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

    def delete_document(self, document_name):
        """Elimina el archivo y lo quita del metadata."""
        doc_path = self.get_document_path(document_name)
        if os.path.exists(doc_path):
            try:
                os.remove(doc_path)
            except OSError:
                pass
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if document_name in meta.get("documents", []):
                    meta["documents"].remove(document_name)
                    with open(self.metadata_path, "w", encoding="utf-8") as f:
                        json.dump(meta, f, indent=4, ensure_ascii=False)
            except Exception:
                pass

    def list_documents(self):
        """Devuelve los documentos almacenados en la carpeta del proyecto."""
        if not os.path.exists(self.documents_path):
            return []
        allowed = tuple(self.TEXT_EXTENSIONS | self.IMAGE_EXTENSIONS)
        return sorted(f for f in os.listdir(self.documents_path) if f.lower().endswith(allowed))

    def get_document_path(self, document_name):
        return os.path.join(self.documents_path, document_name)

    def read_document(self, document_name):
        """Lee el texto plano almacenado para un documento. Las imágenes devuelven cadena vacía."""
        doc_path = self.get_document_path(document_name)
        if not os.path.exists(doc_path):
            return ""
        ext = os.path.splitext(document_name)[1].lower()
        if ext in self.IMAGE_EXTENSIONS:
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

    # ==================================================================
    # NUEVAS ESTRUCTURAS DE DATOS (EDDs) EN MEMORIA
    # ==================================================================
    
    # --- TEXTOS EN MEMORIA ---
    def load_all_texts_to_memory(self):
        """Carga el texto de todos los documentos en self.texts_dict para lectura O(1)."""
        for doc_name in self.list_documents():
            self.get_document_text(doc_name)

    def get_document_text(self, doc_name):
        """Devuelve el texto del documento. Si no está en memoria, lo carga perezosamente."""
        if doc_name not in self.texts_dict:
            self.texts_dict[doc_name] = self.read_document(doc_name)
        return self.texts_dict[doc_name]

    # --- CRUD CÓDIGOS ---
    def add_code(self, code_name, hexcolor="#5d9bd3", memo=""):
        if code_name not in self.codes_dict:
            self.codes_dict[code_name] = {
                "hexcolor": hexcolor,
                "memo": memo,
                "fragments": {} # doc_name: [{"start": 0, "end": 10}, ...]
            }

    def delete_code(self, code_name):
        if code_name in self.codes_dict:
            del self.codes_dict[code_name]
            # También lo sacamos de cualquier tema al que pertenezca
            for theme in self.themes_dict.values():
                if code_name in theme.get("codes", []):
                    theme["codes"].remove(code_name)

    def update_code(self, old_name, new_name=None, hexcolor=None, memo=None):
        if old_name not in self.codes_dict:
            return
            
        # Si se renombra el código, extraemos sus datos y cambiamos la llave
        if new_name and new_name != old_name:
            self.codes_dict[new_name] = self.codes_dict.pop(old_name)
            target_name = new_name
            # Actualizar en los temas
            for theme in self.themes_dict.values():
                if old_name in theme.get("codes", []):
                    theme["codes"].remove(old_name)
                    theme["codes"].append(new_name)
        else:
            target_name = old_name
            
        if hexcolor is not None:
            self.codes_dict[target_name]["hexcolor"] = hexcolor
        if memo is not None:
            self.codes_dict[target_name]["memo"] = memo

    def add_fragment(self, code_name, doc_name, fragment_data):
        """Añade los datos de un fragmento (texto o imagen) a un código específico."""
        self.add_code(code_name) # Asegurar que el código exista
        fragments_doc = self.codes_dict[code_name]["fragments"].setdefault(doc_name, [])
        fragments_doc.append(fragment_data)

    def get_fragments_for_code(self, code_name):
        """
        Recupera el texto real de forma instantánea (O(1)) para todos los fragmentos
        asociados a un código utilizando el texto pre-cargado.
        """
        if code_name not in self.codes_dict:
            return []
            
        results = []
        for doc_name, fragments in self.codes_dict[code_name]["fragments"].items():
            full_text = self.get_document_text(doc_name)
            for frag in fragments:
                start, end = frag["start"], frag["end"]
                text_snippet = full_text[start:end]
                results.append({
                    "doc": doc_name,
                    "start": start,
                    "end": end,
                    "text": text_snippet
                })
        return results

    # --- CRUD TEMAS ---
    def add_theme(self, theme_name, memo=""):
        if theme_name not in self.themes_dict:
            self.themes_dict[theme_name] = {
                "memo": memo,
                "codes": []
            }

    def delete_theme(self, theme_name):
        if theme_name in self.themes_dict:
            del self.themes_dict[theme_name]

    def add_code_to_theme(self, theme_name, code_name):
        self.add_theme(theme_name)
        if code_name not in self.themes_dict[theme_name]["codes"]:
            self.themes_dict[theme_name]["codes"].append(code_name)
            
    def remove_code_from_theme(self, theme_name, code_name):
        if theme_name in self.themes_dict:
            if code_name in self.themes_dict[theme_name]["codes"]:
                self.themes_dict[theme_name]["codes"].remove(code_name)

    # --- PERSISTENCIA ELIMINADA: TODO SE MANEJA EN SAVE_PROJECT_DATA ---
    def update_document_text(self, doc_name, new_text):
        """
        Actualiza el texto en disco y resincroniza dinámicamente 
        los índices de los códigos asociados usando Diff-Match-Patch.
        """
        # 1. Leer el texto original ANTES de sobrescribirlo
        old_text = self.read_document(doc_name)
        
        # 2. Sincronizar la Estructura de Datos (EDD)
        self._sync_fragment_indices(doc_name, old_text, new_text)
        
        # 3. Sobrescribir el archivo en disco
        doc_path = self.get_document_path(doc_name)
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(new_text)

    def _sync_fragment_indices(self, doc_name, old_text, new_text):
        """
        Busca dónde aterrizaron los fragmentos antiguos dentro del texto nuevo.
        """
        dmp = diff_match_patch()
        
        # Tolerancia del algoritmo (0.0 es exacto, 0.5 es muy flexible)
        # 0.3 es un buen balance: permite pequeñas correcciones ortográficas 
        # sin perder el fragmento, pero falla si cambian la frase entera.
        dmp.Match_Threshold = 0.3 
        
        for code_name, data in self.codes_dict.items():
            fragments = data.get("fragments", {}).get(doc_name, [])
            valid_fragments = []
            
            for frag in fragments:
                # Ignorar imágenes u otros tipos de datos
                if frag.get("type") != "text":
                    valid_fragments.append(frag)
                    continue
                    
                start = frag.get("start")
                end = frag.get("end")
                
                if start is None or end is None:
                    valid_fragments.append(frag)
                    continue
                    
                # Extraemos cómo se veía el fragmento antes de la edición
                frag_text = old_text[start:end]
                
                # Buscamos la nueva ubicación aproximada partiendo de la ubicación vieja
                new_start = dmp.match_main(new_text, frag_text, start)
                
                if new_start != -1:
                    # El algoritmo encontró el fragmento. Actualizamos índices.
                    frag["start"] = new_start
                    frag["end"] = new_start + len(frag_text)
                    valid_fragments.append(frag)
                else:
                    # El usuario borró u alteró completamente esta frase.
                    # Al no agregarlo a valid_fragments, se elimina de la EDD silenciosamente.
                    print(f"⚠️ Fragmento eliminado automáticamente en el código '{code_name}' por edición destructiva.")
                    
            # Guardamos la lista purgada y actualizada en la EDD
            self.codes_dict[code_name]["fragments"][doc_name] = valid_fragments