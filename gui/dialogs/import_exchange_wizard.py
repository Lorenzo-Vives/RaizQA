from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QTreeWidget, QTreeWidgetItem, QCheckBox, QLabel, QHeaderView, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QFileIconProvider

class ImportDocumentsPage(QWizardPage):
    """
    Página del asistente de importación que muestra una tabla comparativa
    entre los documentos del paquete .rex y los locales del proyecto.
    Permite al usuario decidir cuáles fusionar o sobrescribir.
    """
    def __init__(self, project, exchange_data, parent=None):
        super().__init__(parent)
        self.project = project
        self.exchange_data = exchange_data
        
        self.setTitle("Seleccionar y asignar documentos")
        self.setSubTitle("Por favor selecciona los documentos que deseas importar.")
        
        layout = QVBoxLayout(self)
        
        self.cb_select_all = QCheckBox("Seleccionar todos los documentos")
        self.cb_select_all.setChecked(True)
        self.cb_select_all.stateChanged.connect(self._toggle_all)
        layout.addWidget(self.cb_select_all)
        
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Archivo de Intercambio", "Proyecto Local"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        self._populate_table()
        
    def _populate_table(self):
        docs_in_package = self.exchange_data.get("documents", [])
        existing_docs = set(self.project.list_documents())
        icon_provider = QFileIconProvider()
        file_icon = icon_provider.icon(QFileIconProvider.File)
        
        self.table.setRowCount(len(docs_in_package))
        for row, doc in enumerate(docs_in_package):
            # Column 0: Checkbox + Name
            item_src = QTableWidgetItem(doc)
            item_src.setIcon(file_icon)
            item_src.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item_src.setCheckState(Qt.Checked)
            self.table.setItem(row, 0, item_src)
            
            # Column 1: Target combo or label
            if doc in existing_docs:
                item_target = QTableWidgetItem(doc) # Will overwrite
                item_target.setIcon(file_icon)
                item_target.setBackground(QColor(200, 230, 200)) # Light green to indicate match
            else:
                item_target = QTableWidgetItem("<Nuevo documento>")
                item_target.setIcon(file_icon)
            
            item_target.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 1, item_target)

    def _toggle_all(self, state):
        check_state = Qt.Checked if state == Qt.Checked.value else Qt.Unchecked
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(check_state)

    def get_selected_documents(self):
        selected = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                selected.append(item.text())
        return selected


