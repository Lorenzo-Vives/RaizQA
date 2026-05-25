from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QComboBox, QScrollArea, QWidget, QFrame
)
from PySide6.QtCore import Qt, QTimer
from datetime import datetime

class DiaryDialog(QDialog):
    """Diálogo de scroll continuo para las entradas del diario de codificación."""
    
    def __init__(self, diary_manager, parent=None):
        super().__init__(parent)
        self.diary_manager = diary_manager
        self.setWindowTitle("📓 Diario de codificación")
        self.resize(650, 750)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        
        # 1. Área de Scroll (Feed de entradas)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.feed_widget = QWidget()
        self.feed_layout = QVBoxLayout(self.feed_widget)
        self.feed_layout.setAlignment(Qt.AlignTop)
        self.feed_layout.setSpacing(12)
        
        self.scroll_area.setWidget(self.feed_widget)
        main_layout.addWidget(self.scroll_area, 7) # Ocupa el 70% de la pantalla
        
        # 2. Área de nueva entrada (Input)
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background-color: palette(alternate-base);
                border: 1px solid palette(mid);
                border-radius: 8px;
            }
        """)
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(12, 12, 12, 12)
        input_layout.setSpacing(8)
        
        # Área de texto del mensaje (ahora va arriba)
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Escribe tu reflexión, nota metodológica o avance aquí...")
        self.message_input.setMaximumHeight(100)
        self.message_input.setStyleSheet("border: 1px solid palette(mid); border-radius: 4px;")
        input_layout.addWidget(self.message_input)
        
        # Barra inferior (Autor a la izquierda, Botón a la derecha)
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 0, 0, 0)
        
        # --- Sección del Autor ---
        lbl_author = QLabel("👤 Autor:")
        lbl_author.setStyleSheet("color: gray; font-weight: bold;")
        bottom_bar.addWidget(lbl_author)
        
        self.author_input = QComboBox()
        self.author_input.setEditable(True)
        self.author_input.setPlaceholderText("Tu nombre...")
        self.author_input.setFixedWidth(160) # ¡Aquí está la magia! Restringimos el tamaño
        
        # Cargar historial de autores
        authors = self.diary_manager.get_authors()
        if authors:
            self.author_input.addItems(authors)
            
        bottom_bar.addWidget(self.author_input)
        
        # --- Espaciador central ---
        bottom_bar.addStretch() 
        
        # --- Botón de enviar ---
        self.btn_submit = QPushButton("Añadir entrada")
        self.btn_submit.setCursor(Qt.PointingHandCursor)
        self.btn_submit.setFixedWidth(130)
        self.btn_submit.clicked.connect(self.submit_entry)
        bottom_bar.addWidget(self.btn_submit)
        
        input_layout.addLayout(bottom_bar)
        main_layout.addWidget(input_frame, 0) # El 0 evita que el input_frame intente estirarse verticalmente
        self.populate_feed()

    def populate_feed(self):
        """Pinta todas las entradas en el scroll layout."""
        # Limpiar layout actual
        for i in reversed(range(self.feed_layout.count())): 
            widget = self.feed_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                
        entries = self.diary_manager.get_entries()
        
        if not entries:
            empty_label = QLabel("El diario está vacío. ¡Escribe la primera entrada!")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: gray; font-style: italic; padding: 20px;")
            self.feed_layout.addWidget(empty_label)
            return

        for entry in entries:
            self.add_entry_widget(entry)
            
        # Hacer scroll automático hacia abajo al cargar
        QTimer.singleShot(50, self.scroll_to_bottom)

    def add_entry_widget(self, entry):
        """Crea el diseño visual de una burbuja de entrada."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: palette(base);
                border: 1px solid palette(mid);
                border-radius: 6px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(6)
        
        # Parsear fecha
        try:
            dt = datetime.fromisoformat(entry["date"])
            date_str = dt.strftime("%d/%m/%Y a las %H:%M")
        except ValueError:
            date_str = entry["date"]
            
        # Cabecera (Autor y Fecha)
        header_layout = QHBoxLayout()
        lbl_author = QLabel(f"<b>{entry.get('author', 'Desconocido')}</b>")
        lbl_date = QLabel(date_str)
        lbl_date.setStyleSheet("color: gray; font-size: 11px;")
        
        header_layout.addWidget(lbl_author)
        header_layout.addStretch()
        header_layout.addWidget(lbl_date)
        layout.addLayout(header_layout)
        
        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: palette(midlight);")
        layout.addWidget(line)
        
        # Mensaje
        lbl_msg = QLabel(entry.get("message", "").replace("\n", "<br>"))
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(lbl_msg)
        
        self.feed_layout.addWidget(frame)

    def submit_entry(self):
        """Captura los datos y los envía al manager."""
        author = self.author_input.currentText().strip()
        message = self.message_input.toPlainText().strip()
        
        if not author or not message:
            return # No guardar entradas vacías
            
        # 1. Guardar en backend
        self.diary_manager.add_entry(author, message)
        
        # 2. Refrescar historial de autocompletado si es un autor nuevo
        if self.author_input.findText(author) == -1:
            self.author_input.addItem(author)
            
        # 3. Limpiar caja de texto y repintar
        self.message_input.clear()
        self.populate_feed()

    def scroll_to_bottom(self):
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())