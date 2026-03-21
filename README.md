# RaizQA

RaizQA es una aplicacion de analisis cualitativo escrita en Python con PySide6. Permite importar documentos de texto e imagen, crear codigos jerarquicos, registrar memos y diario de codificacion, explorar fragmentos y ejecutar vistas de analisis como comparacion de documentos, nube de palabras, temas/categorias, estudio de casos y Code Matrix Browser con heatmap.

## Estado actual

La entrada principal del proyecto es `main.py` y la ventana principal vive en `gui/main_window.py`.

Capacidades principales:

- Gestion de proyectos con guardado automatico.
- Importacion de `.txt`, `.pdf`, `.docx` e imagenes (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif`, `.tiff`).
- Codificacion de texto por seleccion.
- Codificacion de imagenes por zonas con coordenadas persistentes en espacio de imagen.
- Arbol de codigos con subcodigos, color por codigo y memos.
- Diario de codificacion y exportacion a Word.
- Exportacion del sistema de codigos a Excel.
- Visor de fragmentos codificados.
- Comparacion de documentos.
- Code Matrix Browser con vista tabla y heatmap.
- Nube de palabras.
- Agrupacion de codigos en temas/categorias.
- Estudio de casos basado en documentos y carpetas.

## Requisitos

- Python 3.13 recomendado por el entorno actual del proyecto.
- Dependencias definidas en `requirements.txt`.

Instalacion local:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecutar en desarrollo

```bash
python main.py
```

## Empaquetado

Windows `.exe`:

```bash
pip install pyinstaller
pyinstaller --clean RaizQA.spec
```

Salida esperada:

- `dist/RaizQA.exe`

macOS `.app`:

```bash
pip install pyinstaller
pyinstaller --clean RaizQA_macos.spec
```

Salida esperada:

- `dist/RaizQA.app`

Linux:

- El proyecto puede ejecutarse desde codigo fuente.
- No existe aun un spec dedicado de Linux en este repositorio.

## Documentacion

- Guia de usuario: `docs/USER_GUIDE.md`
- Guia tecnica y de desarrollo: `docs/DEVELOPER_GUIDE.md`
- Modelo de datos y persistencia: `docs/DATA_MODEL.md`

## Estructura del repositorio

```text
.
|-- main.py
|-- requirements.txt
|-- RaizQA.spec
|-- RaizQA_macos.spec
|-- core/
|   |-- project.py
|   `-- memos.py
|-- gui/
|   |-- main_window.py
|   |-- image_viewer.py
|   |-- theme.py
|   |-- document_tree.py
|   |-- code_tree.py
|   `-- dialogs/
|-- code_viewer/
|   `-- code_viewer.py
|-- data/
|-- memos/
`-- models/
```

## Notas de mantenimiento

- `main.py` + `gui/main_window.py` representan la aplicacion activa.
- Existen archivos historicos o de transicion como `gui_raizQA.py`, `gui_raizQA_pyside.py` y partes de `models/`. No son la ruta principal de ejecucion actual.

## Licencia

MIT License.
