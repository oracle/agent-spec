#!/bin/bash
#
# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

# Default Python version
PYTHON_CMD="python3.10"

# Check if the selected Python version is available
if ! command -v "$PYTHON_CMD" &> /dev/null; then
  echo -e "\e[31mError: Python command '$PYTHON_CMD' not found. Please make sure it's installed.\e[0m"
  exit 1
fi

source ./_installation_tools.sh

create_venv

setup_pypi_mirror

upgrade_pip_or_uv

./install-all-dev.sh

pre-commit install && echo -e "${GREEN}Successfully installed pre-commit hooks${NC}"
