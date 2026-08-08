import os
import shutil
import zipfile
import tempfile
import json
from diff_match_patch import diff_match_patch


class ImportManager:
    """Gestor dedicado para desempaquetar proyectos en formato .rqa"""

    @staticmethod
    def import_project_from_rqa(rqa_path: str, dest_base_path: str) -> str:
        """
        Extrae un archivo .rqa en el dest_base_path.
        Retorna la ruta completa al nuevo proyecto.
        Lanza excepciones si el archivo es inválido.
        """
        if not os.path.exists(rqa_path):
            raise FileNotFoundError(f"El archivo {rqa_path} no existe.")
            
        # Comprobar que sea un ZIP válido
        if not zipfile.is_zipfile(rqa_path):
            raise ValueError("El archivo seleccionado no es un formato válido o está corrupto.")
            
        # Extraer a una carpeta temporal para validarlo
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(rqa_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                
            # Validar si tiene metadata.json
            metadata_path = os.path.join(temp_dir, "metadata.json")
            if not os.path.exists(metadata_path):
                raise ValueError("El archivo importado no contiene 'metadata.json'. No es un proyecto de RaizQA válido.")
                
            # Leer nombre del proyecto desde metadata.json
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    project_name = metadata.get("name")
                    if not project_name:
                        raise ValueError("El metadata.json no contiene el nombre del proyecto.")
            except Exception as e:
                raise ValueError(f"No se pudo leer el archivo metadata.json: {e}")
                
            # Calcular el destino final
            final_project_path = os.path.join(dest_base_path, project_name)
            
            if os.path.exists(final_project_path):
                shutil.rmtree(final_project_path)
                
            # Movemos la carpeta desde el temporal a la ubicación final
            shutil.copytree(temp_dir, final_project_path)
            
            return final_project_path

    @staticmethod
    def inspect_exchange_file(rex_path: str) -> dict:
        """
        Inspecciona un archivo .rex sin extraerlo por completo y devuelve los metadatos
        de los documentos, códigos y temas que contiene para que el usuario pueda
        seleccionarlos en la interfaz antes de importar.

        Args:
            rex_path (str): La ruta absoluta hacia el archivo .rex.

        Returns:
            dict: Datos del paquete, incluyendo 'documents', 'codes_dict', 'themes_dict' y 'memos_dict'.
        """
        if not os.path.exists(rex_path):
            raise FileNotFoundError(f"El archivo {rex_path} no existe.")
        if not zipfile.is_zipfile(rex_path):
            raise ValueError("El archivo no es un formato válido o está corrupto.")
            
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(rex_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                
            metadata_path = os.path.join(temp_dir, "metadata.json")
            if not os.path.exists(metadata_path):
                raise ValueError("El archivo no contiene metadata.json.")
                
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                
            if not metadata.get("is_exchange", False):
                raise ValueError("El archivo no es un Exchange File (.rex) válido.")
                
            data_path = os.path.join(temp_dir, "project_data.json")
            if not os.path.exists(data_path):
                raise ValueError("El archivo no contiene project_data.json.")
                
            with open(data_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
                
            return {
                "metadata": metadata,
                "documents": metadata.get("documents", []),
                "codes_dict": project_data.get("codes_dict", {}),
                "themes_dict": project_data.get("themes_dict", {}),
                "memos_dict": project_data.get("memos_dict", {})
            }

    @staticmethod
    def import_exchange_from_rex(rex_path: str, target_project, import_data: dict):
        """
        Importa datos desde un archivo .rex y los fusiona en el proyecto destino.

        Si un documento se sobrescribe con una nueva versión del paquete .rex,
        se utilizará diff_match_patch para realinear inteligentemente los índices de
        los fragmentos preexistentes, evitando que se pierda o desincronice el
        trabajo previo.

        Args:
            rex_path (str): La ruta absoluta hacia el archivo .rex.
            target_project (Project): El proyecto actual de RaizQA en el cual se inyectarán los datos.
            import_data (dict): Diccionario con las opciones de importación (códigos, documentos, memos, etc.)
        """
        dmp = diff_match_patch()
        
        # Guardamos el estado base legacy para resguardarlo
        legacy_state = target_project.load_project_data()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(rex_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                
            docs_to_import = import_data.get("documents", [])
            codes_to_import = import_data.get("codes", [])
            import_fragments = import_data.get("import_fragments", True)
            import_memos = import_data.get("import_memos", True)
            
            with open(os.path.join(temp_dir, "project_data.json"), 'r', encoding='utf-8') as f:
                pkg_data = json.load(f)
                
            pkg_codes = pkg_data.get("codes_dict", {})
            pkg_themes = pkg_data.get("themes_dict", {})
            pkg_memos = pkg_data.get("memos_dict", {})
            
            # 1. IMPORTAR DOCUMENTOS
            for doc in docs_to_import:
                src_path = os.path.join(temp_dir, "documentos", doc)
                if not os.path.exists(src_path):
                    continue
                    
                target_path = os.path.join(target_project.documents_path, doc)
                old_text = ""
                if os.path.exists(target_path):
                    old_text = target_project.get_document_text(doc)
                    
                # Sobrescribir
                shutil.copy2(src_path, target_path)
                target_project._register_document(doc)
                
                # Leer nuevo texto
                new_text = target_project.read_document(doc)
                target_project.texts_dict[doc] = new_text
                
                # Adaptar fragmentos existentes si el documento fue editado
                if old_text and old_text != new_text:
                    diffs = dmp.diff_main(old_text, new_text)
                    dmp.diff_cleanupSemantic(diffs)
                    
                    for code_name, code_data in target_project.codes_dict.items():
                        if doc in code_data.get("fragments", {}):
                            adapted_fragments = []
                            for frag in code_data["fragments"][doc]:
                                old_start = frag["start"]
                                old_end = frag["end"]
                                new_start = dmp.diff_xIndex(diffs, old_start)
                                new_end = dmp.diff_xIndex(diffs, old_end)
                                
                                if new_end > new_start:
                                    adapted_fragments.append({
                                        "start": new_start,
                                        "end": new_end,
                                        "code": frag.get("code", code_name)
                                    })
                            code_data["fragments"][doc] = adapted_fragments

            # 2. IMPORTAR MEMOS
            if import_memos:
                for memo_id, memo_text in pkg_memos.items():
                    target = memo_id
                    if target in docs_to_import or target in codes_to_import:
                        target_project.memos_dict[memo_id] = memo_text
                        target_project.memo_manager.memos[memo_id] = memo_text

            # 3. IMPORTAR CÓDIGOS Y TEMAS
            for code in codes_to_import:
                if code not in pkg_codes:
                    continue
                
                pkg_code_data = pkg_codes[code]
                
                if code not in target_project.codes_dict:
                    target_project.codes_dict[code] = {
                        "hexcolor": pkg_code_data.get("hexcolor", "#5d9bd3"),
                        "memo": pkg_code_data.get("memo", ""),
                        "fragments": {}
                    }
                    
                target_code_data = target_project.codes_dict[code]
                
                for theme_name, theme_data in pkg_themes.items():
                    if code in theme_data.get("codes", []):
                        if theme_name not in target_project.themes_dict:
                            target_project.add_theme(theme_name, theme_data.get("memo", ""))
                        if code not in target_project.themes_dict[theme_name]["codes"]:
                            target_project.themes_dict[theme_name]["codes"].append(code)
                
                # 4. FUSIONAR FRAGMENTOS
                if import_fragments:
                    pkg_fragments = pkg_code_data.get("fragments", {})
                    for doc in docs_to_import:
                        if doc in pkg_fragments:
                            if doc not in target_code_data["fragments"]:
                                target_code_data["fragments"][doc] = []
                                
                            existing_frags = target_code_data["fragments"][doc]
                            for new_frag in pkg_fragments[doc]:
                                is_dup = any(f["start"] == new_frag["start"] and f["end"] == new_frag["end"] for f in existing_frags)
                                if not is_dup:
                                    existing_frags.append(new_frag)

            # 5. GUARDAR TODO EN DISCO
            target_project.save_project_data(
                documents=legacy_state.get("documents", []),
                highlights=legacy_state.get("highlights", {}),
                doc_groups=legacy_state.get("doc_groups"),
                themes=legacy_state.get("themes"),
                case_studies=legacy_state.get("case_studies")
            )
