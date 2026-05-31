import os
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication

"""Configuraciones de tema compartidas entre la ventana principal y los diálogos."""

LIGHT_THEME = {
    "window_bg": "#f7f7f9",
    "panel_bg": "#f0f0f3",
    "text_bg": "#ffffff",
    "text_fg": "#1a1a1a",
    "muted_text": "#6c6c6c",
    "border": "#d6d6d6",
    "selection": "#1976d2",
    "list_bg": "#ffffff",
    "list_fg": "#1c1c1c",
    "tree_bg": "#ffffff",
    "tree_fg": "#1c1c1c",
    "button_bg": "#ffffff",
    "button_fg": "#1c1c1c",
}

DARK_THEME = {
    "window_bg": "#121212",
    "panel_bg": "#1e1e1e",
    "text_bg": "#1a1a1a",
    "text_fg": "#f1f1f1",
    "muted_text": "#a0a4b0",
    "border": "#2f2f2f",
    "selection": "#64b5f6",
    "list_bg": "#1b1b1b",
    "list_fg": "#f0f0f0",
    "tree_bg": "#1b1b1b",
    "tree_fg": "#f0f0f0",
    "button_bg": "#252525",
    "button_fg": "#f0f0f0",
}


def get_theme(is_dark=False):
    """Devuelve el diccionario de colores para el modo solicitado."""
    return DARK_THEME if is_dark else LIGHT_THEME


_qss_cache = None

def apply_theme_to_window(window, is_dark_mode):
    """Aplica la paleta y los estilos QSS a la ventana."""
    global _qss_cache
    
    theme = get_theme(is_dark_mode)
    highlight_text = "#0b0b0b" if is_dark_mode else "#ffffff"

    # 1. Aplicar QPalette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(theme["window_bg"]))
    palette.setColor(QPalette.Base, QColor(theme["text_bg"]))
    palette.setColor(QPalette.AlternateBase, QColor(theme["panel_bg"]))
    palette.setColor(QPalette.Text, QColor(theme["text_fg"]))
    palette.setColor(QPalette.Button, QColor(theme["button_bg"]))
    palette.setColor(QPalette.ButtonText, QColor(theme["button_fg"]))
    palette.setColor(QPalette.Highlight, QColor(theme["selection"]))
    palette.setColor(QPalette.HighlightedText, QColor(highlight_text))

    app = QApplication.instance()
    if app:
        app.setPalette(palette)
    window.setPalette(palette)

    # 2. Cargar y formatear QSS
    if _qss_cache is None:
        qss_path = os.path.join(os.path.dirname(__file__), "styles.qss")
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                _qss_cache = f.read()
        except Exception as e:
            print(f"Error loading styles.qss: {e}")
            _qss_cache = ""

    # Usamos formateo seguro. 
    # El archivo de estilos utiliza variables como {window_bg}.
    if _qss_cache:
        formatted_qss = _qss_cache.format(**theme, highlight_text=highlight_text)
        window.setStyleSheet(formatted_qss)
