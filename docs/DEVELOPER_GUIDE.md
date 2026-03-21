# Guia tecnica y de desarrollo

## 1. Arquitectura general

La aplicacion activa parte en `main.py`:

- crea `QApplication`
- muestra `ReadmeDialog`
- crea `RaizQAGUI`

La mayor parte de la logica de interfaz y coordinacion vive en `gui/main_window.py`.

Separacion principal:

- `core/`: persistencia y utilidades de dominio
- `gui/`: ventana principal, temas, arboles y dialogos
- `code_viewer/`: visor de fragmentos codificados

## 2. Modulos clave

### Entrada

- `main.py`

### Persistencia

- `core/project.py`
  - crea estructura de proyecto
  - importa documentos
  - carga y guarda `project_data.json`
  - administra el diario
- `core/memos.py`
  - administra `memos.json`

### UI principal

- `gui/main_window.py`
  - shell principal de la aplicacion
  - seleccion de proyecto
  - importacion de documentos
  - codificacion de texto
  - codificacion de imagenes por zonas
  - guardado automatico
  - apertura de dialogos de analisis y exportacion

### Visores

- `gui/image_viewer.py`
  - `QGraphicsView` para imagenes
  - seleccion rectangular
  - overlays de fragmentos de imagen
  - zoom con persistencia de coordenadas
- `code_viewer/code_viewer.py`
  - visor de fragmentos de codigos
  - soporta texto e imagen

### Dialogos

- `gui/dialogs/memo_dialog.py`
- `gui/dialogs/diary_dialog.py`
- `gui/dialogs/fragments_dialog.py`
- `gui/dialogs/compare_dialog.py`
- `gui/dialogs/code_matrix_dialog.py`
- `gui/dialogs/wordcloud_dialog.py`
- `gui/dialogs/themes_categories_dialog.py`
- `gui/dialogs/themes_analysis_dialog.py`
- `gui/dialogs/case_setup_dialog.py`
- `gui/dialogs/case_study_dialog.py`
- `gui/dialogs/readme_dialog.py`

## 3. Flujo principal de estado

### Inicio

1. `main.py` crea la app Qt.
2. Se muestra `ReadmeDialog`.
3. Se instancia `RaizQAGUI`.

### Trabajo con proyecto

1. El usuario define `working_dir`.
2. Se crea o abre un proyecto.
3. `core.project.Project` garantiza estructura minima.
4. `gui.main_window.RaizQAGUI.load_project()` reconstruye:
   - codigos
   - documentos
   - highlights
   - grupos de documentos
   - temas
   - casos

### Guardado

`RaizQAGUI.save_project()`:

- reconstruye grupos desde el arbol de documentos
- reconstruye codigos desde el arbol de codigos
- delega en `Project.save_state(...)`

Tambien existe guardado automatico cada 30 segundos.

## 4. Codificacion de texto

El flujo se basa en `QTextEdit`:

1. seleccion de texto
2. menu contextual
3. creacion o asignacion a codigo
4. guardado de fragmento con `start/end`
5. resaltado visual

Funciones relevantes en `gui/main_window.py`:

- `text_context_menu`
- `create_new_code`
- `add_to_existing_code`
- `create_subcode`
- `highlight_fragment`
- `restore_highlights`

## 5. Codificacion de imagenes

La implementacion actual usa `ImageDocumentViewer`.

Puntos clave:

- el usuario dibuja un rectangulo sobre la imagen
- la zona se guarda como `rect`
- las coordenadas son de la imagen original
- el zoom no altera la persistencia

Funciones relevantes:

- `ImageDocumentViewer.load_image`
- `ImageDocumentViewer.get_selection_rect`
- `ImageDocumentViewer.set_fragments`
- `RaizQAGUI._image_context_menu`
- `RaizQAGUI.create_new_code`
- `RaizQAGUI.add_to_existing_code`

## 6. Analisis incluidos

### CompareDialog

Compara dos documentos y navega coincidencias de codigos compartidos.

### CodeMatrixDialog

Genera una matriz `codigo x documento` con:

- vista tabla
- vista heatmap
- normalizacion global, por fila o por documento
- orden por nombre o total descendente

### WordCloudDialog

Genera una nube de palabras con filtro de longitud minima y stopwords embebidas.

### ThemesCategoriesDialog

Agrupa codigos por arrastre dentro de temas o categorias.

### ThemesAnalysisDialog

Resume los temas y permite abrir fragmentos por codigo.

### CaseSetupDialog + CaseStudyDialog

Definen casos, asignan documentos y permiten revisar codigos y fragmentos por caso.

## 7. Dependencias

`requirements.txt`:

- `PySide6`
- `PyPDF2`
- `python-docx`
- `pyspellchecker`
- `openpyxl`

Uso principal:

- `PySide6`: interfaz y widgets
- `PyPDF2`: lectura de PDF
- `python-docx`: lectura y exportacion Word
- `pyspellchecker`: corrector de memos
- `openpyxl`: exportacion de codigos a Excel

## 8. Entorno de desarrollo

Instalacion:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Ejecucion:

```bash
python main.py
```

Verificacion de sintaxis:

```bash
python -m compileall .
```

## 9. Empaquetado

### Windows

Spec activo:

- `RaizQA.spec`

Comando:

```bash
pyinstaller --clean RaizQA.spec
```

Salida:

- `dist/RaizQA.exe`

### macOS

Spec disponible:

- `RaizQA_macos.spec`

Comando:

```bash
pyinstaller --clean RaizQA_macos.spec
```

### Linux

- No existe aun un spec dedicado en este repositorio.
- La ruta estable hoy es ejecutar desde codigo fuente.

## 10. Estructura del repositorio

```text
core/
  persistencia del proyecto y memos

gui/
  ventana principal, temas, arboles y dialogos

code_viewer/
  visor especializado de fragmentos

data/
  datos auxiliares del proyecto

models/
  modulos historicos o de compatibilidad
```

## 11. Archivos historicos o secundarios

No son la ruta principal actual:

- `gui_raizQA.py`
- `gui_raizQA_pyside.py`
- `gui_raizQA_pyside.spec`
- parte de `models/`

Si se hace limpieza futura, conviene validarlos antes de eliminarlos para no romper flujos heredados.

## 12. Puntos de extension recomendados

### Nuevos dialogos de analisis

Patron actual:

1. crear clase `QDialog` en `gui/dialogs/`
2. abrirla desde `gui/main_window.py`
3. pasar `project`, `codes`, `documents` o tema actual segun corresponda

### Nuevos formatos de documento

La extension natural esta en `core/project.py`:

- deteccion de extension
- lector especializado
- conversion al formato persistido del proyecto

### Nuevas exportaciones

La mayoria viven hoy en `gui/main_window.py`.
Si se amplian, conviene extraerlas a modulos dedicados de exportacion.

## 13. Riesgos tecnicos actuales

- `gui/main_window.py` concentra mucha logica y seria buen candidato a refactor por componentes.
- Hay coexistencia de estructuras nuevas y legacy.
- Los memos aparecen tanto en `memos.json` como dentro del estado del proyecto.
- La app depende de reconstruccion de estado desde widgets en varias operaciones de guardado.

## 14. Mejoras naturales futuras

- documentar pruebas manuales por feature
- agregar tests automatizados para persistencia y transformaciones de datos
- extraer servicios de exportacion
- consolidar modelos activos y legacy
- agregar spec de Linux
