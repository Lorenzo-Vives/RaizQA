#!/bin/bash
set -euo pipefail
# Colores para la terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # Sin color

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}     Instalador de RaizQA (macOS)      ${NC}"
echo -e "${BLUE}=======================================${NC}"
echo ""

# Carpeta segura donde se instalará (fuera de Documentos para evitar bloqueos TCC)
INSTALL_DIR="$HOME/RaizQA"

# Verificar que Git esté instalado
if ! command -v git >/dev/null 2>&1; then
    echo "No se encontró Git en el sistema."
    echo "Instala las herramientas de desarrollo de macOS ejecutando:"
    echo "xcode-select --install"
    exit 1
fi

# 1. Clonar o actualizar el repositorio
if [ -d "$INSTALL_DIR/.git" ]; then
    echo -e "${GREEN}[+] RaizQA ya está instalado en $INSTALL_DIR. Buscando actualizaciones...${NC}"

    git -C "$INSTALL_DIR" pull --ff-only origin main

elif [ -e "$INSTALL_DIR" ]; then
    echo "Error: ya existe la carpeta $INSTALL_DIR,"
    echo "pero no corresponde a una instalación válida de RaizQA."
    echo ""
    echo "Renombra o elimina esa carpeta y vuelve a ejecutar el instalador."
    exit 1

else
    echo -e "${GREEN}[+] Descargando RaizQA por primera vez...${NC}"

    git clone \
        https://github.com/Lorenzo-Vives/RaizQA.git \
        "$INSTALL_DIR"
fi

# Verificar que los archivos esenciales existan
LAUNCHER="$INSTALL_DIR/RaizQALauncher.app/Contents/MacOS/RaizQA"

if [ ! -f "$INSTALL_DIR/main.py" ]; then
    echo "Error: no se encontró main.py en $INSTALL_DIR."
    echo "La instalación parece estar incompleta."
    exit 1
fi

if [ ! -f "$LAUNCHER" ]; then
    echo "Error: no se encontró el launcher de macOS."
    echo "La instalación parece estar incompleta."
    exit 1
fi

# 2. Asegurar que el launcher tenga permisos de ejecución
echo -e "${GREEN}[+] Configurando permisos del sistema...${NC}"
chmod +x "$LAUNCHER"

# 3. Crear un acceso directo en el Escritorio 
echo -e "${GREEN}[+] Creando acceso directo en tu Escritorio...${NC}"
# Eliminar accesos directos antiguos
rm -f "$HOME/Desktop/RaizQA"
rm -f "$HOME/Desktop/RaizQA.app"

# Crear el nuevo acceso directo conservando la extensión .app
ln -sfn \
    "$INSTALL_DIR/RaizQALauncher.app" \
    "$HOME/Desktop/RaizQA.app"

# 4. Iniciar la aplicación
echo -e "${GREEN}[+] ¡Todo listo! Iniciando RaizQA...${NC}"
echo -e "La primera vez puede tardar unos segundos mientras instala los componentes necesarios."
open "$INSTALL_DIR/RaizQALauncher.app"

echo ""
echo -e "${BLUE}=======================================${NC}"
echo -e "Instalación completada. Puedes cerrar esta terminal."
