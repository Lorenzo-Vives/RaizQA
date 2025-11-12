# gui_raizQA_pyside.py
import sys
import os
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QTextEdit, QFileDialog, QMessageBox,
    QInputDialog, QTreeWidget, QTreeWidgetItem, QMenu, QDialog,
    QTextEdit as QTextEditDialog, QDialogButtonBox, QHeaderView, QTreeWidgetItemIterator,
    QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCharFormat, QColor
from models.project import Project
from code_viewer.code_viewer import CodeViewerWindow

# Para revisión ortográfica
try:
    from spellchecker import SpellChecker
    SPELLCHECK_AVAILABLE = True
except Exception:
    SPELLCHECK_AVAILABLE = False

# -------------------- README / VENTANA DE BIENVENIDA --------------------
class ReadmeDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bienvenido a RaizQA 🌱")
        self.resize(600, 500)

        layout = QVBoxLayout()
        text = QTextEdit()
        text.setReadOnly(True)

        # Puedes reemplazar este texto con lo que quieras
        readme_content = """
        <h2>🌱 Bienvenido a <b>RaizQA</b></h2>
        <p>Esta aplicación es un proyecto <b>open source</b> para análisis cualitativo de datos. RaizQA permite:</p>
        <ul>
            <li>Importar documentos (.txt, .pdf, .docx)</li>
            <li>Crear y organizar códigos y subcódigos</li>
            <li>Guardar fragmentos de texto codificados</li>
            <li>Escribir memos analíticos con corrector ortográfico</li>
            <li>Visualizar los códigos y fragmentos asociados</li>
        </ul>

        <h3>🪶 Guía rápida</h3>
        <ol>
            <li><b>Selecciona</b> un Working Directory donde guardar tus proyectos.</li>
            <li><b>Crea</b> un nuevo proyecto o abre uno existente.</li>
            <li><b>Importa</b> tus documentos (TXT, PDF o DOCX).</li>
            <li><b>Selecciona texto</b> para crear códigos o subcódigos.</li>
            <li><b>Haz clic derecho</b> en un código para agregar o editar un memo.</li>
        </ol>

        <h3>💾 Guardado automático</h3>
        <p>Tu proyecto se guarda automáticamente cada 30 segundos.</p>

        <p style='color:gray; font-size:10pt; margin-top:20px;'>
        Versión 1.0 — desarrollado en Python + PySide6 con ayuda de ChatGPT-5.
        </p>
        """

        text.setHtml(readme_content)
        layout.addWidget(text)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
        btn_box.accepted.connect(self.accept)
        layout.addWidget(btn_box)
        self.setLayout(layout)


# -------------------- DIALOGO DE MEMOS --------------------
from spellchecker import SpellChecker
from PySide6.QtGui import QTextCharFormat, QSyntaxHighlighter, QTextCursor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox, QMenu

class SpellHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.spell_es = SpellChecker(language='es')
        self.spell_en = SpellChecker(language='en')
        self.error_format = QTextCharFormat()
        self.error_format.setUnderlineColor(Qt.red)
        self.error_format.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
        self.misspelled_words = {}  # {pos: palabra}

    def highlightBlock(self, text):
        self.misspelled_words.clear()
        words = text.split()
        for word in words:
            clean = ''.join([c for c in word if c.isalpha()])
            if not clean:
                continue
            if (clean.lower() not in self.spell_es and
                clean.lower() not in self.spell_en):
                start = text.find(word)
                if start >= 0:
                    self.setFormat(start, len(word), self.error_format)
                    self.misspelled_words[start] = clean


class MemoDialog(QDialog):
    def __init__(self, code_label, memo_text=""):
        super().__init__()
        self.setWindowTitle(f"Memo para '{code_label}'")
        self.resize(400, 300)

        layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        self.text_edit.setText(memo_text)
        self.highlighter = SpellHighlighter(self.text_edit.document())
        self.text_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_edit.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.text_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def show_context_menu(self, pos):
        cursor = self.text_edit.cursorForPosition(pos)
        cursor.select(QTextCursor.WordUnderCursor)
        selected_word = cursor.selectedText().strip()

        if not selected_word:
            # si no hay palabra seleccionada, mostrar el menú normal
            return self.text_edit.createStandardContextMenu().exec(self.text_edit.mapToGlobal(pos))

        # Verificar si la palabra es incorrecta
        if (selected_word.lower() in self.highlighter.spell_es or
            selected_word.lower() in self.highlighter.spell_en):
            # palabra correcta → menú normal
            return self.text_edit.createStandardContextMenu().exec(self.text_edit.mapToGlobal(pos))

        # Obtener sugerencias
        suggestions = (
            self.highlighter.spell_es.candidates(selected_word)
            or self.highlighter.spell_en.candidates(selected_word)
        )

        menu = QMenu(self)
        if suggestions:
            for s in list(suggestions)[:5]:
                action = menu.addAction(s)
                action.triggered.connect(lambda checked=False, sug=s: self.replace_word(cursor, sug))
        else:
            menu.addAction("(Sin sugerencias)").setEnabled(False)

        menu.addSeparator()
        menu.addAction("Ignorar palabra")
        menu.exec(self.text_edit.mapToGlobal(pos))

    def replace_word(self, cursor, suggestion):
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(suggestion)
        cursor.endEditBlock()

    def get_memo(self):
        return self.text_edit.toPlainText()



