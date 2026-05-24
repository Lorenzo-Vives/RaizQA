import os
from PySide6.QtCore import QObject, Signal

class DocumentEditorController(QObject):
    """Controlador dedicado para manejar el estado de edición del QTextEdit."""
    
    # Señal que se emite cuando el usuario confirma los cambios
    signal_save_requested = Signal(str, str)  # (doc_name, new_text)

    def __init__(self, text_area, btn_edit, btn_save, btn_cancel):
        super().__init__()
        self.text_area = text_area
        self.btn_edit = btn_edit
        self.btn_save = btn_save
        self.btn_cancel = btn_cancel

        self.current_doc = None
        self.original_text = ""
        self.is_editing = False

        # Conectar los botones a los métodos locales
        self.btn_edit.clicked.connect(self.start_editing)
        self.btn_save.clicked.connect(self.save_changes)
        self.btn_cancel.clicked.connect(self.cancel_changes)

        self._update_ui_state()

    def load_document(self, doc_name, text):
        """Se llama al cargar un nuevo documento. Reinicia el estado de edición."""
        self.current_doc = doc_name
        self.original_text = text
        self.is_editing = False
        self.text_area.setReadOnly(True)
        self._update_ui_state()

    def start_editing(self):
        """Habilita la edición en el QTextEdit."""
        if not self.current_doc: return
        self.is_editing = True
        self.text_area.setReadOnly(False)
        self.text_area.setFocus()
        self._update_ui_state()

    def save_changes(self):
        """Guarda los cambios emitiendo la señal hacia el backend."""
        if not self.is_editing: return
        new_text = self.text_area.toPlainText()
        
        # Si no hubo cambios reales, simplemente cancelamos el modo edición
        if new_text != self.original_text:
            self.signal_save_requested.emit(self.current_doc, new_text)
            self.original_text = new_text
            
        self.is_editing = False
        self.text_area.setReadOnly(True)
        self._update_ui_state()

    def cancel_changes(self):
        """Descarta los cambios y restaura el texto original."""
        if not self.is_editing: return
        self.text_area.setPlainText(self.original_text)
        self.is_editing = False
        self.text_area.setReadOnly(True)
        self._update_ui_state()

    def _update_ui_state(self):
        """Muestra u oculta los botones dependiendo del estado."""
        has_doc = self.current_doc is not None
        self.btn_edit.setVisible(has_doc and not self.is_editing)
        self.btn_save.setVisible(self.is_editing)
        self.btn_cancel.setVisible(self.is_editing)