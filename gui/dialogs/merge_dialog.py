from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QCheckBox, QPushButton, QFormLayout, QGroupBox, QDialogButtonBox
)
from PySide6.QtCore import Qt

class MergeDialog(QDialog):
    """
    Diálogo para configurar la combinación de dos proyectos (Merge).
    Permite seleccionar de cuál proyecto se mantienen los memos y cómo se tratan los documentos.
    """
    
    def __init__(self, open_project_name, imported_project_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Combinar proyectos")
        self.setMinimumWidth(500)
        
        self.open_proj = f"Proyecto abierto ({open_project_name})"
        self.imported_proj = f"Proyecto importado ({imported_project_name})"
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Etiqueta de instrucción
        lbl_inst = QLabel("Por favor, elija qué contenido debe mantenerse si hay conflictos.")
        lbl_inst.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_inst)
        
        # Grupo de Memos
        group_memos = QGroupBox()
        form_layout = QFormLayout(group_memos)
        
        self.combo_project_memo = QComboBox()
        self.combo_project_memo.addItems([self.open_proj, self.imported_proj])
        
        self.combo_code_memos = QComboBox()
        self.combo_code_memos.addItems([self.open_proj, self.imported_proj])
        
        self.combo_logbook = QComboBox()
        self.combo_logbook.addItem("Combinar y ordenar cronológicamente")
        self.combo_logbook.setEnabled(False)  # Por defecto siempre se combina
        
        form_layout.addRow("Memo del proyecto (raíz del sistema):", self.combo_project_memo)
        form_layout.addRow("Memos de códigos:", self.combo_code_memos)
        form_layout.addRow("Diario de codificación:", self.combo_logbook)
        
        layout.addWidget(group_memos)
        
        # Opciones de Documentos
        self.chk_dont_import_existing = QCheckBox("No importar archivos ya existentes")
        self.chk_dont_import_existing.setChecked(True)
        
        self.chk_merge_groups = QCheckBox("Combinar grupos de archivos ya existentes con el mismo nombre")
        self.chk_merge_groups.setChecked(True)
        
        layout.addWidget(self.chk_dont_import_existing)
        layout.addWidget(self.chk_merge_groups)
        
        # Botones de Acción
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        layout.addWidget(self.button_box)

    def get_settings(self):
        """
        Retorna la configuración elegida por el usuario.
        """
        return {
            "keep_project_memo_from": "open" if self.combo_project_memo.currentIndex() == 0 else "imported",
            "keep_code_memos_from": "open" if self.combo_code_memos.currentIndex() == 0 else "imported",
            "dont_import_existing_docs": self.chk_dont_import_existing.isChecked(),
            "merge_document_groups": self.chk_merge_groups.isChecked()
        }
