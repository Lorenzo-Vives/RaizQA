import sys
import os
from PySide6.QtWidgets import QApplication
from gui.main_window import RaizQAGUI
from gui.dialogs.readme_dialog import ReadmeDialog

# Asegura que el directorio raíz esté en sys.path (por si se ejecuta desde fuera)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Pantalla de bienvenida
    readme = ReadmeDialog()
    readme.exec()

    # Ventana principal
    window = RaizQAGUI()
    window.show()

    sys.exit(app.exec())