# -------------------- DIALOGO DE VISUALIZACIÓN DE FRAGMENTOS --------------------
class CodeFragmentsDialog(QDialog):
    def __init__(self, code_name, fragments):
        super().__init__()
        self.setWindowTitle(f"Fragmentos del código: {code_name}")
        self.resize(700, 420)
        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        for frag in fragments:
            # mostrar preview para la lista
            preview = frag.get("text", "").strip().replace("\n", " ")
            if len(preview) > 200:
                preview = preview[:200] + "..."
            # incluir documento corto si viene
            doc = frag.get("document", "")
            display = f"{doc}  →  {preview}" if doc else preview
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, frag)
            self.list_widget.addItem(item)

        self.list_widget.itemSelectionChanged.connect(self.on_select)
        layout.addWidget(self.list_widget)

        self.viewer = QTextEdit()
        self.viewer.setReadOnly(True)
        self.viewer.setStyleSheet("background: white; font-size: 13px; padding: 8px;")
        self.viewer.setPlaceholderText("Selecciona un fragmento para ver el texto completo...")
        layout.addWidget(self.viewer)

        self.setLayout(layout)

    def on_select(self):
        items = self.list_widget.selectedItems()
        if not items:
            self.viewer.clear()
            return
        frag = items[0].data(Qt.UserRole)
        self.viewer.setPlainText(frag.get("text", ""))


# -------------------- DIALOGO PARA VER TODOS LOS CÓDIGOS --------------------
class CodeViewerDialog(QDialog):
    """Visor más completo — si usas otro módulo en code_viewer, mantenlo; esta clase es auxiliar."""
    def __init__(self, codes):
        super().__init__()
        self.setWindowTitle("Visor de Códigos")
        self.resize(600, 420)

        layout = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Código", "n", "Memo"])
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.populate_tree(codes)
        layout.addWidget(self.tree)

    def populate_tree(self, codes):
        items_by_name = {}
        for c in codes:
            memo_mark = "✏️" if c.get("memo") else ""
            item = QTreeWidgetItem([c["name"], str(c.get("count", 0)), memo_mark])
            items_by_name[c["name"]] = item
            if not c.get("parent"):
                self.tree.addTopLevelItem(item)
        for c in codes:
            parent_name = c.get("parent")
            if parent_name and parent_name in items_by_name:
                items_by_name[parent_name].addChild(items_by_name[c["name"]])


