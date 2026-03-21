from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
)


class ImageDocumentViewer(QGraphicsView):
    selectionChanged = Signal(object)
    contextMenuRequested = Signal(object, object, object)

    def __init__(self, parent=None, read_only=False):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setContextMenuPolicy(Qt.DefaultContextMenu)

        self.read_only = read_only
        self._pixmap_item = None
        self._image_path = None
        self._rubber_band_item = None
        self._selection_origin = None
        self._selection_rect = None
        self._fragment_items = []
        self._fragment_by_item = {}
        self._displayed_fragments = []
        self._active_fragment = None
        self._zoom_level = 0
        self._theme = None

    def load_image(self, image_path):
        self.scene().clear()
        self._pixmap_item = None
        self._image_path = image_path
        self._fragment_items = []
        self._fragment_by_item = {}
        self._selection_origin = None
        self._selection_rect = None
        self._rubber_band_item = None
        self._active_fragment = None
        self.resetTransform()
        self._zoom_level = 0

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.selectionChanged.emit(None)
            return False

        self._pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene().addItem(self._pixmap_item)
        self.scene().setSceneRect(QRectF(pixmap.rect()))
        self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)
        self.selectionChanged.emit(None)
        return True

    def clear_image(self):
        self.scene().clear()
        self._pixmap_item = None
        self._image_path = None
        self._fragment_items = []
        self._fragment_by_item = {}
        self._displayed_fragments = []
        self._selection_rect = None
        self._rubber_band_item = None
        self._active_fragment = None
        self.selectionChanged.emit(None)

    def has_image(self):
        return self._pixmap_item is not None

    def image_size(self):
        if not self._pixmap_item:
            return None
        pixmap = self._pixmap_item.pixmap()
        return {"w": int(pixmap.width()), "h": int(pixmap.height())}

    def get_selection_rect(self):
        if not self._selection_rect or self._selection_rect.isNull():
            return None
        rect = self._selection_rect.normalized()
        return {
            "x": int(round(rect.x())),
            "y": int(round(rect.y())),
            "w": int(round(rect.width())),
            "h": int(round(rect.height())),
        }

    def clear_selection(self):
        self._selection_origin = None
        self._selection_rect = None
        if self._rubber_band_item:
            self.scene().removeItem(self._rubber_band_item)
            self._rubber_band_item = None
        self.selectionChanged.emit(None)

    def set_fragments(self, fragments, active_fragment=None):
        for item in self._fragment_items:
            self.scene().removeItem(item)
        self._fragment_items = []
        self._fragment_by_item = {}
        self._displayed_fragments = list(fragments or [])
        self._active_fragment = active_fragment

        if not self._pixmap_item:
            return

        for fragment in fragments or []:
            rect = self._fragment_rect(fragment)
            if not rect or rect.isNull():
                continue
            item = QGraphicsRectItem(rect)
            color = QColor(fragment.get("color") or "#ffcc00")
            fill = QColor(color)
            fill.setAlpha(70)
            pen = QPen(color)
            pen.setWidth(3 if fragment is active_fragment else 2)
            item.setPen(pen)
            item.setBrush(fill)
            item.setZValue(2)
            self.scene().addItem(item)
            self._fragment_items.append(item)
            self._fragment_by_item[item] = fragment

    def focus_fragment(self, fragment):
        self._active_fragment = fragment
        if not fragment:
            self.set_fragments(self._displayed_fragments)
            return
        fragments = list(self._displayed_fragments)
        if fragment not in fragments:
            fragments.append(fragment)
        self.set_fragments(fragments, active_fragment=fragment)
        rect = self._fragment_rect(fragment)
        if rect and not rect.isNull():
            self.fitInView(rect.adjusted(-20, -20, 20, 20), Qt.KeepAspectRatio)

    def apply_theme(self, theme):
        self._theme = theme
        background = QColor(theme["text_bg"])
        self.setBackgroundBrush(background)
        self.setStyleSheet(
            f"""
            QGraphicsView {{
                background-color: {theme['text_bg']};
                border: 1px solid {theme['border']};
                border-radius: 8px;
            }}
            QScrollBar:vertical {{
                background: {theme['panel_bg']};
                width: 10px;
                margin: 0px;
                border: 1px solid {theme['border']};
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme['selection']};
                min-height: 30px;
                border-radius: 6px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: {theme['panel_bg']};
                height: 10px;
                margin: 0px;
                border: 1px solid {theme['border']};
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal {{
                background: {theme['selection']};
                min-width: 30px;
                border-radius: 6px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            """
        )

    def zoom_in(self):
        if not self._pixmap_item:
            return
        self.scale(1.15, 1.15)
        self._zoom_level += 1

    def zoom_out(self):
        if not self._pixmap_item:
            return
        self.scale(1 / 1.15, 1 / 1.15)
        self._zoom_level -= 1

    def zoom_reset(self):
        if not self._pixmap_item:
            return
        self.resetTransform()
        self._zoom_level = 0
        self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier and self._pixmap_item:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)

    def mousePressEvent(self, event):
        if not self._pixmap_item:
            return super().mousePressEvent(event)

        if event.button() == Qt.LeftButton and not self.read_only:
            scene_pos = self._clamp_to_image(self.mapToScene(event.position().toPoint()))
            self._selection_origin = scene_pos
            self._selection_rect = QRectF(scene_pos, scene_pos)
            self._ensure_rubber_band()
            self._rubber_band_item.setRect(self._selection_rect.normalized())
            self.selectionChanged.emit(self.get_selection_rect())
            event.accept()
            return

        if event.button() == Qt.RightButton:
            scene_pos = self._clamp_to_image(self.mapToScene(event.position().toPoint()))
            fragment = self._fragment_at_view_pos(event.position().toPoint())
            self.contextMenuRequested.emit(
                {"x": scene_pos.x(), "y": scene_pos.y()},
                event.globalPosition().toPoint(),
                fragment,
            )
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._selection_origin is not None and not self.read_only:
            scene_pos = self._clamp_to_image(self.mapToScene(event.position().toPoint()))
            self._selection_rect = QRectF(self._selection_origin, scene_pos).normalized()
            self._ensure_rubber_band()
            self._rubber_band_item.setRect(self._selection_rect)
            self.selectionChanged.emit(self.get_selection_rect())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._selection_origin is not None and not self.read_only:
            rect = self._selection_rect.normalized() if self._selection_rect else QRectF()
            self._selection_origin = None
            if rect.width() < 3 or rect.height() < 3:
                self.clear_selection()
            else:
                self._selection_rect = rect
                self.selectionChanged.emit(self.get_selection_rect())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _ensure_rubber_band(self):
        if self._rubber_band_item:
            return
        self._rubber_band_item = QGraphicsRectItem()
        color = QColor(self._theme["selection"] if self._theme else "#1976d2")
        fill = QColor(color)
        fill.setAlpha(45)
        pen = QPen(color)
        pen.setWidth(2)
        self._rubber_band_item.setPen(pen)
        self._rubber_band_item.setBrush(fill)
        self._rubber_band_item.setZValue(3)
        self.scene().addItem(self._rubber_band_item)

    def _clamp_to_image(self, scene_pos):
        if not self._pixmap_item:
            return QPointF(scene_pos)
        bounds = self._pixmap_item.boundingRect()
        x = min(max(scene_pos.x(), bounds.left()), bounds.right())
        y = min(max(scene_pos.y(), bounds.top()), bounds.bottom())
        return QPointF(x, y)

    def _fragment_rect(self, fragment):
        rect_data = fragment.get("rect") or {}
        if not rect_data:
            return None
        return QRectF(
            float(rect_data.get("x", 0)),
            float(rect_data.get("y", 0)),
            float(rect_data.get("w", 0)),
            float(rect_data.get("h", 0)),
        ).normalized()

    def _fragment_at_view_pos(self, pos):
        for item in self.items(pos):
            if item in self._fragment_by_item:
                return self._fragment_by_item[item]
        return None
