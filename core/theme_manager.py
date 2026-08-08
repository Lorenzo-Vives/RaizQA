import logging
from typing import Dict, List, Optional, Tuple


from core.data_models import Theme


logger = logging.getLogger(__name__)



# ----------------------------------------------------------------------
# Gestor de Temas
# ----------------------------------------------------------------------
class ThemeManager:
    """
    Gestiona el conjunto de temas y su relación con los códigos.
    """
    def __init__(self):
        self.themes_dict: Dict[str, Theme] = {}

    def add_theme(self, theme_name: str, memo: str = ""):
        if theme_name not in self.themes_dict:
            self.themes_dict[theme_name] = Theme(memo=memo)

    def delete_theme(self, theme_name: str):
        self.themes_dict.pop(theme_name, None)

    def add_code_to_theme(self, theme_name: str, code_name: str):
        self.add_theme(theme_name)
        if code_name not in self.themes_dict[theme_name].codes:
            self.themes_dict[theme_name].codes.append(code_name)

    def remove_code_from_theme(self, theme_name: str, code_name: str):
        if (
            theme_name in self.themes_dict
            and code_name in self.themes_dict[theme_name].codes
        ):
            self.themes_dict[theme_name].codes.remove(code_name)

    def remove_code_from_all_themes(self, code_name: str):
        for theme in self.themes_dict.values():
            if code_name in theme.codes:
                theme.codes.remove(code_name)

    def rename_code_in_themes(self, old_name: str, new_name: str):
        for theme in self.themes_dict.values():
            for i, name in enumerate(theme.codes):
                if name == old_name:
                    theme.codes[i] = new_name

    def get_all_themes(self) -> Dict[str, dict]:
        return {k: v.to_dict() for k, v in self.themes_dict.items()}

    def load_themes(self, themes_dict: Dict[str, dict]):
        self.themes_dict = {k: Theme.from_dict(v) for k, v in themes_dict.items()}

