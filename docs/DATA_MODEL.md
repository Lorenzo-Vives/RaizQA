# Modelo de datos y persistencia

## 1. Estructura de un proyecto

Cada proyecto se crea dentro del Working Directory con esta estructura base:

```text
<working_dir>/
`-- <nombre_proyecto>/
    |-- documentos/
    |-- codigos/
    |-- metadata.json
    |-- project_data.json
    |-- memos.json
    `-- diario.txt
```

## 2. Archivos principales

### `metadata.json`

Se usa para compatibilidad y contiene como minimo:

```json
{
  "name": "MiProyecto",
  "documents": ["entrevista_01.txt", "foto_01.jpg"]
}
```

### `project_data.json`

Es el estado principal del proyecto. Guarda:

- `codes`
- `documents`
- `highlights`
- `doc_groups`
- `themes`
- `case_studies`

### `memos.json`

Contiene memos asociados por nombre de codigo:

```json
{
  "Identidad": "Memo del codigo",
  "Territorio": "Otro memo"
}
```

### `diario.txt`

Guarda el texto libre del diario de codificacion.

## 3. Documento

Los documentos se administran desde `core/project.py`.

Tipos soportados:

- Texto: `.txt`, `.docx`, `.pdf`
- Imagen: `.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif`, `.tiff`

Reglas actuales:

- Los documentos de texto se almacenan como `.txt`.
- Las imagenes se copian sin conversion.

## 4. Estructura de codigo

Cada codigo en `project_data.json` sigue este esquema general:

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

- Hay una coexistencia entre memo por codigo dentro de `project_data.json` y `memos.json`.
- La ruta activa de la aplicacion usa `core/project.py` y `core/memos.py`.
- Existen modulos historicos en `models/` y archivos antiguos que no son la ruta principal actual.

## 12. Modulos responsables

- Persistencia del proyecto: `core/project.py`
- Persistencia de memos: `core/memos.py`
- Vista principal y reconstruccion de estado: `gui/main_window.py`
- Visor de imagenes y overlays: `gui/image_viewer.py`
