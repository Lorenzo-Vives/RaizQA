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
