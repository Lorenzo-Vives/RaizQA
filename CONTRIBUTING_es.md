## 🌱 Contribuir a RaizQA

¡Te damos la bienvenida al proyecto RaizQA! Estamos muy contentos de que tengas interés en contribuir a nuestra aplicación de análisis cualitativo. Esta guía te ayudará a comprender nuestra arquitectura, la lógica del sistema y cómo puedes comenzar a contribuir tanto en el frontend como en el backend del proyecto.

## 🛠️ Stack Tecnológico y Configuración

RaizQA es una aplicación de escritorio desarrollada completamente en **Python** y **PySide6** (Qt para Python).

### Configuración de tu entorno de desarrollo:
1. **Haz un fork y clona** el repositorio.
2. **Crea un entorno virtual**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En Windows: .venv\Scripts\activate
   ```
3. **Instala las dependencias**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Ejecuta la aplicación**:
   ```bash
   python main.py
   ```

## 🏗️ Arquitectura del Proyecto y Lógica

Para contribuir de manera efectiva, es importante comprender cómo está estructurado RaizQA. La aplicación se divide a grandes rasgos en un **Frontend (Interfaz de Usuario)** y un **Backend (Lógica central y persistencia)**. Estamos en una transición activa hacia una estructura más modular, por lo que es vital seguir estos patrones.

### 🖥️ Frontend (`gui/` y `code_viewer/`)
El frontend es responsable de todo aquello con lo que interactúa el usuario, construido utilizando PySide6.
*   **`gui/main_window.py`**: El contenedor principal de la aplicación. Históricamente contenía la mayor parte de la lógica, pero actualmente se está refactorizando para que actúe estrictamente como un coordinador. Configura el diseño del espacio de trabajo, gestiona el estado global (p. ej., el proyecto activo actualmente) y enruta las señales Qt entre los widgets.
*   **Widgets Modulares (`gui/widgets/`)**: Este es el nuevo hogar para los componentes modulares de la interfaz (p. ej., `actions_panel.py`, `document_editor.py`, `local_search.py`). **Todos los nuevos paneles y componentes de interfaz deben crearse aquí.** Estos componentes deben ser autónomos y comunicarse con la ventana principal mediante señales y slots (Signals and Slots) de PySide6.
*   **`gui/dialogs/`**: Contiene ventanas emergentes modulares para funciones específicas (p. ej., `new_code_dialog.py`, `wordcloud_dialog.py`, `compare_dialog.py`).
*   **`gui/image_viewer.py`**: Maneja la representación de imágenes, el zoom y el trazado de rectángulos de selección mediante `QGraphicsView`. Una lógica clave aquí es que **las coordenadas de selección se mapean a la resolución original de la imagen (`image_size`)**, garantizando que el zoom o el redimensionamiento de la ventana no desplacen las zonas codificadas.
*   **Representación de Texto y Resaltado**: El texto del documento se muestra utilizando `QTextEdit`. Cuando un usuario selecciona texto y lo codifica, la interfaz captura los índices exactos de inicio (`start`) y fin (`end`) de la selección. Estos índices se utilizan para inyectar resaltados de fondo de color (overlays) directamente en el componente de texto.

**Cómo contribuir al Frontend:**
*   **Añadir nuevos widgets modulares**: Al añadir nuevos elementos a la interfaz, constrúyelos como clases autónomas dentro de `gui/widgets/` e intégralos en `main_window.py`. Por favor, evita sobrecargar `main_window.py`.
*   **Añadir nuevos diálogos de análisis**: Crea una nueva clase `QDialog` en `gui/dialogs/` y conéctala a la aplicación principal.
*   **Pulido de UI/UX**: Mejora el tema visual en `gui/theme.py` o mejora la adaptabilidad y el diseño (layouts).

### ⚙️ Backend (`core/`)
El backend es completamente local y basado en archivos. Gestiona la persistencia de datos, el análisis sintáctico de archivos (parsing) y la lógica de negocio sin necesidad de un servidor de bases de datos.
*   **Estructuras de Datos en Memoria (EDDs)**: `core/project.py` mantiene diccionarios en memoria de alto rendimiento (`codes_dict`, `themes_dict`, `texts_dict`). Esto permite tiempos de lectura instantáneos O(1) al consultar fragmentos codificados o al buscar texto, optimizando enormemente el proceso de análisis.
*   **Lógica de Persistencia Atómica**: Los proyectos se almacenan en una estructura de carpetas estándar que contiene archivos JSON (`project_data.json`, `edds_data.json`). El backend utiliza un `PointerManager` para guardados atómicos, asegurando que, incluso si la aplicación se bloquea a mitad de un guardado, el estado del proyecto no se corrompa.
*   **Sincronización Dinámica de Texto (Diff-Match-Patch)**: Cuando el usuario edita un documento, el backend utiliza un algoritmo `diff_match_patch` (con una tolerancia de umbral de `0.3`) para localizar y resincronizar automáticamente los índices `start` y `end` de los fragmentos codificados existentes. Si una oración se sobrescribe por completo, el fragmento de código asociado se elimina silenciosamente para mantener la integridad de los datos.
*   **Lógica de Importación**: Los formatos compatibles (TXT, PDF, DOCX, imágenes) se procesan al importarlos. Los documentos de texto se convierten en cadenas de texto sin formato y se almacenan internamente, mientras que las imágenes se copian directamente en la carpeta `/documentos` del proyecto.

**Cómo contribuir al Backend:**
*   **Añadir nuevos formatos de documento**: Amplía `core/project.py` para procesar nuevos tipos de archivos (p. ej., CSV o Markdown) e intégralos en la estructura del proyecto.
*   **Mejorar las funcionalidades de Exportación**: Ayuda a construir mejores manejadores de exportación en `core/export_manager.py` (p. ej., exportando a nuevos formatos como HTML o SPSS).
*   **Integridad de Datos y Testing**: Añade pruebas unitarias (unit tests) para la persistencia y las transformaciones de datos para asegurar que el estado JSON nunca se corrompa.

## 🔄 Flujo de Trabajo para Contribuir

1. **Crea una rama (Branch)**: Crea una nueva rama para tu nueva característica o corrección de errores (`git checkout -b feature/mi-nueva-caracteristica`).
2. **Escribe el código**: Realiza tus cambios manteniendo la separación de responsabilidades (Widgets modulares del Frontend en `gui/widgets/`, Backend en `core/`). Evita modificar archivos heredados como `gui_raizQA.py` y el directorio `models/`.
3. **Commit**: Escribe mensajes de commit claros y concisos.
4. **Push**: Sube tu rama a tu fork.
5. **Pull Request**: Abre un PR hacia la rama `NewStructure` (o `main`, según el destino). Proporciona una descripción clara de lo que resuelve o añade tu PR.
