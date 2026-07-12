#!/bin/bash

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

# 1. Clonar o actualizar el repositorio
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${GREEN}[+] RaizQA ya está instalado en $INSTALL_DIR. Buscando actualizaciones...${NC}"
    cd "$INSTALL_DIR"
    git pull origin main
else
    echo -e "${GREEN}[+] Descargando RaizQA por primera vez...${NC}"
    git clone https://github.com/Lorenzo-Vives/RaizQA "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 2. Asegurar que el launcher tenga permisos de ejecución
echo -e "${GREEN}[+] Configurando permisos del sistema...${NC}"
chmod +x "$INSTALL_DIR/RaizQALauncher.app/Contents/MacOS/RaizQA"

# 3. Crear un acceso directo en el Escritorio (Opcional pero útil)
echo -e "${GREEN}[+] Creando acceso directo en tu Escritorio...${NC}"
ln -sf "$INSTALL_DIR/RaizQALauncher.app" "$HOME/Desktop/RaizQA"

# 4. Iniciar la aplicación
echo -e "${GREEN}[+] ¡Todo listo! Iniciando RaizQA...${NC}"
echo -e "La primera vez puede tardar unos segundos mientras instala los componentes necesarios."
open "$INSTALL_DIR/RaizQALauncher.app"

echo ""
echo -e "${BLUE}=======================================${NC}"
echo -e "Instalación completada. Puedes cerrar esta terminal."
