from PySide6.QtWidgets import QProgressDialog
from PySide6.QtCore import Qt

class LoadingDialog(QProgressDialog):
    """
    Diálogo de carga indeterminado para operaciones en segundo plano.
    Bloquea la interacción con la ventana padre mientras está activo.
    """
    def __init__(self, title: str, message: str, parent=None):
        super().__init__(message, None, 0, 0, parent)
        self.setWindowTitle(title)
        self.setWindowModality(Qt.WindowModal)
        self.setCancelButton(None)
        self.setMinimum(0)
        self.setMaximum(0)
