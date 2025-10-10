# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper to run pip
run_pip() {
    python -m pip "$@"
}

install_with_pip() {
    run_pip install "$@"
}

# Creates a virtual environment
create_venv() {
    local VENV_DIR=".venv-agentspec"

    echo -e "${BLUE}Creating virtual environment using $PYTHON_CMD...${NC}"

    "$PYTHON_CMD" -m venv "$VENV_DIR"
    echo -e "${GREEN}Virtual environment created at .venv-agentspec${NC}"

    # Activate the environment
    source "$VENV_DIR/bin/activate"
    echo -e "${BLUE}Virtual environment activated.${NC}"
}

# Upgrades pip
upgrade_pip() {
    echo -e "${BLUE}Upgrading pip package installer...${NC}"
    install_with_pip --upgrade pip
}

# Checks if package already installed
prepare_package_installation() {
    package_name=$(basename "$1")

    if python -m pip show "$package_name" &> /dev/null; then
        echo -e "${GREEN}Package $package_name is already locally installed.${NC}"
        return 1
    else
        echo "Package $package_name not found. Installing from local source \"$1\" ..."

        if [ -d "$1" ]; then
            cd "$1"
            return 0
        else
            echo -e "${RED}Error: the local directory $package_name does not exist.  cwd: $(pwd)${NC}"
            exit 1
        fi
    fi
}

install_python_package() {
    prepare_package_installation "$1"
    install_status=$?

    if [ "$install_status" -eq 0 ]; then
        bash install.sh
        cd -
    fi
}

install_dev_python_package() {
    prepare_package_installation "$1"
    install_status=$?

    if [ "$install_status" -eq 0 ]; then
        bash install-dev.sh
        cd -
    fi
}

install_requirements_dev() {
    echo -e "Installing requirements-dev.txt from $(pwd)..."
    python -m pip install -r requirements-dev.txt
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}$(pwd)/requirements-dev.txt installed successfully${NC}"
    else
        echo -e "${RED}$(pwd)/requirements-dev.txt installation failed. Exiting.${NC}"
        exit 1
    fi
}
