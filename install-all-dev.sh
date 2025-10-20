#!/bin/bash
#
# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

source ./_installation_tools.sh

upgrade_pip_or_uv

# Install pyagentspec main module
install_dev_python_package pyagentspec

# Install also the adapters for the docs
install_dev_python_package adapters/autogenagentspecadapter
install_dev_python_package adapters/langgraphagentspecadapter
