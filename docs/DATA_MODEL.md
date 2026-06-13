# Modelo de datos y persistencia

La arquitectura actual sigue un patrón **MVC (Model-View-Controller)**, donde `core/project.py` y las Estructuras de Datos en Memoria (EDDs) actúan como el **Modelo**, y `core/logica.py` actúa como el **Controlador** que orquesta la persistencia y la lógica pesada.

## 1. Estructura de un proyecto

Cada proyecto se crea dentro del Working Directory con esta estructura base:

```text
<working_dir>/
`-- <nombre_proyecto>/
    |-- documentos/
    |-- codigos/
    |-- metadata.json
    |-- project_data.json
    `-- project_data.json.bak
```

## 2. Archivos principales

### `metadata.json`

Se usa principalmente para compatibilidad e indexación básica:

```json
{
  "name": "MiProyecto",
  "documents": ["entrevista_01.txt", "foto_01.jpg"]
}
```

### `project_data.json`

Es el estado principal unificado del proyecto y se guarda de forma atómica. Guarda todo:

- `documents` y `highlights`
- `codes_dict` (diccionario principal de códigos y subcódigos)
- `themes_dict` (temas y categorías)
- `memos_dict` (memos de la investigación)
- `doc_groups` y `case_studies`

### `project_data.json.bak`

Es el respaldo atómico generado automáticamente por el proceso de guardado para evitar corrupción de datos en caso de fallo durante la escritura.

## 3. Documento

Los documentos se administran desde `core/project.py`.

Tipos soportados:

- Texto: `.txt`, `.docx`, `.pdf`
- Imagen: `.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif`, `.tiff`

Reglas actuales:

- Los documentos de texto se almacenan como `.txt`.
- Las imagenes se copian sin conversion.

## 4. Estructura de codigo

Cada codigo en `project_data.json` sigue este esquema general. Ahora soporta **jerarquía de sub-códigos** de manera nativa:

```json
{
  "name": "Nombre del codigo",
  "parent": null,
  "memo": "",
  "color": "#ffcc00",
  "count": 3,
  "fragments": []
}
```

Campos:

- `name`: nombre del codigo
- `parent`: nombre del codigo padre o `null`
- `memo`: texto del memo integrado al estado del proyecto
- `color`: color hexadecimal del codigo
- `count`: cantidad de fragmentos
- `fragments`: lista de fragmentos asociados

## 5. Fragmentos de texto

Esquema habitual:

```json
{
  "text": "fragmento seleccionado",
  "document": "entrevista_01.txt",
  "start": 120,
  "end": 180,
  "color": "#ffcc00",
  "type": "text"
}
```

Campos:

- `text`: contenido seleccionado
- `document`: documento de origen
- `start`: posicion inicial en el texto
- `end`: posicion final en el texto
- `color`: color del codigo
- `type`: `"text"`

## 6. Fragmentos de imagen

Esquema actual:

```json
{
  "text": "Zona de imagen",
  "comment": "Zona de imagen",
  "document": "foto_01.jpg",
  "start": null,
  "end": null,
  "color": "#64b5f6",
  "type": "image",
  "rect": {
    "x": 120,
    "y": 80,
    "w": 240,
    "h": 160
  },
  "image_size": {
    "w": 1920,
    "h": 1080
  },
  "area": 38400,
  "coverage": 0.018519
}
```

Campos importantes:

- `type`: `"image"`
- `comment`: descripcion escrita por el usuario
- `rect`: coordenadas y tamano de la zona seleccionada
- `image_size`: resolucion original de la imagen
- `area`: area del rectangulo
- `coverage`: proporcion del area respecto a la imagen completa

### Regla clave

`rect` se guarda en coordenadas de la imagen original. Por eso la zona no se desplaza aunque el usuario haga zoom en el visor.

## 7. Highlights

`highlights` agrupa los fragmentos por documento para restaurar resaltados o overlays cuando el documento vuelve a abrirse.

Para texto:

- se reaplican rangos `start/end`

Para imagen:

- se redibujan overlays usando `rect`

## 8. Grupos de documentos

`doc_groups` representa carpetas de documentos creadas por el usuario:

```json
{
  "__root__": ["entrevista_01.txt"],
  "Grupo A": ["entrevista_02.txt", "foto_01.jpg"]
}
```

Uso:

- organizacion de corpus
- base para crear casos a partir de carpetas

## 9. Temas y categorias

`themes` guarda agrupaciones de codigos:

```json
[
  {
    "name": "Memoria",
    "codes": ["Recuerdo", "Infancia", "Archivo"]
  }
]
```

## 10. Casos

`case_studies` guarda casos y documentos asociados:

```json
[
  {
    "name": "Caso 1",
    "documents": ["entrevista_01.txt", "foto_01.jpg"],
    "characteristics": "Descripcion del caso",
    "comments": "Notas del analista"
  }
]
```

## 11. Compatibilidades y observaciones

- Archivos heredados como `memos.json` o `diario.txt` ya **no se usan**. Si existen, solo se leen como mecanismo de migración hacia `project_data.json` al cargar proyectos antiguos.
- Existen modulos historicos en el directorio `models/` que han sido completamente reemplazados por el patrón MVC de `core/`. No forman parte de la ruta principal actual.
- Se ha implementado una lógica de guardado atómico que garantiza que `project_data.json` nunca se corrompa, apoyándose en la creación temporal y renombrado con `project_data.json.bak`.

## 12. Modulos responsables (MVC)

- **Modelo**: `core/project.py` (Persistencia unificada en `project_data.json` y EDDs).
- **Controlador**: `core/logica.py` (Maneja las peticiones asíncronas, coordina el modelo y envía señales a la vista).
- **Vista**: `gui/main_window.py` (Recepción de señales y reconstrucción visual del estado) y `gui/widgets/`.
- Fusión y Colaboración: `core/merge_manager.py`, `core/import_manager.py`, `core/export_manager.py`
