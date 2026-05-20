import os

class SearchManager:
    """Maneja la lógica de búsqueda global del proyecto."""

    @staticmethod
    def run_global_search(term, project, codes, memo_manager):
        """
        Realiza una búsqueda del término en documentos, códigos y memos.
        Devuelve un diccionario con los resultados.
        """
        if not term:
            return None

        term_lower = term.lower()
        doc_matches = []
        code_matches = []
        memo_matches = []
        search_matches = []

        # 1. Buscar en documentos
        if project:
            for doc_name in project.list_documents():
                if SearchManager._is_image(doc_name):
                    continue
                try:
                    text = project.read_document(doc_name)
                    if term_lower in text.lower():
                        doc_matches.append(doc_name)
                        
                        text_lower = text.lower()
                        start = 0
                        while True:
                            idx = text_lower.find(term_lower, start)
                            if idx == -1:
                                break
                            search_matches.append({
                                "doc": doc_name, 
                                "start": idx, 
                                "length": len(term)
                            })
                            start = idx + len(term)
                except Exception:
                    continue

        # 2. Buscar en nombres de códigos
        for code_name in codes.keys():
            if term_lower in code_name.lower():
                code_matches.append(code_name)

        # 3. Buscar en memos
        if memo_manager:
            for code_name, memo_text in memo_manager.memos.items():
                if term_lower in code_name.lower() or term_lower in (memo_text or "").lower():
                    if code_name not in memo_matches:
                        memo_matches.append(code_name)

        return {
            "term": term,
            "search_matches": search_matches,
            "doc_matches": doc_matches,
            "code_matches": code_matches,
            "memo_matches": memo_matches
        }

    @staticmethod
    def _is_image(doc_name):
        ext = os.path.splitext(doc_name)[1].lower()
        return ext in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff"}
