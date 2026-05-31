from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QListWidget, QListWidgetItem,
    QTreeWidget, QTreeWidgetItem, QCheckBox, QLabel
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QFileIconProvider

class DocumentsPage(QWizardPage):
    """
    Página del asistente de exportación que permite al usuario
    seleccionar qué documentos desea incluir en el paquete de intercambio (.rex).
    Muestra la estructura en carpetas usando un QTreeWidget.
    """
    def __init__(self, project, doc_groups, parent=None):
        super().__init__(parent)
        self.project = project
        self.doc_groups = doc_groups
        self.setTitle("Seleccionar documentos")
        self.setSubTitle("Selecciona los documentos que deseas incluir en el archivo de intercambio.")

        layout = QVBoxLayout(self)
        
        self.cb_select_all = QCheckBox("Seleccionar todos los documentos")
        self.cb_select_all.setChecked(True)
        self.cb_select_all.stateChanged.connect(self._toggle_all)
        layout.addWidget(self.cb_select_all)
        
        self.tree_docs = QTreeWidget()
        self.tree_docs.setHeaderHidden(True)
        layout.addWidget(self.tree_docs)

        self._populate_docs()

    def _populate_docs(self):
        self.icon_provider = QFileIconProvider()
        
        root_docs = self.doc_groups.get("__root__", [])
        for doc in root_docs:
            item = QTreeWidgetItem([doc])
            item.setIcon(0, self.icon_provider.icon(QFileIconProvider.File))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Checked)
            self.tree_docs.addTopLevelItem(item)
            
        for folder, docs in self.doc_groups.items():
            if folder == "__root__": continue
            folder_item = QTreeWidgetItem([folder])
            folder_item.setIcon(0, self.icon_provider.icon(QFileIconProvider.Folder))
            folder_item.setFlags(folder_item.flags() | Qt.ItemIsUserCheckable)
            folder_item.setCheckState(0, Qt.Checked)
            
            for doc in docs:
                doc_item = QTreeWidgetItem([doc])
                doc_item.setIcon(0, self.icon_provider.icon(QFileIconProvider.File))
                doc_item.setFlags(doc_item.flags() | Qt.ItemIsUserCheckable)
                doc_item.setCheckState(0, Qt.Checked)
                folder_item.addChild(doc_item)
                
            self.tree_docs.addTopLevelItem(folder_item)
            folder_item.setExpanded(True)
            
        self.tree_docs.itemChanged.connect(self._handle_item_changed)
        
    def _handle_item_changed(self, item, column):
        self.tree_docs.blockSignals(True)
        state = item.checkState(column)
        for i in range(item.childCount()):
            item.child(i).setCheckState(0, state)
        self.tree_docs.blockSignals(False)

    def _toggle_all(self, state):
        check_state = Qt.Checked if state == Qt.Checked.value else Qt.Unchecked
        self.tree_docs.blockSignals(True)
        for i in range(self.tree_docs.topLevelItemCount()):
            item = self.tree_docs.topLevelItem(i)
            item.setCheckState(0, check_state)
            for j in range(item.childCount()):
                item.child(j).setCheckState(0, check_state)
        self.tree_docs.blockSignals(False)

    def get_selected_documents(self):
        selected = []
        for i in range(self.tree_docs.topLevelItemCount()):
            item = self.tree_docs.topLevelItem(i)
            if item.childCount() == 0:
                if item.checkState(0) == Qt.Checked:
                    selected.append(item.text(0))
            else:
                for j in range(item.childCount()):
                    child = item.child(j)
                    if child.checkState(0) == Qt.Checked:
                        selected.append(child.text(0))
        return selected

