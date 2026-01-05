import math
import re
from collections import Counter

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QSpinBox,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
)
from PySide6.QtGui import QFont, QColor, QPainter, QFontMetrics
from PySide6.QtCore import QRectF, QPointF, QSizeF, Qt


class WordCloudDialog(QDialog):
    """Muestra una nube de palabras simple basada en los documentos del proyecto."""

    _STOPWORDS = {
        "a", "al", "algo", "algunas", "algunos", "ante", "antes", "como", "con", "contra", "cual",
        "cuales", "cuando", "de", "del", "desde", "donde", "dos", "el", "ella", "ellas", "ellos",
        "en", "entre", "era", "erais", "eran", "eras", "eres", "es", "esa", "esas", "ese", "eso",
        "esos", "esta", "estaba", "estabais", "estaban", "estabas", "estad", "estada", "estadas",
        "estado", "estados", "estamos", "estando", "estar", "estaremos", "estará", "estarán",
        "estarás", "estaré", "estaréis", "estaría", "estaríais", "estaríamos", "estarían",
        "estarías", "estas", "este", "estemos", "esto", "estos", "estoy", "estuve", "estuviera",
        "estuvierais", "estuvieran", "estuvieras", "estuvieron", "estuviese", "estuvieseis",
        "estuviesen", "estuvieses", "estuvimos", "estuviste", "estuvisteis", "estuvo", "ex",
        "ha", "habéis", "haber", "había", "habíais", "habíamos", "habían", "habías", "habida",
        "habidas", "habido", "habidos", "habiendo", "habremos", "habrá", "habrán", "habrás",
        "habré", "habréis", "habría", "habríais", "habríamos", "habrían", "habrías", "habéis",
        "hacia", "han", "has", "hasta", "hay", "haya", "hayáis", "hayamos", "hayan", "hayas",
        "he", "hemos", "hube", "hubiera", "hubierais", "hubieran", "hubieras", "hubieron",
        "hubiese", "hubieseis", "hubiesen", "hubieses", "hubimos", "hubiste", "hubisteis",
        "hubo", "in", "la", "las", "le", "les", "lo", "los", "más", "me", "mi", "mis", "mía",
        "mías", "mientras", "mío", "míos", "muy", "no", "nos", "nosotras", "nosotros", "nuestra",
        "nuestras", "nuestro", "nuestros", "o", "os", "otra", "otras", "otro", "otros", "para",
        "pero", "poco", "por", "porque", "que", "quien", "quienes", "se", "sea", "seáis",
        "seamos", "sean", "seas", "ser", "será", "serán", "serás", "seré", "seréis", "sería",
        "seríais", "seríamos", "serían", "serías", "si", "sido", "siempre", "siendo", "sin",
        "sobre", "sois", "somos", "son", "soy", "su", "sus", "suya", "suyas", "suyo", "suyos",
        "también", "tan", "tanto", "te", "tendremos", "tendrá", "tendrán", "tendrás", "tendré",
        "tendréis", "tendría", "tendríais", "tendríamos", "tendrían", "tendrías", "tened",
        "tenéis", "tenemos", "tener", "tengo", "tenía", "teníais", "teníamos", "tenían",
        "tenías", "ti", "tiene", "tienen", "tienes", "todo", "todos", "tu", "tus", "tuve",
        "tuviera", "tuvierais", "tuvieran", "tuvieras", "tuvieron", "tuviese", "tuvieseis",
        "tuviesen", "tuvieses", "tuvimos", "tuviste", "tuvisteis", "tuvo", "un", "una", "uno",
        "unos", "y", "ya", "yo",
    }

    def __init__(self, project, documents, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nube de palabras")
        self.resize(900, 600)
        self.project = project
        self.documents = documents or []

        layout = QVBoxLayout(self)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("Documento:"))
        self.cbo_doc = QComboBox()
        self.cbo_doc.addItem("(Todos)")
        for doc in self.documents:
            self.cbo_doc.addItem(doc)
        filters.addWidget(self.cbo_doc)

        filters.addWidget(QLabel("Mínimo letras:"))
        self.spin_min_len = QSpinBox()
        self.spin_min_len.setRange(2, 12)
        self.spin_min_len.setValue(3)
        filters.addWidget(self.spin_min_len)

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_refresh.clicked.connect(self.build_cloud)
        filters.addWidget(self.btn_refresh)
        filters.addStretch()
        layout.addLayout(filters)

        self.scene = QGraphicsScene()
        self.cloud_view = QGraphicsView(self.scene)
        self.cloud_view.setRenderHint(QPainter.Antialiasing)
        self.cloud_view.setRenderHint(QPainter.TextAntialiasing)
        self.cloud_view.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.cloud_view, 1)

        self.cbo_doc.currentIndexChanged.connect(self.build_cloud)
        self.spin_min_len.valueChanged.connect(self.build_cloud)
        self.build_cloud()

    def build_cloud(self):
        docs_filter = self.cbo_doc.currentText()
        active_docs = self.documents if docs_filter == "(Todos)" else [docs_filter]
        min_len = self.spin_min_len.value()

        text_chunks = []
        for doc in active_docs:
            try:
                text_chunks.append(self.project.read_document(doc))
            except Exception:
                continue

        text = " ".join(text_chunks).lower()
        tokens = re.findall(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü]+", text)
        words = [t for t in tokens if len(t) >= min_len and t not in self._STOPWORDS]
        counts = Counter(words)

        self.scene.clear()
        view_size = self.cloud_view.viewport().size()
        canvas_w = max(view_size.width(), 860)
        canvas_h = max(view_size.height(), 520)
        if not counts:
            empty_item = QGraphicsSimpleTextItem("No hay palabras suficientes para mostrar.")
            self.scene.addItem(empty_item)
            self.scene.setSceneRect(empty_item.boundingRect())
            return

        top_words = counts.most_common(80)
        values = [c for _, c in top_words]
        min_val, max_val = min(values), max(values)

        def scale(val, min_size=12, max_size=36):
            if min_val == max_val:
                return (min_size + max_size) // 2
            return int(min_size + (val - min_val) * (max_size - min_size) / (max_val - min_val))

        colors = [
            QColor("#1b4965"),
            QColor("#5fa8d3"),
            QColor("#62b6cb"),
            QColor("#cae9ff"),
            QColor("#43766c"),
            QColor("#76453b"),
        ]

        center = QPointF(canvas_w / 2, canvas_h / 2)
        placed_rects = []

        for idx, (word, count) in enumerate(top_words):
            size = scale(count)
            placed = False
            for shrink in range(0, 6):
                final_size = max(10, size - shrink * 2)
                font = QFont()
                font.setPointSize(final_size)
                font.setBold(final_size >= 22)
                metrics = QFontMetrics(font)
                rect = metrics.boundingRect(word)
                rect_size = QSizeF(rect.width() + 6, rect.height() + 6)
                max_radius = min(canvas_w, canvas_h) / 2 - 20
                step = 4
                angle = 0.0
                radius = 0.0
                while radius < max_radius and not placed:
                    x = center.x() + radius * math.cos(angle)
                    y = center.y() + radius * math.sin(angle)
                    top_left = QPointF(x - rect_size.width() / 2, y - rect_size.height() / 2)
                    candidate = QRectF(top_left, rect_size)
                    if self._fits(candidate, canvas_w, canvas_h, placed_rects):
                        item = QGraphicsSimpleTextItem(word)
                        item.setFont(font)
                        item.setBrush(colors[idx % len(colors)])
                        item.setPos(top_left)
                        self.scene.addItem(item)
                        placed_rects.append(candidate)
                        placed = True
                        break
                    angle += 0.35
                    radius += step * angle / (2 * math.pi)
                if placed:
                    break

        self.scene.setSceneRect(0, 0, canvas_w, canvas_h)

    def _fits(self, rect, width, height, placed_rects):
        if rect.left() < 0 or rect.top() < 0 or rect.right() > width or rect.bottom() > height:
            return False
        for other in placed_rects:
            if rect.intersects(other):
                return False
        return True
