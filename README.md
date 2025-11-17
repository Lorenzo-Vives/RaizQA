# RaizQA

Aplicación de escritorio para organizar proyectos de análisis cualitativo con PySide6. Permite importar documentos de texto (TXT, PDF o DOCX), subrayar fragmentos, asignar códigos jerárquicos y redactar memos vinculados a cada código.

## Requisitos

- Python 3.10 o superior (se probó con 3.13)
- Pip para instalar dependencias
- Sistema operativo con entorno gráfico (Windows, macOS o Linux con X11/Wayland)

## Instalación rápida

```bash
python -m venv venv
venv\Scripts\activate           # En Linux/macOS usar: source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Flujo básico de uso

1. Ejecuta `python main.py` para abrir el asistente de bienvenida.
2. Selecciona un **Working Directory** donde se crearán las carpetas de los proyectos.
3. Crea un proyecto nuevo o abre uno existente desde la ventana principal.
4. Importa documentos (`.txt`, `.pdf`, `.docx`). Se convertirán a texto plano y quedarán disponibles en la lista de documentos.
5. Selecciona fragmentos en el visor de texto para crear códigos principales o subcódigos y verlos en el árbol jerárquico.
6. Haz clic derecho en el árbol de códigos para crear/editar memos con corrector ortográfico.
7. Usa el botón “Ver Códigos” para abrir el visor que lista todos los fragmentos codificados.

## Estructura de proyecto

Cada proyecto vive dentro del directorio de trabajo elegido y sigue esta estructura:

```
<working_dir>/<nombre_proyecto>/
├── documentos/           # Documentos importados convertidos a .txt
├── codigos/              # (Reservado para exportes por documento)
├── memos.json            # Memos administrados por código
└── project_data.json     # Códigos, documentos y subrayados de la sesión
```

Los memos y el resto de los datos se guardan automáticamente cada 30 segundos y también cuando se accionan las operaciones principales (crear código, importar documento, etc.).

## Módulos relevantes

- `main.py`: punto de entrada de la aplicación.
- `gui/main_window.py`: ventana principal con todo el flujo de trabajo.
- `core/project.py`: administra la persistencia de documentos, códigos y resaltados.
- `core/memos.py`: almacenamiento de memos en formato JSON.
- `code_viewer/code_viewer.py`: visor de fragmentos codificados.

## Próximos pasos sugeridos

- Añadir un script de empaquetado (PyInstaller) para distribuir ejecutables.
- Crear datos de demostración en `data/` para nuevos usuarios.
- Automatizar pruebas unitarias sobre `core/` para asegurar la persistencia.