class CodesPage(QWizardPage):
    """
    Página del asistente de exportación encargada de mostrar y permitir
    la selección de códigos y temas. Incluye opciones adicionales como exportar memos.
    """
    def __init__(self, project, code_themes, parent=None):
        super().__init__(parent)
        self.project = project
        self.code_themes = code_themes
        self.setTitle("Seleccionar códigos")
        self.setSubTitle("Selecciona los códigos y datos adicionales que deseas exportar.")

        layout = QVBoxLayout(self)
        
        self.cb_select_all = QCheckBox("Seleccionar todos los códigos")
        self.cb_select_all.setChecked(True)
        self.cb_select_all.stateChanged.connect(self._toggle_all)
        layout.addWidget(self.cb_select_all)

        self.tree_codes = QTreeWidget()
        self.tree_codes.setHeaderHidden(True)
        layout.addWidget(self.tree_codes)

        # Checkboxes for extra data
        self.cb_memos = QCheckBox("Incluir memos")
        self.cb_memos.setChecked(True)
        layout.addWidget(self.cb_memos)

        self._populate_codes()

    def _circle_icon(self, color_hex):
        color = QColor(color_hex)
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        return QIcon(pixmap)

    def _populate_codes(self):
        codes_in_themes = set()
        icon_provider = QFileIconProvider()
        
        for theme in self.code_themes:
            theme_name = theme.get("name", "Tema sin nombre")
            theme_codes = theme.get("codes", [])
            
            theme_item = QTreeWidgetItem([theme_name])
            theme_item.setIcon(0, icon_provider.icon(QFileIconProvider.Folder))
            theme_item.setFlags(theme_item.flags() | Qt.ItemIsUserCheckable)
            theme_item.setCheckState(0, Qt.Checked)
            
            for code_name in theme_codes:
                codes_in_themes.add(code_name)
                if code_name in self.project.codes_dict:
                    code_data = self.project.codes_dict[code_name]
                    code_item = QTreeWidgetItem([code_name])
                    code_item.setIcon(0, self._circle_icon(code_data.get("hexcolor", "#fff59d")))
                    code_item.setFlags(code_item.flags() | Qt.ItemIsUserCheckable)
                    code_item.setCheckState(0, Qt.Checked)
                    theme_item.addChild(code_item)
            
            self.tree_codes.addTopLevelItem(theme_item)
            theme_item.setExpanded(True)

        unassigned_codes = []
        for code_name in self.project.codes_dict.keys():
            if code_name not in codes_in_themes:
                unassigned_codes.append(code_name)

        if unassigned_codes:
            unassigned_item = QTreeWidgetItem(["<Sin tema asignado>"])
            unassigned_item.setIcon(0, icon_provider.icon(QFileIconProvider.Folder))
            unassigned_item.setFlags(unassigned_item.flags() | Qt.ItemIsUserCheckable)
            unassigned_item.setCheckState(0, Qt.Checked)
            
            for code_name in unassigned_codes:
                code_data = self.project.codes_dict.get(code_name, {})
                code_item = QTreeWidgetItem([code_name])
                code_item.setIcon(0, self._circle_icon(code_data.get("hexcolor", "#fff59d")))
                code_item.setFlags(code_item.flags() | Qt.ItemIsUserCheckable)
                code_item.setCheckState(0, Qt.Checked)
                unassigned_item.addChild(code_item)
                
            self.tree_codes.addTopLevelItem(unassigned_item)
            unassigned_item.setExpanded(True)
            
        self.tree_codes.itemChanged.connect(self._handle_item_changed)

    def _handle_item_changed(self, item, column):
        self.tree_codes.blockSignals(True)
        state = item.checkState(column)
        for i in range(item.childCount()):
            item.child(i).setCheckState(0, state)
        self.tree_codes.blockSignals(False)

    def _toggle_all(self, state):
        check_state = Qt.Checked if state == Qt.Checked.value else Qt.Unchecked
        self.tree_codes.blockSignals(True)
        for i in range(self.tree_codes.topLevelItemCount()):
            item = self.tree_docs.topLevelItem(i) if hasattr(self, 'tree_docs') else self.tree_codes.topLevelItem(i)
            # wait, typo fixed below
            item = self.tree_codes.topLevelItem(i)
            item.setCheckState(0, check_state)
            for j in range(item.childCount()):
                item.child(j).setCheckState(0, check_state)
        self.tree_codes.blockSignals(False)

    def get_selected_codes(self):
        selected = set()
        for i in range(self.tree_codes.topLevelItemCount()):
            top_item = self.tree_codes.topLevelItem(i)
            for j in range(top_item.childCount()):
                child = top_item.child(j)
                if child.checkState(0) == Qt.Checked:
                    selected.add(child.text(0))
        return list(selected)

class ExportExchangeWizard(QWizard):
    """
    Asistente gráfico (Wizard) principal para exportar datos del proyecto local
    hacia un archivo de intercambio colaborativo (.rex).
    """
    def __init__(self, project, doc_groups, code_themes, parent=None):
        super().__init__(parent)
        self.project = project
        self.doc_groups = doc_groups
        self.code_themes = code_themes
        self.setWindowTitle("Exportar archivo de intercambio (.rex)")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setButtonText(QWizard.NextButton, "Siguiente >")
        self.setButtonText(QWizard.BackButton, "< Atrás")
        self.setButtonText(QWizard.FinishButton, "Exportar")
        self.setButtonText(QWizard.CancelButton, "Cancelar")
        self.resize(600, 500)

        self.docs_page = DocumentsPage(self.project, self.doc_groups)
        self.codes_page = CodesPage(self.project, self.code_themes)

        self.addPage(self.docs_page)
        self.addPage(self.codes_page)

    def get_export_data(self):
        return {
            "documents": self.docs_page.get_selected_documents(),
            "codes": self.codes_page.get_selected_codes(),
            "include_memos": self.codes_page.cb_memos.isChecked(),
            "code_themes": self.code_themes, # We pass it down so export manager has it!
        }
