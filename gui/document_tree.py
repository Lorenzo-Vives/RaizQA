from PySide6.QtWidgets import QTreeWidget, QAbstractItemView
from PySide6.QtCore import Qt


class DocumentTree(QTreeWidget):
    """Árbol de documentos con soporte de drag & drop para mover archivos y carpetas."""

    def __init__(self, drop_callback=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.drop_callback = drop_callback
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragDropMode(QAbstractItemView.InternalMove)

    def dropEvent(self, event):
        super().dropEvent(event)
        if callable(self.drop_callback):
            self.drop_callback()
