import os
import tempfile
import zipfile
import shutil
import json
from datetime import datetime

from core.project import Project
from core.export_manager import ExportManager


class MergeManager:
    """Gestor para la combinación (merge) de dos proyectos .rqa"""

    @staticmethod
    def merge_projects(target_project: Project, rqa_path: str, settings: dict) -> dict:
        """
        Combina un proyecto importado (.rqa) en el proyecto destino (abierto).
            dict: Resumen de la fusión (documentos, códigos, fragmentos, etc.)
        """
        # 1. Crear respaldo del proyecto actual antes de proceder (versionado
        # con timestamp para no pisar el respaldo de un merge anterior).
        backup_name = f"{target_project.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.rqa"
        backup_path = os.path.join(target_project.base_path, backup_name)
        ExportManager.export_project_to_rqa(target_project.path, backup_path)

        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(rqa_path, 'r') as zip_ref:
                zip_ref.extract("metadata.json", temp_dir)

            metadata_path = os.path.join(temp_dir, "metadata.json")
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                imported_name = metadata.get("name")

            if imported_name == target_project.name:
                raise ValueError("No se puede combinar un proyecto consigo mismo.")

            extract_path = os.path.join(temp_dir, imported_name)
            os.makedirs(extract_path, exist_ok=True)

            with zipfile.ZipFile(rqa_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)

            # Cargar el proyecto importado con la arquitectura de managers actual
            imported_project = Project(imported_name, temp_dir)

            docs_added, docs_skipped = MergeManager._merge_documents(
                target_project, imported_project, settings
            )
            MergeManager._merge_doc_groups(target_project, imported_project, settings)
            codes_summary = MergeManager._merge_codes(target_project, imported_project, settings)
            MergeManager._merge_themes(target_project, imported_project, settings)
            MergeManager._merge_memos(target_project, imported_project, settings)
            case_studies_added = MergeManager._merge_case_studies(target_project, imported_project)
            entries_added = MergeManager._merge_diary(target_project, imported_project)

            # Guardado explícito único al final de la fusión completa
            target_project.save_state()

            return {
                "backup_path": backup_path,
                "documents_added": docs_added,
                "documents_skipped": docs_skipped,
                "codes_added": codes_summary["codes_added"],
                "codes_merged": codes_summary["codes_merged"],
                "fragments_added": codes_summary["fragments_added"],
                "fragments_duplicated": codes_summary["fragments_duplicated"],
                "case_studies_added": case_studies_added,
                "diary_entries_added": entries_added,
            }

    # ------------------------------------------------------------------
    # Documentos
    # ------------------------------------------------------------------
    @staticmethod
    def _merge_documents(target_project: Project, imported_project: Project, settings: dict):
        target_names = {d["name"] for d in target_project.doc_manager.documents}
        added, skipped = [], []

        for doc in imported_project.doc_manager.list_documents():
            src_path = imported_project.doc_manager.get_document_path(doc)
            if not os.path.exists(src_path):
                continue

            doc_exists = doc in target_names
            if doc_exists and settings.get("dont_import_existing_docs", True):
                skipped.append(doc)
                continue

            target_path = target_project.doc_manager.get_document_path(doc)
            old_text = target_project.doc_manager.get_document_text(doc) if doc_exists else None
            shutil.copy2(src_path, target_path)

            new_text = target_project.doc_manager.read_document(doc)
            target_project.doc_manager.text_cache[doc] = new_text

            if doc_exists:
                # Documento sobrescrito: resincronizar offsets de fragmentos existentes
                # con el nuevo texto, igual que hace update_document_text.
                if old_text and old_text != new_text:
                    target_project.code_manager.sync_fragments_for_document(doc, old_text, new_text)
            else:
                target_project.doc_manager.register_document(doc)
                target_names.add(doc)

            added.append(doc)

        return added, skipped

    # ------------------------------------------------------------------
    # Grupos de documentos
    # ------------------------------------------------------------------
    @staticmethod
    def _merge_doc_groups(target_project: Project, imported_project: Project, settings: dict):
        target_groups = target_project.group_manager.groups
        imported_groups = imported_project.group_manager.groups

        for group_name, docs in imported_groups.items():
            if group_name == "__root__":
                for d in docs:
                    if d not in target_groups["__root__"]:
                        target_groups["__root__"].append(d)
                continue

            target_group_name = group_name
            if not settings.get("merge_document_groups", True):
                # Si no combinamos, renombramos si existe para evitar colisión
                count = 1
                while target_group_name in target_groups:
                    target_group_name = f"{group_name} ({count})"
                    count += 1

            target_groups.setdefault(target_group_name, [])
            for d in docs:
                if d not in target_groups[target_group_name]:
                    target_groups[target_group_name].append(d)

        target_project.group_manager.groups = target_groups

    # ------------------------------------------------------------------
    # Códigos y fragmentos (incluye jerarquía padre/hijo y fragmentos de imagen)
    # ------------------------------------------------------------------
    @staticmethod
    def _merge_codes(target_project: Project, imported_project: Project, settings: dict) -> dict:
        target_codes = target_project.code_manager.codes_dict
        imported_codes = imported_project.code_manager.codes_dict
        summary = {"codes_added": [], "codes_merged": [], "fragments_added": 0, "fragments_duplicated": 0}

        # 1. Crear códigos faltantes / resolver conflicto de color y memo
        for code_name, code_obj in imported_codes.items():
            if code_name not in target_codes:
                target_project.code_manager.add_code(code_name, code_obj.hexcolor, code_obj.memo)
                summary["codes_added"].append(code_name)
            else:
                summary["codes_merged"].append(code_name)
                if settings.get("keep_code_color_from") == "imported":
                    target_codes[code_name].hexcolor = code_obj.hexcolor
                if settings.get("keep_code_memos_from") == "imported":
                    target_codes[code_name].memo = code_obj.memo

        # 2. Reconstruir jerarquía padre/hijo del proyecto importado
        # (MAXQDA fusiona el sistema de códigos como árbol, no como lista plana)
        for code_name, code_obj in imported_codes.items():
            if (
                code_obj.parent
                and code_obj.parent in target_codes
                and target_codes[code_name].parent is None
            ):
                target_codes[code_name].parent = code_obj.parent
                if code_name not in target_codes[code_obj.parent].children:
                    target_codes[code_obj.parent].children.append(code_name)

        # 3. Fusionar fragmentos, deduplicando por igualdad de dataclass Fragment
        # (incluye type + rect/image_size para no colisionar fragmentos de imagen
        # con fragmentos de texto que compartan offsets por coincidencia).
        for code_name, code_obj in imported_codes.items():
            target_code = target_codes[code_name]
            for doc_name, fragments in code_obj.fragments.items():
                existing = target_code.fragments.setdefault(doc_name, [])
                for frag in fragments:
                    if frag in existing:
                        summary["fragments_duplicated"] += 1
                        continue
                    existing.append(frag)
                    summary["fragments_added"] += 1

        return summary

    # ------------------------------------------------------------------
    # Temas / categorías
    # ------------------------------------------------------------------
    @staticmethod
    def _merge_themes(target_project: Project, imported_project: Project, settings: dict):
        imported_themes = imported_project.theme_manager.themes_dict
        for theme_name, theme_obj in imported_themes.items():
            if theme_name not in target_project.theme_manager.themes_dict:
                target_project.theme_manager.add_theme(theme_name, theme_obj.memo)
            elif settings.get("keep_code_memos_from") == "imported":
                # Usamos la misma regla que para memos de códigos
                target_project.theme_manager.themes_dict[theme_name].memo = theme_obj.memo

            for code in theme_obj.codes:
                target_project.theme_manager.add_code_to_theme(theme_name, code)

    # ------------------------------------------------------------------
    # Memos generales (proyecto, códigos, documentos)
    # ------------------------------------------------------------------
    @staticmethod
    def _merge_memos(target_project: Project, imported_project: Project, settings: dict):
        target_memos = target_project.memo_manager.memos
        imported_memos = imported_project.memo_manager.memos

        for memo_id, text in imported_memos.items():
            if memo_id not in target_memos:
                target_memos[memo_id] = text
            elif memo_id in ("__project_memo__", "ProjectMemo"):
                if settings.get("keep_project_memo_from") == "imported":
                    target_memos[memo_id] = text
            else:
                if settings.get("keep_code_memos_from") == "imported":
                    target_memos[memo_id] = text

    # ------------------------------------------------------------------
    # Estudios de caso
    # ------------------------------------------------------------------
    @staticmethod
    def _merge_case_studies(target_project: Project, imported_project: Project) -> int:
        target_cs = target_project.case_study_manager.case_studies
        existing_names = {cs.get("name") for cs in target_cs}
        added = 0
        for cs in imported_project.case_study_manager.get_all():
            if cs.get("name") not in existing_names:
                target_cs.append(cs)
                existing_names.add(cs.get("name"))
                added += 1
        return added

    # ------------------------------------------------------------------
    # Diario de codificación
    # ------------------------------------------------------------------
    @staticmethod
    def _merge_diary(target_project: Project, imported_project: Project) -> int:
        target_diary = target_project.diary_manager
        imported_diary = imported_project.diary_manager

        combined_entries = target_diary.entries + imported_diary.entries
        unique_entries = []
        seen = set()
        for entry in combined_entries:
            # Usamos author, date y message como firma única
            signature = (entry.get("author", ""), entry.get("date", ""), entry.get("message", ""))
            if signature not in seen:
                seen.add(signature)
                unique_entries.append(entry)

        added = max(len(unique_entries) - len(target_diary.entries), 0)

        # Ordenar cronológicamente
        unique_entries.sort(key=lambda x: x.get("date", ""))
        target_diary.entries = unique_entries
        target_diary.save_diary()
        return added