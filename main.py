import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from gui.main_window import RaizQAGUI
from gui.dialogs.readme_dialog import ReadmeDialog

# Asegura que el directorio raíz esté en sys.path (por si se ejecuta desde fuera)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # App/window icon (works in dev and PyInstaller)
    base_path = getattr(sys, "_MEIPASS", BASE_DIR)
    icon_path = os.path.join(base_path, "logo1.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Pantalla de bienvenida
    readme = ReadmeDialog()
    readme.exec()

    # Ventana principal
    window = RaizQAGUI()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    window.show()

    sys.exit(app.exec())
