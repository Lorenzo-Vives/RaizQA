import os
import json
from datetime import datetime

class DiaryManager:
    """
    Gestor independiente para el diario de codificación.
    Maneja la persistencia en formato JSON y el historial de autores.
    """
    def __init__(self, project_path):
        self.project_path = project_path
        self.diary_file = os.path.join(project_path, "diary.json")
        self.entries = []
        self.authors = set()
        self.load_diary()

    def load_diary(self):
        """Carga el diario desde el JSON. Si no existe, inicia vacío."""
        if not os.path.exists(self.diary_file):
            return

        try:
            with open(self.diary_file, 'r', encoding='utf-8') as f:
                self.entries = json.load(f)
                # Extraer todos los autores únicos para el autocompletado
                for entry in self.entries:
                    if "author" in entry:
                        self.authors.add(entry["author"])
        except Exception as e:
            print(f"Error al cargar el diario JSON: {e}")

    def add_entry(self, author, message):
        """Crea una nueva entrada con fecha exacta y la guarda en disco."""
        entry = {
            "author": author.strip(),
            "date": datetime.now().isoformat(),
            "message": message.strip()
        }
        self.entries.append(entry)
        self.authors.add(entry["author"])
        self.save_diary()

    def save_diary(self):
        """Persiste las entradas en el disco en formato JSON."""
        try:
            with open(self.diary_file, 'w', encoding='utf-8') as f:
                json.dump(self.entries, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error al guardar el diario JSON: {e}")

    def get_entries(self):
        """Retorna las entradas de más antigua a más reciente."""
        return self.entries

    def get_authors(self):
        """Retorna una lista ordenada de los autores históricos."""
        return sorted(list(self.authors))