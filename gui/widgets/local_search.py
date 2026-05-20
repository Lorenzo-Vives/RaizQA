from PySide6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QLabel, QPushButton, QTextEdit
from PySide6.QtCore import Qt, QRegularExpression, Signal
from PySide6.QtGui import QTextCursor, QTextCharFormat, QColor

class LocalSearchWidget(QFrame):
    """
    Componente modular para la búsqueda local dentro de un documento de texto.
    Encapsula la UI de búsqueda, la navegación y la generación de resaltados.
    """
    # Emitimos esta señal con la lista de selecciones para que la ventana principal las pinte
    selections_updated = Signal(list) 
    closed = Signal()

    def __init__(self, text_area, parent=None):
        super().__init__(parent)
        self.text_area = text_area
        self.setObjectName("TabBar")
        self.setFixedHeight(34)
        
        # Variables de estado internas
        self._local_matches = []
        self._current_ls_index = -1
        self.theme = {}
        self.is_dark_mode = False

        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(6)

        self.ls_input = QLineEdit()
        self.ls_input.setPlaceholderText("Buscar en el documento...")
        self.ls_input.textChanged.connect(self.run_search)
        self.ls_input.returnPressed.connect(self.next_match)
        layout.addWidget(self.ls_input)

        self.lbl_count = QLabel("0/0")
        layout.addWidget(self.lbl_count)

        self.btn_prev = QPushButton("↑")
        self.btn_prev.setObjectName("SearchNavButton")
        self.btn_prev.setFixedSize(24, 24)
        self.btn_prev.clicked.connect(self.prev_match)
        layout.addWidget(self.btn_prev)

        self.btn_next = QPushButton("↓")
        self.btn_next.setObjectName("SearchNavButton")
        self.btn_next.setFixedSize(24, 24)
        self.btn_next.clicked.connect(self.next_match)
        layout.addWidget(self.btn_next)

        self.btn_close = QPushButton("✖")
        self.btn_close.setObjectName("GhostButton")
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.clicked.connect(self.close_search)
        layout.addWidget(self.btn_close)

    def update_theme(self, theme_dict, is_dark):
        """Recibe el tema desde la ventana principal para mantener coherencia visual."""
        self.theme = theme_dict
        self.is_dark_mode = is_dark
        if self.isVisible():
            self._generate_highlights()

    def run_search(self):
        """Ejecuta la búsqueda con Regex y guarda las posiciones."""
        term = self.ls_input.text()
        self._local_matches = []
        
        if not term:
            self.lbl_count.setText("0/0")
            self.selections_updated.emit([]) # Limpiar resaltados
            return

        doc_text = self.text_area.toPlainText()
        
        # Búsqueda insensible a mayúsculas/minúsculas
        regex = QRegularExpression(QRegularExpression.escape(term), QRegularExpression.CaseInsensitiveOption)
        iterator = regex.globalMatch(doc_text)
        
        while iterator.hasNext():
            match = iterator.next()
            self._local_matches.append({
                "start": match.capturedStart(),
                "end": match.capturedEnd()
            })

        if self._local_matches:
            self._current_ls_index = 0
            self._generate_highlights()
        else:
            self._current_ls_index = -1
            self.lbl_count.setText("0/0")
            self.selections_updated.emit([])

    def _generate_highlights(self):
        """Crea los objetos QTextEdit.ExtraSelection y los emite."""
        if not self._local_matches or not self.theme:
            self.selections_updated.emit([])
            return

        selections = []
        inactive_color = QColor(self.theme.get("border", "#cccccc"))
        inactive_color.setAlpha(100)
        active_color = QColor(self.theme.get("selection", "#0078d7")) 

        for i, match in enumerate(self._local_matches):
            selection = QTextEdit.ExtraSelection()
            cursor = self.text_area.textCursor()
            cursor.setPosition(match["start"])
            cursor.setPosition(match["end"], QTextCursor.KeepAnchor)
            selection.cursor = cursor
            
            fmt = QTextCharFormat()
            if i == self._current_ls_index:
                fmt.setBackground(active_color)
                fmt.setForeground(QColor("#ffffff" if self.is_dark_mode else "#000000"))
                # Mover el scroll de la pantalla hacia el match activo
                self.text_area.setTextCursor(cursor)
            else:
                fmt.setBackground(inactive_color)
                
            selection.format = fmt
            selections.append(selection)

        self.lbl_count.setText(f"{self._current_ls_index + 1}/{len(self._local_matches)}")
        
        # Emitimos los resaltados para que la ventana principal los combine
        self.selections_updated.emit(selections)

    def next_match(self):
        if self._local_matches:
            self._current_ls_index = (self._current_ls_index + 1) % len(self._local_matches)
            self._generate_highlights()

    def prev_match(self):
        if self._local_matches:
            self._current_ls_index = (self._current_ls_index - 1) % len(self._local_matches)
            self._generate_highlights()

    def show_search(self):
        self.setVisible(True)
        self.ls_input.setFocus()
        self.ls_input.selectAll()
        self.run_search()

    def close_search(self):
        self.setVisible(False)
        self.ls_input.clear()
        self.selections_updated.emit([]) # Al cerrar, limpiar la pantalla
        self.closed.emit()