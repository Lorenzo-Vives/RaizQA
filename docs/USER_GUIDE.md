# Guia de usuario

## 1. Que hace RaizQA

RaizQA es una aplicacion de analisis cualitativo orientada a trabajar con documentos de texto e imagen. El flujo general es:

1. Elegir un directorio de trabajo.
2. Crear o abrir un proyecto.
3. Importar documentos.
4. Codificar texto o zonas de imagen.
5. Organizar codigos, memos y temas.
6. Ejecutar vistas de analisis.
7. Exportar resultados.

## 2. Primer inicio

Al abrir la aplicacion aparece una ventana de bienvenida. Luego se muestra la ventana principal con tres areas:

- Navegacion superior y menus.
- Panel izquierdo con documentos y arbol de codigos.
- Panel central con el visor del documento activo.

## 3. Crear o abrir un proyecto

### Seleccionar Working Directory

Usa el boton `Seleccionar Working Directory`.

Ese directorio sera la carpeta base donde RaizQA guardara los proyectos.

### Crear proyecto

Usa `Crear Proyecto` y escribe un nombre.

RaizQA creara una carpeta con la estructura base del proyecto.

### Abrir proyecto

Usa `Abrir Proyecto` para listar carpetas disponibles dentro del Working Directory actual.

## 4. Importar documentos

Boton: `Importar Archivo`

Formatos admitidos:

- Texto plano: `.txt`
- Word: `.docx`
- PDF: `.pdf`
- Imagen: `.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif`, `.tiff`

Comportamiento:

- Los documentos de texto se almacenan como `.txt` dentro del proyecto.
- Las imagenes se copian al proyecto manteniendo su extension.

## 5. Organizar documentos

El panel izquierdo permite:

- Ver documentos importados.
- Crear carpetas de documentos.
- Mover documentos a carpetas.
- Eliminar documentos del proyecto.

Las carpetas tambien pueden reutilizarse despues para definir casos.

## 6. Codificacion de texto

Para codificar texto:

1. Abre un documento de texto.
2. Selecciona un fragmento.
3. Haz clic derecho.
4. Elige una opcion:
   - `Crear nuevo codigo`
   - `Crear subcodigo`
   - `Codificar in vivo`
   - `Agregar a codigo existente`

Cada fragmento guarda:

- documento de origen
- texto seleccionado
- posicion inicial
- posicion final
- color asociado al codigo

## 7. Codificacion de imagenes por zonas

RaizQA permite codificar imagenes por seleccion rectangular.

### Flujo

1. Abre una imagen importada.
2. Arrastra con el boton izquierdo para definir una zona.
3. Haz clic derecho sobre el visor.
4. Elige:
   - `Crear nuevo codigo para zona`
   - `Crear subcodigo para zona`
   - `Agregar a codigo existente`

Tambien puedes codificar la imagen completa si no hay una zona seleccionada.

### Como se guarda

Las zonas se guardan en coordenadas de la imagen original, no en coordenadas de pantalla. Eso evita que se pierdan o desplacen cuando haces zoom.

### Recomendacion de resolucion

Para una buena precision:

- Minimo util: 1200 px en el lado mas largo.
- Recomendado: 1800 a 3000 px en el lado mas largo.

## 8. Arbol de codigos

El arbol de codigos permite:

- Crear codigos y subcodigos.
- Ver frecuencia por codigo.
- Colapsar o expandir la jerarquia.
- Buscar codigos.
- Abrir fragmentos asociados.
- Acceder a memos por codigo.

Cada codigo tiene:

- nombre
- padre opcional
- color
- memo
- frecuencia
- lista de fragmentos

## 9. Memos

Haz clic derecho sobre un codigo para:

- Ver memo
- Agregar o editar memo
- Eliminar memo

El editor de memos integra corrector ortografico en espanol e ingles cuando la dependencia esta disponible.

## 10. Diario de codificacion

Boton: `Diario de codificacion`

Sirve para registrar:

- decisiones metodologicas
- observaciones durante el analisis
- reflexiones interpretativas

Exportacion:

- `Exportar diario` genera un archivo Word `.docx`

## 11. Ver codigos y fragmentos

Boton: `Ver Codigos`

Permite explorar los fragmentos codificados de todos los codigos.

Para imagenes, el visor muestra la imagen y enfoca la zona codificada.

## 12. Analisis disponibles

### Comparar documentos

Abre dos documentos en paralelo y resalta coincidencias de codigos compartidos.

### Code Matrix Browser

Muestra una matriz `codigo x documento`.

Modos disponibles:

- Tabla + Heatmap
- Heatmap
- Tabla

Escalas disponibles:

- Global
- Por fila
- Por documento

La matriz cuenta fragmentos por codigo en cada documento.

### Nube de palabras

Construye una nube de palabras a partir de uno o varios documentos con filtro de longitud minima.

### Temas y categorias

Permite agrupar codigos dentro de temas o categorias mediante arrastre.

### Analisis de temas

Resume temas y categorias con:

- cantidad de codigos
- cantidad total de fragmentos
- acceso a fragmentos por codigo

### Estudio de casos

Permite definir casos, asignar documentos y revisar fragmentos por caso.

## 13. Colaboración y Exportaciones

### Menú Colaborar

El menú **Colaborar** en la parte superior te permite trabajar en equipo:
- **Exportar Proyecto**: Genera un archivo empaquetado de tu proyecto y codificaciones para compartir.
- **Importar Proyecto**: Permite importar el proyecto empaquetado de un compañero.
- **Merge (Fusionar) Proyectos**: Integra las codificaciones de un compañero en tu proyecto activo, resolviendo conflictos de forma inteligente sin pérdida de datos.

### Exportar codigos

Genera un archivo Excel `.xlsx` con el sistema de codigos.

### Exportar diario

Genera un archivo Word `.docx` con el diario del proyecto.

## 14. Busqueda global

La barra superior permite buscar texto en:

- documentos
- nombres de codigos
- memos

Si hay coincidencias en documentos, RaizQA navega entre ellas.

## 15. Guardado automatico y Advertencias

El proyecto se guarda automaticamente cada 30 segundos.

Tambien puedes usar `Guardar Proyecto`.

Si intentas cerrar la aplicación y tienes cambios sin guardar, aparecerá un aviso de advertencia para evitar que pierdas tu progreso.

## 16. Consejos practicos

- Usa nombres de codigo consistentes desde el inicio.
- Trabaja con imagenes de resolucion media o alta si vas a codificar zonas.
- Usa carpetas de documentos para organizar corpus y para crear casos mas tarde.
- Exporta diario y codigos de forma periodica.

## 17. Problemas comunes

### No aparece un proyecto para abrir

Verifica que el Working Directory sea el correcto.

### Un PDF o DOCX no se importa bien

El resultado depende de la calidad del texto extraible del archivo original.

### El corrector ortografico no sugiere nada

Revisa que `pyspellchecker` este instalado.

### La imagen se ve borrosa para codificar

Busca una version con mayor resolucion. El zoom no inventa detalle si la imagen original es pequena.
