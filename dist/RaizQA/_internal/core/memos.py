import json
import os

class MemoManager:
    def __init__(self, project_dir):
        """
        Administra los memos de un proyecto.
        Guarda todos los memos en un archivo JSON dentro del proyecto.
        """
        self.project_dir = project_dir
        self.memo_file = os.path.join(project_dir, "memos.json")
        self.memos = self.load_memos()

    def load_memos(self):
        """Carga los memos desde el archivo JSON (si existe)."""
        if os.path.exists(self.memo_file):
            try:
                with open(self.memo_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("ADVERTENCIA: memos.json no se pudo leer; se creará una copia vacía.")
                return {}
        return {}

    def save_memos(self):
        """Guarda todos los memos en el archivo JSON."""
        try:
            with open(self.memo_file, "w", encoding="utf-8") as f:
                json.dump(self.memos, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"ERROR: no se pudieron guardar los memos ({e})")

    def get_memo(self, code_label):
        """Devuelve el texto del memo asociado a un código (si existe)."""
        return self.memos.get(code_label, "")

    def add_or_update_memo(self, code_label, text):
        """Agrega o actualiza un memo asociado a un código."""
        self.memos[code_label] = text
        self.save_memos()

    def delete_memo(self, code_label):
        """Elimina un memo de un código."""
        if code_label in self.memos:
            del self.memos[code_label]
            self.save_memos()
