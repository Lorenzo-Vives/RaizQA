# Guia tecnica y de desarrollo

## 1. Arquitectura general (MVC)

La aplicacion sigue un patrón **Model-View-Controller (MVC)**:

- **Model (`core/project.py`)**: Maneja la persistencia y las Estructuras de Datos en Memoria (EDDs).
- **View (`gui/`)**: Muestra la interfaz al usuario (`main_window.py`, `widgets/`, `dialogs/`) y envía señales.
- **Controller (`core/logica.py`)**: Recibe señales de la vista, orquesta al modelo y a los workers asíncronos, y devuelve señales de actualización a la vista.

La aplicacion activa parte en `main.py`:

- crea `QApplication`
- muestra `ReadmeDialog`
- instancia el **Controller** (`ControladorLogico`) y la **Vista** (`RaizQAGUI`), conectando sus señales.
- `code_viewer/`: visor de fragmentos codificados

## 2. Modulos clave

### Controlador y Workers

- `core/logica.py`
  - procesa las acciones del usuario
  - emite señales Qt de vuelta a la UI
- `core/worker_objects.py`
  - hilos en segundo plano para importación, exportación y búsquedas

### Persistencia y Modelo

- `core/project.py`
  - crea estructura de proyecto
  - importa documentos
  - carga y guarda el estado unificado en `project_data.json` (junto con su backup `.bak`)
  - administra el diario y los memos integrados
- `core/merge_manager.py` (junto con `import_manager` y `export_manager`)
  - maneja la fusión de códigos y colaboración en equipo

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
pip install pytest pytest-qt
```

Ejecucion:

```bash
python main.py
```

Ejecucion de pruebas automatizadas:

```bash
pytest tests/
```

Verificacion de sintaxis:

```bash
python -m compileall .
```

## 9. Empaquetado

### Windows

Spec activo:

- `main.spec`

Comando:

```bash
pyinstaller --clean main.spec
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
  [Model/Controller] persistencia del proyecto, logica y colaboracion

gui/
  [View] ventana principal, estilos, temas, widgets modulares y dialogos

code_viewer/
  visor especializado de fragmentos

tests/
  pruebas unitarias y de integracion (pytest)

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

- `gui/main_window.py` concentra todavía algo de lógica visual, pero está en proceso continuo de refactorización hacia `gui/widgets/`.
- La app depende de reconstruccion de estado desde widgets en ciertas operaciones, aunque se avanza hacia una separación estricta.

## 14. Mejoras naturales futuras

- documentar pruebas manuales por feature
- extraer servicios de exportacion
- consolidar modelos activos y legacy
- agregar spec de Linux
