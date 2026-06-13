# Guía de Pruebas de RaizQA

Este directorio contiene todas las pruebas automatizadas para garantizar la integridad, estabilidad y el correcto funcionamiento de la aplicación. Utilizamos **`pytest`** como nuestro framework de pruebas y **`pytest-qt`** para manejar adecuadamente nuestras pruebas de interfaz de usuario (UI) en PySide6.

## 📦 Dependencias

Para ejecutar estas pruebas, asegúrate de tener instaladas las dependencias requeridas:

``` bash
pip install pytest pytest-qt
```

## 🚀 Cómo Ejecutar las Pruebas

Puedes ejecutar las pruebas desde el directorio raíz del repositorio.

1.  **Ejecutar toda la suite de pruebas:**

    ``` bash
    pytest tests/
    ```

2.  **Ejecutar con salida detallada (muestra qué pruebas pasaron o fallaron):**

    ``` bash
    pytest -v tests/
    ```

3.  **Ejecutar un archivo de prueba específico:**

    ``` bash
    pytest tests/test_merge_manager.py
    ```

4.  **Ejecutar una función de prueba específica:**

    ``` bash
    pytest tests/test_edds.py::test_specific_function_name
    ```

## 🧩 Fixtures (`conftest.py`)

El archivo `conftest.py` proporciona "fixtures" compartidos que configuran automáticamente el estado necesario para las pruebas. Puedes inyectarlos en tus pruebas simplemente añadiéndolos como argumentos a tu función de prueba.

- **`temp_project`**: Crea un directorio de proyecto temporal y aislado utilizando `tmp_path` de pytest. Asegura que las pruebas que modifican el disco no corrompan los datos reales de los usuarios.
- **`qapp`**: Proporcionado por `pytest-qt`. Instancia un singleton de `QApplication`, necesario para cualquier prueba relacionada con la interfaz de usuario.
- **`logica`**: Instancia un `ControladorLogico` limpio (el backend central).
- **`main_window`**: Instancia la `RaizQAGUI`, conectando automáticamente las señales y slots (Signals and Slots) esenciales de Qt entre la interfaz y el backend (`logica`), tal como sucede en producción.

## 📂 Resumen de los Módulos de Prueba

A continuación, se detalla lo que cubre cada archivo de prueba:

- **`test_edds.py`**: Prueba las Estructuras de Datos en Memoria (EDDs). Garantiza que la creación, consulta y estructuración de códigos, temas y sub-códigos funcione de manera instantánea y confiable.
- **`test_file_creation.py`**: Prueba la configuración del proyecto y la lógica de persistencia. Verifica que los proyectos se inicialicen correctamente, generando los archivos `project_data.json`, `edds_data.json` y la carpeta `/documentos` necesarios.
- **`test_file_modification.py`**: Prueba la lógica de `diff_match_patch`. Cuando se edita un documento de texto, esto asegura que la aplicación resincronice correctamente los índices de coordenadas de inicio (`start`) y fin (`end`) de los fragmentos codificados existentes.
- **`test_gui.py`**: Pruebas de integración para la interfaz de usuario (UI). Simula interacciones del usuario (como hacer clic en botones o añadir códigos) y verifica que las señales de la `main_window` se comuniquen adecuadamente con el backend.
- **`test_import.py`**: Prueba la lógica de análisis (parsing) de documentos al añadirlos a un proyecto, asegurando que la extracción de texto funcione para los formatos de archivo compatibles.
- **`test_merge_manager.py`**: Prueba la lógica de trabajo en equipo y colaboración. Garantiza que el `MergeManager` maneje adecuadamente la fusión de códigos y la resolución de conflictos sin pérdida de datos cuando varios usuarios colaboran.
- **`test_project_import_export.py`**: Prueba la lógica completa de empaquetado del proyecto. Verifica que los proyectos se puedan exportar a archivos zip y posteriormente reimportar sin problemas.

## ✍️ Escribiendo Nuevas Pruebas

Cuando contribuyas con nuevas funcionalidades o correcciones de errores, por favor escribe sus pruebas correspondientes:

1.  **Utiliza `temp_project` para operaciones con archivos**: Nunca escribas pruebas que creen o modifiquen archivos en la carpeta raíz del proyecto. Inyecta siempre `temp_project` para que los archivos se escriban en una carpeta temporal y aislada que se limpia automáticamente.
2.  **Mantén las pruebas de UI aisladas**: Si estás probando una función de la lógica central, no necesitas la interfaz gráfica. Prueba las funciones del backend directamente. Si estás probando específicamente la interacción del usuario o las señales de Qt, inyecta el fixture `main_window`.
3.  **Uso de Mocks**: Utiliza `unittest.mock.patch` de Python si necesitas omitir los cuadros de diálogo de archivos o ventanas emergentes durante una prueba de interfaz de usuario.