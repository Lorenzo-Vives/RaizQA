# -------------------- README / VENTANA DE BIENVENIDA --------------------
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox

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
            <li>Escribir memos analíticos</li>
            <li>Desarrollar y exportar el diario de codificación</li>
            <li>Exportar el libro de códigos y fragmentos</li>
            <li>Visualizar los códigos y fragmentos asociados</li>
        </ul>

        <h3>⚡ Guía rápida</h3>
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
        Versión 1.4 — desarrollado en Python + PySide6 con ayuda de Codex y ChatGPT-5.
        </p>
        """

        text.setHtml(readme_content)
        layout.addWidget(text)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
        btn_box.accepted.connect(self.accept)
        layout.addWidget(btn_box)
        self.setLayout(layout)
