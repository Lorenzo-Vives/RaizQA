class MemoManager:
    def __init__(self, memos_dict=None):
        """
        Administra los memos de un proyecto en memoria.
        El guardado real lo maneja la clase Project.
        """
        self.memos = memos_dict if memos_dict is not None else {}

    def get_memo(self, code_label):
        """Devuelve el texto del memo asociado a un código (si existe)."""
        return self.memos.get(code_label, "")

    def add_or_update_memo(self, code_label, text):
        """Agrega o actualiza un memo asociado a un código."""
        self.memos[code_label] = text

    def delete_memo(self, code_label):
        """Elimina un memo de un código."""
        if code_label in self.memos:
            del self.memos[code_label]

    def rename_memo(self, old_label, new_label):
        if old_label == new_label or old_label not in self.memos:
            return
        self.memos[new_label] = self.memos.pop(old_label)