# -------------------- VENTANA PRINCIPAL --------------------
class RaizQAGUI(QMainWindow):
    AUTO_SAVE_INTERVAL = 30000

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RaizQA")
        self.setGeometry(100, 100, 1000, 600)

        self.current_project = None
        self.working_dir = None
        self.current_doc = None
        self.codes = []
        self.highlights = {}

        # -------------------- LAYOUT PRINCIPAL --------------------
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        middle_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # -------------------- TOP --------------------
        self.btn_working_dir = QPushButton("Seleccionar Working Directory")
        self.btn_working_dir.clicked.connect(self.select_working_dir)
        top_layout.addWidget(self.btn_working_dir)

        self.btn_create = QPushButton("Crear Proyecto")
        self.btn_create.clicked.connect(self.create_project)
        top_layout.addWidget(self.btn_create)

        self.btn_open = QPushButton("Abrir Proyecto")
        self.btn_open.clicked.connect(self.open_project)
        top_layout.addWidget(self.btn_open)

        self.btn_import_doc = QPushButton("Importar Archivo")
        self.btn_import_doc.clicked.connect(self.import_file)
        top_layout.addWidget(self.btn_import_doc)

        self.btn_save = QPushButton("💾 Guardar Proyecto")
        self.btn_save.clicked.connect(self.save_project)
        top_layout.addWidget(self.btn_save)

        self.btn_view_codes = QPushButton("Ver Códigos")
        self.btn_view_codes.clicked.connect(self.open_code_viewer)
        top_layout.addWidget(self.btn_view_codes)

        top_layout.addStretch()
        self.lbl_project = QLabel("Proyecto: Ninguno")
        top_layout.addWidget(self.lbl_project)
        main_layout.addLayout(top_layout)

        # -------------------- MIDDLE --------------------
        left_layout = QVBoxLayout()
        self.doc_list = QListWidget()
        self.doc_list.currentItemChanged.connect(self.display_document)
        left_layout.addWidget(QLabel("Documentos importados"))
        left_layout.addWidget(self.doc_list, 50)

        self.code_tree = QTreeWidget()
        self.code_tree.setHeaderLabels(["Código", "n", "Memo"])
        header = self.code_tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        left_layout.addWidget(QLabel("Códigos (Jerarquía)"))
        left_layout.addWidget(self.code_tree, 50)

        # Eventos
        self.code_tree.itemClicked.connect(self.show_code_fragments)
        self.code_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.code_tree.customContextMenuRequested.connect(self.code_tree_context_menu)

        middle_layout.addLayout(left_layout, 40)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_area.customContextMenuRequested.connect(self.text_context_menu)
        middle_layout.addWidget(self.text_area, 60)
        main_layout.addLayout(middle_layout)

        self.lbl_working_dir = QLabel("WD: Ninguno")
        self.lbl_working_dir.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_working_dir.setStyleSheet("font-size:10px; color: gray; margin-top:-10px;")
        main_layout.addWidget(self.lbl_working_dir)

        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(self.AUTO_SAVE_INTERVAL)

    # -------------------- MEMOS --------------------
    def code_tree_context_menu(self, pos):
        item = self.code_tree.itemAt(pos)
        if not item:
            return
        code_name = item.text(0)
        menu = QMenu()

        view_memo_action = menu.addAction("👁️ Ver Memo")
        add_memo_action = menu.addAction("📝 Agregar / Editar Memo")
        delete_memo_action = menu.addAction("❌ Eliminar Memo")

        action = menu.exec(self.code_tree.viewport().mapToGlobal(pos))
        if action == view_memo_action:
            self.view_memo(code_name)
        elif action == add_memo_action:
            self.add_or_edit_memo(code_name)
        elif action == delete_memo_action:
            self.delete_memo(code_name)

    def view_memo(self, code_name):
        """Muestra el memo asociado al código en modo solo lectura."""
        code = next((c for c in self.codes if c["name"] == code_name), None)
        if not code:
            return

        memo_text = code.get("memo", "").strip()
        if not memo_text:
            QMessageBox.information(self, "Sin memo", f"El código '{code_name}' no tiene memo asociado.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"👁️ Memo de '{code_name}'")
        dialog.resize(420, 320)
        layout = QVBoxLayout(dialog)
        text_edit = QTextEditDialog()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(memo_text)
        layout.addWidget(text_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def add_or_edit_memo(self, code_name):
        code = next((c for c in self.codes if c["name"] == code_name), None)
        if not code:
            return
        dialog = MemoDialog(code_name, code.get("memo", ""))
        if dialog.exec():
            code["memo"] = dialog.get_memo()
            self.update_memo_icon(code_name, has_memo=bool(code["memo"]))
            self.save_project()

    def delete_memo(self, code_name):
        code = next((c for c in self.codes if c["name"] == code_name), None)
        if code:
            code["memo"] = ""
            self.update_memo_icon(code_name, has_memo=False)
            self.save_project()

    def update_memo_icon(self, code_name, has_memo):
        iterator = QTreeWidgetItemIterator(self.code_tree)
        while iterator.value():
            item = iterator.value()
            if item.text(0) == code_name:
                item.setText(2, "✏️" if has_memo else "")
                break
            iterator += 1

    # -------------------- FUNCIONES NUEVAS --------------------
    def show_code_fragments(self, item, column):
        code_name = item.text(0)
        code = next((c for c in self.codes if c["name"] == code_name), None)
        if code and "fragments" in code:
            dialog = CodeFragmentsDialog(code_name, code["fragments"])
            dialog.exec()

    # -------------------- FUNCIONES BÁSICAS --------------------
    def select_working_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Selecciona Working Directory")
        if dir_path:
            self.working_dir = dir_path
            self.lbl_working_dir.setText(f"WD: {dir_path}")

    def create_project(self):
        if not self.working_dir:
            QMessageBox.warning(self, "Crear Proyecto", "Primero selecciona el Working Directory.")
            return
        name, ok = QInputDialog.getText(self, "Crear Proyecto", "Nombre del nuevo proyecto:")
        if ok and name:
            self.current_project = Project(name, self.working_dir)
            self.lbl_project.setText(f"Proyecto: {name}")
            QMessageBox.information(self, "Proyecto creado", f"Proyecto '{name}' creado exitosamente.")
            self.save_project()

    def open_project(self):
        if not self.working_dir:
            QMessageBox.warning(self, "Abrir Proyecto", "Primero selecciona el Working Directory.")
            return
        projects = [d for d in os.listdir(self.working_dir) if os.path.isdir(os.path.join(self.working_dir, d))]
        if not projects:
            QMessageBox.warning(self, "Abrir Proyecto", "No se encontraron proyectos.")
            return
        selected, ok = QInputDialog.getItem(self, "Abrir Proyecto", "Selecciona proyecto:", projects, 0, False)
        if ok and selected:
            self.current_project = Project(selected, self.working_dir)
            self.lbl_project.setText(f"Proyecto: {self.current_project.name}")
            self.load_project()
            QMessageBox.information(self, "Proyecto abierto", f"Proyecto '{self.current_project.name}' abierto.")

    # -------------------- GUARDAR / CARGAR --------------------
    def save_project(self):
        if not self.current_project:
            return
        data = {
            "codes": self.codes,
            "documents": [self.doc_list.item(i).text() for i in range(self.doc_list.count())],
        }
        json_path = os.path.join(self.current_project.path, "project_data.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Proyecto guardado en {json_path}")

    def auto_save(self):
        self.save_project()

    def load_project(self):
        json_path = os.path.join(self.current_project.path, "project_data.json")
        if not os.path.exists(json_path):
            return
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.codes = data.get("codes", [])
        self.code_tree.clear()
        self.doc_list.clear()

        for d in data.get("documents", []):
            self.doc_list.addItem(d)
        for c in self.codes:
            parent_item = self.find_tree_item(c["parent"]) if c.get("parent") else None
            memo_mark = "✏️" if c.get("memo") else ""
            code_item = QTreeWidgetItem([c["name"], str(c.get("count", 0)), memo_mark])
            if parent_item:
                parent_item.addChild(code_item)
            else:
                self.code_tree.addTopLevelItem(code_item)

    # -------------------- IMPORTAR ARCHIVO --------------------
    def import_file(self):
        if not self.current_project:
            QMessageBox.warning(self, "Importar archivo", "Primero crea o abre un proyecto.")
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", "", "Documentos (*.txt *.pdf *.docx)")
        if not file_path:
            return

        import docx
        from PyPDF2 import PdfReader
        ext = os.path.splitext(file_path)[1].lower()
        text = ""
        try:
            if ext == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            elif ext == ".pdf":
                reader = PdfReader(file_path)
                text = "\n".join([page.extract_text() or "" for page in reader.pages])
            elif ext == ".docx":
                doc = docx.Document(file_path)
                text = "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer el archivo:\n{e}")
            return

        file_name = os.path.basename(file_path)
        os.makedirs(self.current_project.documents_path, exist_ok=True)
        dest_path = os.path.join(self.current_project.documents_path, file_name)
        with open(dest_path, "w", encoding="utf-8") as f_out:
            f_out.write(text)

        self.doc_list.addItem(file_name)
        self.text_area.setPlainText(text)
        self.current_doc = file_name
        self.save_project()
        QMessageBox.information(self, "Importar", f"✅ Documento '{file_name}' importado correctamente.")

    # -------------------- DOCUMENTO --------------------
    def display_document(self, current, previous=None):
        if not current:
            return
        self.current_doc = current.text()
        txt_path = os.path.join(self.current_project.documents_path, self.current_doc)
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                text = f.read()
                self.text_area.setPlainText(text)
            self.restore_highlights()

    # -------------------- CÓDIGOS --------------------
    def text_context_menu(self, pos):
        cursor = self.text_area.textCursor()
        selected_text = cursor.selectedText()
        menu = QMenu()

        if selected_text:
            create_code_action = menu.addAction("➕ Crear nuevo código")
            create_subcode_action = menu.addAction("↳ Crear subcódigo")

            if self.codes:
                add_to_existing = menu.addMenu("🏷️ Agregar a código existente")
                for c in self.codes:
                    act = add_to_existing.addAction(c["name"])
                    act.triggered.connect(
                        lambda checked=False, name=c["name"]:
                        self.add_to_existing_code(name, cursor, selected_text)
                    )

            action = menu.exec(self.text_area.mapToGlobal(pos))
            if action == create_code_action:
                self.create_new_code(selected_text, cursor)
            elif action == create_subcode_action:
                self.create_subcode(selected_text, cursor)
        else:
            menu.exec(self.text_area.mapToGlobal(pos))

    # -------------------------------------------------
    def create_new_code(self, selected_text, cursor, parent_item=None, code_label=None):
        """Crea un nuevo código y guarda el fragmento con posiciones de texto."""
        if not code_label:
            code_label, ok = QInputDialog.getText(self, "Nuevo Código", "Nombre del código:")
            if not ok or not code_label:
                return

        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()

        fragment = {
            "text": selected_text,
            "document": self.current_doc,  # documento de origen
            "start": start_pos,
            "end": end_pos
        }

        code_item = QTreeWidgetItem([code_label, "1", ""])
        if parent_item:
            parent_item.addChild(code_item)
            parent_item.setExpanded(True)
        else:
            self.code_tree.addTopLevelItem(code_item)

        self.codes.append({
            "name": code_label,
            "parent": parent_item.text(0) if parent_item else None,
            "memo": "",
            "color": "#fff59d",
            "count": 1,
            "fragments": [fragment]
        })

        self.highlight_selection(cursor, QColor("#fff59d"))
        self.save_project()

    # -------------------------------------------------
    def add_to_existing_code(self, code_name, cursor, selected_text):
        """Agrega un fragmento a un código existente (con posición y documento)."""
        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()

        for c in self.codes:
            if c["name"] == code_name:
                fragment = {
                    "text": selected_text,
                    "document": self.current_doc,
                    "start": start_pos,
                    "end": end_pos
                }
                c.setdefault("fragments", []).append(fragment)
                c["count"] = len(c["fragments"])
                self.update_code_count(code_name, c["count"])
                self.highlight_selection(cursor, QColor(c["color"]))
                break
        self.save_project()

    # -------------------------------------------------
    def update_code_count(self, code_name, new_count):
        """Actualiza el número de fragmentos de un código en el árbol."""
        iterator = QTreeWidgetItemIterator(self.code_tree)
        while iterator.value():
            item = iterator.value()
            if item.text(0) == code_name:
                item.setText(1, str(new_count))
                break
            iterator += 1

    # -------------------------------------------------
    def create_subcode(self, selected_text, cursor):
        """Crea un subcódigo bajo un código existente."""
        iterator = QTreeWidgetItemIterator(self.code_tree)
        code_names = []
        while iterator.value():
            code_names.append(iterator.value().text(0))
            iterator += 1
        if not code_names:
            QMessageBox.warning(self, "Subcódigo", "Primero crea un código principal.")
            return

        parent_name, ok = QInputDialog.getItem(self, "Subcódigo", "Selecciona código padre:", code_names, 0, False)
        if not ok or not parent_name:
            return

        sub_label, ok = QInputDialog.getText(self, "Nuevo Subcódigo", "Nombre del subcódigo:")
        if not ok or not sub_label:
            return

        parent_item = self.find_tree_item(parent_name)
        if parent_item:
            self.create_new_code(selected_text, cursor, parent_item, sub_label)

    # -------------------------------------------------
    def find_tree_item(self, code_name):
        """Busca un código en el árbol por nombre."""
        iterator = QTreeWidgetItemIterator(self.code_tree)
        while iterator.value():
            item = iterator.value()
            if item.text(0) == code_name:
                return item
            iterator += 1
        return None


    # -------------------- VER CÓDIGOS --------------------
    def open_code_viewer(self):
        if not self.codes:
            QMessageBox.information(self, "Códigos", "No hay códigos creados aún.")
            return
        if not self.current_doc:
            QMessageBox.information(self, "Códigos", "Primero selecciona un documento.")
            return
        doc_path = os.path.join(self.current_project.documents_path, self.current_doc)
        viewer = CodeViewerWindow(doc_path, self.codes)
        viewer.exec()

    # -------------------- DESTACADO Y RESTAURACIÓN --------------------
    def highlight_selection(self, cursor, color):
        fmt = QTextCharFormat()
        fmt.setBackground(color)
        cursor.mergeCharFormat(fmt)

    def restore_highlights(self):
        for c in self.codes:
            if "fragments" in c:
                color = QColor(c["color"])
                for frag in c["fragments"]:
                    cursor = self.text_area.textCursor()
                    cursor.setPosition(frag["start"])
                    cursor.setPosition(frag["end"], QTextCursor.KeepAnchor)
                    self.highlight_selection(cursor, color)


# -------------------- MAIN --------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RaizQAGUI()
    window.show()

    # 🌿 Mostrar README al iniciar
    readme = ReadmeDialog()
    readme.exec()  # diálogo modal con información de bienvenida

    sys.exit(app.exec())