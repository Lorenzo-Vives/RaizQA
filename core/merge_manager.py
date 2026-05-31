import os
import tempfile
import zipfile
import shutil
import json
from core.project import Project
from core.export_manager import ExportManager

class MergeManager:
    """Gestor para la combinación (merge) de dos proyectos .rqa."""

    @staticmethod
    def merge_projects(target_project: Project, rqa_path: str, settings: dict) -> bool:
        """
        Combina un proyecto importado (.rqa) en el proyecto destino (abierto).
        
        Args:
            target_project (Project): El proyecto actualmente abierto.
            rqa_path (str): Ruta al archivo .rqa a importar.
            settings (dict): Diccionario con la configuración:
                - keep_project_memo_from: "open" | "imported"
                - keep_code_memos_from: "open" | "imported"
                - dont_import_existing_docs: bool
                - merge_document_groups: bool
        """
        # 1. Crear respaldo del proyecto actual antes de proceder
        backup_path = os.path.join(target_project.base_path, f"{target_project.name}_backup_antes_de_combinar.rqa")
        ExportManager.export_project_to_rqa(target_project.path, backup_path)
        
        target_state = target_project.load_project_data()
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(rqa_path, 'r') as zip_ref:
                    zip_ref.extract("metadata.json", temp_dir)
                    
                metadata_path = os.path.join(temp_dir, "metadata.json")
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    imported_name = metadata.get("name")
                    
                extract_path = os.path.join(temp_dir, imported_name)
                os.makedirs(extract_path, exist_ok=True)
                
                with zipfile.ZipFile(rqa_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                    
                # Cargar el proyecto importado
                imported_project = Project(imported_name, temp_dir)
                imported_state = imported_project.load_project_data()
                
                # --- Mezclar Documentos ---
                imported_docs = imported_state.get("documents", [])
                target_docs = target_state.get("documents", [])
                
                for doc in imported_docs:
                    src_path = os.path.join(imported_project.documents_path, doc)
                    if not os.path.exists(src_path):
                        continue
                        
                    doc_exists = doc in target_docs
                    if settings.get("dont_import_existing_docs", True) and doc_exists:
                        continue # No sobrescribir
                        
                    # Copiar archivo y registrar
                    target_path = os.path.join(target_project.documents_path, doc)
                    shutil.copy2(src_path, target_path)
                    if not doc_exists:
                        target_project._register_document(doc)
                        target_docs.append(doc)
                        
                # --- Mezclar Grupos de Documentos ---
                target_groups = target_state.get("doc_groups", {"__root__": []})
                imported_groups = imported_state.get("doc_groups", {"__root__": []})
                
                for group_name, docs in imported_groups.items():
                    if group_name == "__root__":
                        for d in docs:
                            if d not in target_groups["__root__"]:
                                target_groups["__root__"].append(d)
                    else:
                        target_group_name = group_name
                        if not settings.get("merge_document_groups", True):
                            # Si no combinamos, renombramos si existe para evitar colisión
                            count = 1
                            while target_group_name in target_groups:
                                target_group_name = f"{group_name} ({count})"
                                count += 1
                        
                        if target_group_name not in target_groups:
                            target_groups[target_group_name] = []
                            
                        for d in docs:
                            if d not in target_groups[target_group_name]:
                                target_groups[target_group_name].append(d)
                                
                # --- Mezclar Códigos y Fragmentos ---
                imported_codes = imported_state.get("codes_dict", {})
                for code_name, code_data in imported_codes.items():
                    if code_name not in target_project.codes_dict:
                        target_project.codes_dict[code_name] = {
                            "hexcolor": code_data.get("hexcolor", "#5d9bd3"),
                            "memo": code_data.get("memo", ""),
                            "fragments": {}
                        }
                    else:
                        # Conflicto: decidir memo según configuración
                        if settings.get("keep_code_memos_from") == "imported":
                            target_project.codes_dict[code_name]["memo"] = code_data.get("memo", "")
                            
                    # Mezclar fragmentos
                    target_code_data = target_project.codes_dict[code_name]
                    for doc_name, fragments in code_data.get("fragments", {}).items():
                        if doc_name not in target_code_data["fragments"]:
                            target_code_data["fragments"][doc_name] = []
                            
                        existing_frags = target_code_data["fragments"][doc_name]
                        for new_frag in fragments:
                            is_dup = any(f["start"] == new_frag["start"] and f["end"] == new_frag["end"] for f in existing_frags)
                            if not is_dup:
                                existing_frags.append(new_frag)

                # --- Mezclar Temas ---
                imported_themes = imported_state.get("themes_dict", {})
                for theme_name, theme_data in imported_themes.items():
                    if theme_name not in target_project.themes_dict:
                        target_project.add_theme(theme_name, theme_data.get("memo", ""))
                    else:
                        if settings.get("keep_code_memos_from") == "imported": # Usamos la misma regla para temas
                            target_project.themes_dict[theme_name]["memo"] = theme_data.get("memo", "")
                            
                    for code in theme_data.get("codes", []):
                        if code not in target_project.themes_dict[theme_name]["codes"]:
                            target_project.themes_dict[theme_name]["codes"].append(code)

                # --- Mezclar Memos Generales (memos_dict) ---
                imported_memos = imported_state.get("memos_dict", {})
                for memo_id, text in imported_memos.items():
                    if memo_id not in target_project.memos_dict:
                        target_project.memos_dict[memo_id] = text
                    else:
                        # Determinar quién gana
                        # Si es el memo del proyecto (asumiendo "__project_memo__" o id del proyecto)
                        # o si son memos de documentos/códigos.
                        # Para simplificar, si el memo es "__project_memo__" o igual al nombre del proyecto
                        if memo_id in ("__project_memo__", "ProjectMemo"):
                            if settings.get("keep_project_memo_from") == "imported":
                                target_project.memos_dict[memo_id] = text
                        else:
                            if settings.get("keep_code_memos_from") == "imported":
                                target_project.memos_dict[memo_id] = text
                                
                target_project.memo_manager.memos = target_project.memos_dict

                # --- Mezclar Diario de Codificación ---
                target_diary = target_project.diary_manager
                imported_diary = imported_project.diary_manager
                
                # Combinamos y eliminamos duplicados
                combined_entries = target_diary.entries + imported_diary.entries
                unique_entries = []
                seen = set()
                for entry in combined_entries:
                    # Usamos author, date y message como firma única
                    signature = (entry.get("author", ""), entry.get("date", ""), entry.get("message", ""))
                    if signature not in seen:
                        seen.add(signature)
                        unique_entries.append(entry)
                        
                # Ordenar cronológicamente
                unique_entries.sort(key=lambda x: x.get("date", ""))
                target_diary.entries = unique_entries
                target_diary.save_diary()

                # Guardar todo en disco
                target_project.save_project_data(
                    documents=target_docs,
                    highlights=target_state.get("highlights", {}),
                    doc_groups=target_groups,
                    themes=target_state.get("themes")
                )
                
                return True
        except Exception as e:
            print(f"Error durante el merge: {e}")
            raise e
