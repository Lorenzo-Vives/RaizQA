import os
import tempfile
import zipfile
import shutil
import json
import copy
from core.project import Project
from core.export_manager import ExportManager
from core.fragment_utils import merge_unique_fragments

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

                # Preparar el resultado en copias. El proyecto abierto no se
                # modifica hasta que toda la combinación haya sido validada.
                merged_codes = copy.deepcopy(target_project.codes_dict)
                merged_themes = copy.deepcopy(target_project.themes_dict)
                merged_memos = copy.deepcopy(target_project.memos_dict)
                
                # --- Mezclar Documentos ---
                imported_docs = imported_state.get("documents", [])
                target_docs = list(target_state.get("documents", []))
                document_copies = []
                
                for doc in imported_docs:
                    src_path = os.path.join(imported_project.documents_path, doc)
                    if not os.path.exists(src_path):
                        continue
                        
                    doc_exists = doc in target_docs
                    if settings.get("dont_import_existing_docs", True) and doc_exists:
                        continue # No sobrescribir
                        
                    target_path = os.path.join(target_project.documents_path, doc)
                    document_copies.append((src_path, target_path, doc))
                    if not doc_exists:
                        target_docs.append(doc)
                        
                # --- Mezclar Grupos de Documentos ---
                target_groups = copy.deepcopy(target_state.get("doc_groups", {"__root__": []}))
                target_groups.setdefault("__root__", [])
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
                new_code_names = set()
                for code_name, code_data in imported_codes.items():
                    if code_name not in merged_codes:
                        merged_codes[code_name] = {
                            "hexcolor": code_data.get("hexcolor", "#5d9bd3"),
                            "memo": code_data.get("memo", ""),
                            "fragments": {},
                            "parent": None,
                            "children": [],
                        }
                        new_code_names.add(code_name)
                    else:
                        # Conflicto: decidir memo según configuración
                        if settings.get("keep_code_memos_from") == "imported":
                            merged_codes[code_name]["memo"] = code_data.get("memo", "")

                    # Mezclar fragmentos
                    target_code_data = merged_codes[code_name]
                    target_code_data.setdefault("fragments", {})
                    target_code_data.setdefault("parent", None)
                    target_code_data.setdefault("children", [])
                    for doc_name, fragments in code_data.get("fragments", {}).items():
                        if doc_name not in target_code_data["fragments"]:
                            target_code_data["fragments"][doc_name] = []

                        existing_frags = target_code_data["fragments"][doc_name]
                        merge_unique_fragments(existing_frags, fragments)

                # Aplicar la jerarquía importada solo a códigos nuevos. Si un
                # nombre ya existía, prevalece la jerarquía del proyecto abierto.
                for code_name in new_code_names:
                    imported_parent = imported_codes[code_name].get("parent")
                    if imported_parent in merged_codes and imported_parent != code_name:
                        merged_codes[code_name]["parent"] = imported_parent
                MergeManager._normalize_code_hierarchy(merged_codes)

                # --- Mezclar Temas ---
                imported_themes = imported_state.get("themes_dict", {})
                for theme_name, theme_data in imported_themes.items():
                    if theme_name not in merged_themes:
                        merged_themes[theme_name] = {
                            "memo": theme_data.get("memo", ""),
                            "codes": [],
                        }
                    else:
                        if settings.get("keep_code_memos_from") == "imported": # Usamos la misma regla para temas
                            merged_themes[theme_name]["memo"] = theme_data.get("memo", "")

                    merged_themes[theme_name].setdefault("codes", [])

                    for code in theme_data.get("codes", []):
                        if code in merged_codes and code not in merged_themes[theme_name]["codes"]:
                            merged_themes[theme_name]["codes"].append(code)

                # --- Mezclar Memos Generales (memos_dict) ---
                imported_memos = imported_state.get("memos_dict", {})
                for memo_id, text in imported_memos.items():
                    if memo_id not in merged_memos:
                        merged_memos[memo_id] = text
                    else:
                        # Determinar quién gana
                        # Si es el memo del proyecto (asumiendo "__project_memo__" o id del proyecto)
                        # o si son memos de documentos/códigos.
                        # Para simplificar, si el memo es "__project_memo__" o igual al nombre del proyecto
                        if memo_id in ("__project_memo__", "ProjectMemo"):
                            if settings.get("keep_project_memo_from") == "imported":
                                merged_memos[memo_id] = text
                        else:
                            if settings.get("keep_code_memos_from") == "imported":
                                merged_memos[memo_id] = text

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

                # Confirmar archivos y estructuras solo después de calcular y
                # validar el resultado completo.
                MergeManager._copy_documents_with_rollback(
                    document_copies,
                    target_project,
                    temp_dir,
                )
                target_project.codes_dict = merged_codes
                target_project.themes_dict = merged_themes
                target_project.memos_dict = merged_memos
                target_project.memo_manager.memos = target_project.memos_dict
                target_diary.entries = unique_entries
                target_diary.authors = {
                    entry.get("author", "")
                    for entry in unique_entries
                    if entry.get("author")
                }
                target_diary.save_diary()

                # save_project_data normaliza desde themes_dict. No reutilizar
                # target_state["themes"], porque corresponde al estado anterior
                # al merge y eliminaría los temas recién incorporados.
                target_project.save_project_data(
                    documents=target_docs,
                    highlights=target_state.get("highlights", {}),
                    doc_groups=target_groups
                )
                
                return True
        except Exception as e:
            print(f"Error durante el merge: {e}")
            raise e

    @staticmethod
    def _normalize_code_hierarchy(codes):
        """Rebuild children from parent fields and break invalid parent chains."""
        for code_data in codes.values():
            code_data.setdefault("parent", None)
            code_data["children"] = []

        for code_name, code_data in codes.items():
            parent = code_data.get("parent")
            if parent not in codes or parent == code_name:
                code_data["parent"] = None
                continue

            seen = {code_name}
            cursor = parent
            while cursor:
                if cursor in seen:
                    code_data["parent"] = None
                    break
                seen.add(cursor)
                cursor = codes.get(cursor, {}).get("parent")

        for code_name, code_data in codes.items():
            parent = code_data.get("parent")
            if parent and code_name not in codes[parent]["children"]:
                codes[parent]["children"].append(code_name)

    @staticmethod
    def _copy_documents_with_rollback(document_copies, target_project, temp_dir):
        """Copy merge documents and restore prior files if a copy fails."""
        rollback_dir = os.path.join(temp_dir, "rollback")
        os.makedirs(rollback_dir, exist_ok=True)
        created_paths = []
        overwritten_paths = []
        metadata_backup = os.path.join(rollback_dir, "metadata.json")
        if os.path.exists(target_project.metadata_path):
            shutil.copy2(target_project.metadata_path, metadata_backup)

        try:
            for index, (src_path, target_path, doc_name) in enumerate(document_copies):
                if os.path.exists(target_path):
                    backup_path = os.path.join(rollback_dir, f"document_{index}")
                    shutil.copy2(target_path, backup_path)
                    overwritten_paths.append((backup_path, target_path))
                else:
                    created_paths.append(target_path)

                shutil.copy2(src_path, target_path)
                target_project._register_document(doc_name)
                target_project.texts_dict.pop(doc_name, None)
        except Exception:
            for path in created_paths:
                if os.path.exists(path):
                    os.remove(path)
            for backup_path, target_path in overwritten_paths:
                shutil.copy2(backup_path, target_path)
            if os.path.exists(metadata_backup):
                shutil.copy2(metadata_backup, target_project.metadata_path)
            raise
