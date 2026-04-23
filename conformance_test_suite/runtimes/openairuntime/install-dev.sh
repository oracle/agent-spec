#!/bin/bash
#
# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# Use shared helpers for consistent local installs
source ../../../_installation_tools.sh

upgrade_pip

# Install this package in editable mode with dev requirements
install_requirements_dev
