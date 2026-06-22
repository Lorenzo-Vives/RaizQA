# RaizQA 🌱

RaizQA 🌱 es una aplicacion de analisis cualitativo escrita en Python con PySide6. Permite importar documentos de texto e imagen, crear codigos jerarquicos, registrar memos y diario de codificacion, explorar fragmentos y ejecutar vistas de analisis como comparacion de documentos, nube de palabras, temas/categorias, estudio de casos y Code Matrix Browser con heatmap.

## Instalación
- Descarga la última versión: RaizQA v1.6.5 — https://github.com/Lorenzo-Vives/RaizQA/releases/download/v.1.6.5/RaizQA.exe
## ⚠️ Nota: Windows puede mostrar una advertencia. Usa “Más información” → “Ejecutar de todas formas”.

## Funciones del software:

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
- Trabajo en equipo: exportacion, importacion y fusion de proyectos.



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
|   |-- logica.py
|   `-- worker_objects.py
|-- gui/
|   |-- main_window.py
|   |-- image_viewer.py
|   |-- theme.py
|   |-- widgets/
|   `-- dialogs/
|-- code_viewer/
|-- tests/
|-- data/
`-- models/
```

## Notas de mantenimiento

- RaizQA utiliza un diseño MVC: `core/project.py` (Modelo) y `core/logica.py` (Controlador central), dejando la interfaz gráfica bajo `gui/` (Vista).
- La persistencia es atómica a través de un único archivo de estado. Se descartó el uso de archivos divididos heredados.
- Existen archivos historicos o de transicion como `gui_raizQA.py`, `gui_raizQA_pyside.py` y partes de `models/`. No son la ruta principal de ejecucion actual.

## Licencia

RaizQA se distribuye bajo los términos de la Licencia MIT, sujeta a una restricción de no comercialización basada en la Commons Clause.

Esto significa que puedes usar, copiar, modificar y distribuir el software, siempre que no vendas, revendas, sublicencies ni ofrezcas el software o el acceso al software como un servicio comercial que compita sustancialmente con un producto o servicio comercial basado en RaizQA.

El uso del software para investigación propia, académica o institucional —incluso con financiamiento— está permitido, siempre que el software en sí mismo no sea vendido como servicio comercial.

Consulta el texto completo en el archivo `LICENSE.txt`.
