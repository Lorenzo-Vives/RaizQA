# RaizQA 🌱

RaizQA es un proyecto open source de análisis cualitativo en Python con PySide6, creado por Lorenzo Vives (Sociólogo, Magíster en Sociología PUC) con ayuda de CodexAI y ChatGPT-5.

## Instalación
- Descarga la última versión: RaizQA v1.5 — https://github.com/Lorenzo-Vives/RaizQA/releases/download/v.1.6/RaizQA.exe
## ⚠️ Nota: Windows puede mostrar una advertencia. Usa “Más información” → “Ejecutar de todas formas”.

## Crear un .app en macOS
1) Instala dependencias en un entorno virtual:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pyinstaller
```
2) Empaqueta con PyInstaller usando el spec macOS:
```bash
pyinstaller --clean RaizQA_macos.spec
```
3) El bundle queda en `dist/RaizQA.app` (abre con doble clic).  
Opcional: coloca un icono `.icns` y actualiza `icon=` en `RaizQA_macos.spec`.

## Flujo básico de uso
1) Selecciona un Working Directory donde se guardan los proyectos.  
2) Crea un proyecto nuevo o abre uno existente.  
3) Importa documentos .txt, .pdf o .docx (se convierten a texto plano) o imagenes (.png, .jpg, .jpeg, .bmp, .gif, .tiff) para verlas y codificarlas.  
4) Selecciona texto para crear códigos y subcódigos (árbol jerárquico).  
5) Clic derecho en un código para crear/editar memos (con corrector ortográfico).  
6) Lleva tu diario de codificación (botón Diario) y expórtalo a Word con “Exportar diario”.  
7) Exporta el libro de códigos a Excel y los fragmentos a Word con “Exportar códigos”.  
8) Usa “Ver Códigos” para visualizar todos los fragmentos codificados.

## Guardado automático
El proyecto se guarda automáticamente cada 30 segundos.

## Tecnologías
- Python  
- PySide6  
- IA: CodexAI y ChatGPT-5

## Licencia
MIT License — Copyright (c) 2025 Lorenzo Vives
