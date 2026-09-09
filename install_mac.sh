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

python_is_compatible() {
    local candidate="$1"

    [ -x "$candidate" ] && \
        "$candidate" -c \
            'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
            >/dev/null 2>&1
}

find_compatible_python() {
    local candidate

    for candidate in \
        "/opt/homebrew/bin/python3" \
        "/usr/local/bin/python3" \
        "/Library/Frameworks/Python.framework/Versions/Current/bin/python3"
    do
        if python_is_compatible "$candidate"; then
            printf '%s' "$candidate"
            return 0
        fi
    done

    if command -v python3 >/dev/null 2>&1; then
        candidate="$(command -v python3)"
        if python_is_compatible "$candidate"; then
            printf '%s' "$candidate"
            return 0
        fi
    fi

    return 1
}

find_homebrew() {
    local candidate

    for candidate in "/opt/homebrew/bin/brew" "/usr/local/bin/brew"; do
        if [ -x "$candidate" ]; then
            printf '%s' "$candidate"
            return 0
        fi
    done

    if command -v brew >/dev/null 2>&1; then
        command -v brew
        return 0
    fi

    return 1
}

# Buscar primero un Python ya instalado. Si no hay uno compatible, instalarlo
# mediante Homebrew. Se usan rutas absolutas porque las aplicaciones abiertas
# desde Finder no siempre heredan el PATH configurado en la Terminal.
PYTHON_BIN="$(find_compatible_python || true)"

if [ -z "$PYTHON_BIN" ]; then
    HOMEBREW_BIN="$(find_homebrew || true)"

    if [ -z "$HOMEBREW_BIN" ]; then
        echo "RaizQA necesita Python 3.10 o superior."
        echo ""
        echo "No se encontró Homebrew, que se utiliza para instalar Python."
        echo "Copia y pega este comando en la Terminal:"
        echo ""
        echo '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        echo ""
        echo "Cuando termine, vuelve a ejecutar el instalador de RaizQA."
        exit 1
    fi

    echo -e "${GREEN}[+] Instalando una versión compatible de Python...${NC}"
    "$HOMEBREW_BIN" install python

    HOMEBREW_PREFIX="$("$HOMEBREW_BIN" --prefix)"
    PYTHON_BIN="$HOMEBREW_PREFIX/bin/python3"

    if ! python_is_compatible "$PYTHON_BIN"; then
        echo "Error: Homebrew no pudo proporcionar Python 3.10 o superior."
        echo "Actualiza Homebrew con 'brew update' y vuelve a intentarlo."
        exit 1
    fi
fi

PYTHON_VERSION="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')"
echo -e "${GREEN}[+] Python compatible encontrado: $PYTHON_VERSION${NC}"

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
RAIZQA_PYTHON="$PYTHON_BIN" open "$INSTALL_DIR/RaizQALauncher.app"

echo ""
echo -e "${BLUE}=======================================${NC}"
echo -e "Instalación completada. Puedes cerrar esta terminal."