class ImportCodesPage(QWizardPage):
    """
    Página del asistente de importación que visualiza la jerarquía
    de temas y códigos que vienen en el archivo .rex.
    Resalta en verde los códigos nuevos. También contiene opciones adicionales de importación.
    """
    def __init__(self, project, exchange_data, parent=None):
        super().__init__(parent)
        self.project = project
        self.exchange_data = exchange_data
        
        self.setTitle("Seleccionar códigos y opciones")
        self.setSubTitle("Los códigos nuevos se muestran en verde.")
        
        layout = QVBoxLayout(self)
        
        self.cb_select_all = QCheckBox("Seleccionar todos los códigos")
        self.cb_select_all.setChecked(True)
        self.cb_select_all.stateChanged.connect(self._toggle_all)
        layout.addWidget(self.cb_select_all)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        layout.addWidget(self.tree)
        
        # Opciones de importación (movidas aquí desde la página 3)
        self.cb_fragments = QCheckBox("Importar Fragmentos Codificados")
        self.cb_fragments.setChecked(True)
        layout.addWidget(self.cb_fragments)
        
        self.cb_memos = QCheckBox("Importar Memos")
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
        # We need to render the themes and codes from the exchange package
        pkg_themes = self.exchange_data.get("themes_dict", {})
        pkg_codes = self.exchange_data.get("codes_dict", {})
        
        existing_codes = set(self.project.codes_dict.keys())
        
        # Build tree
        codes_in_themes = set()
        icon_provider = QFileIconProvider()
        for theme_name, theme_data in pkg_themes.items():
            theme_item = QTreeWidgetItem([theme_name])
            theme_item.setIcon(0, icon_provider.icon(QFileIconProvider.Folder))
            theme_item.setFlags(theme_item.flags() | Qt.ItemIsUserCheckable)
            theme_item.setCheckState(0, Qt.Checked)
            
            for code_name in theme_data.get("codes", []):
                if code_name in pkg_codes:
                    codes_in_themes.add(code_name)
                    code_item = QTreeWidgetItem([code_name])
                    code_data = pkg_codes[code_name]
                    code_item.setIcon(0, self._circle_icon(code_data.get("hexcolor", "#fff59d")))
                    code_item.setFlags(code_item.flags() | Qt.ItemIsUserCheckable)
                    code_item.setCheckState(0, Qt.Checked)
                    
                    if code_name not in existing_codes:
                        code_item.setForeground(0, QColor("green"))
                    
                    theme_item.addChild(code_item)
            
            self.tree.addTopLevelItem(theme_item)
            theme_item.setExpanded(True)
            
        # Unassigned codes
        unassigned = [c for c in pkg_codes.keys() if c not in codes_in_themes]
        if unassigned:
            unassigned_item = QTreeWidgetItem(["<Sin tema asignado>"])
            unassigned_item.setIcon(0, icon_provider.icon(QFileIconProvider.Folder))
            unassigned_item.setFlags(unassigned_item.flags() | Qt.ItemIsUserCheckable)
            unassigned_item.setCheckState(0, Qt.Checked)
            
            for code_name in unassigned:
                code_item = QTreeWidgetItem([code_name])
                code_data = pkg_codes[code_name]
                code_item.setIcon(0, self._circle_icon(code_data.get("hexcolor", "#fff59d")))
                code_item.setFlags(code_item.flags() | Qt.ItemIsUserCheckable)
                code_item.setCheckState(0, Qt.Checked)
                if code_name not in existing_codes:
                    code_item.setForeground(0, QColor("green"))
                unassigned_item.addChild(code_item)
                
            self.tree.addTopLevelItem(unassigned_item)
            unassigned_item.setExpanded(True)
            
        self.tree.itemChanged.connect(self._handle_item_changed)
        
    def _handle_item_changed(self, item, column):
        self.tree.blockSignals(True)
        state = item.checkState(column)
        for i in range(item.childCount()):
            item.child(i).setCheckState(0, state)
        self.tree.blockSignals(False)

    def _toggle_all(self, state):
        check_state = Qt.Checked if state == Qt.Checked.value else Qt.Unchecked
        self.tree.blockSignals(True)
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setCheckState(0, check_state)
            for j in range(item.childCount()):
                item.child(j).setCheckState(0, check_state)
        self.tree.blockSignals(False)

    def get_selected_codes(self):
        selected = set()
        for i in range(self.tree.topLevelItemCount()):
            top_item = self.tree.topLevelItem(i)
            for j in range(top_item.childCount()):
                child = top_item.child(j)
                if child.checkState(0) == Qt.Checked:
                    selected.add(child.text(0))
        return list(selected)


    def get_options(self):
        return {
            "import_fragments": self.cb_fragments.isChecked(),
            "import_memos": self.cb_memos.isChecked()
        }


class ImportExchangeWizard(QWizard):
    """
    Asistente gráfico (Wizard) para importar y fusionar de manera
    segura un paquete .rex dentro del proyecto actual.
    """
    def __init__(self, project, exchange_data, parent=None):
        super().__init__(parent)
        self.project = project
        self.exchange_data = exchange_data
        
        self.setWindowTitle("Importar archivo de intercambio (.rex)")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setButtonText(QWizard.NextButton, "Siguiente >")
        self.setButtonText(QWizard.BackButton, "< Atrás")
        self.setButtonText(QWizard.FinishButton, "Importar")
        self.setButtonText(QWizard.CancelButton, "Cancelar")
        self.resize(650, 500)
        
        self.docs_page = ImportDocumentsPage(self.project, self.exchange_data)
        self.codes_page = ImportCodesPage(self.project, self.exchange_data)
        
        self.addPage(self.docs_page)
        self.addPage(self.codes_page)
        
    def get_import_data(self):
        data = self.codes_page.get_options()
        data["documents"] = self.docs_page.get_selected_documents()
        data["codes"] = self.codes_page.get_selected_codes()
        return data
