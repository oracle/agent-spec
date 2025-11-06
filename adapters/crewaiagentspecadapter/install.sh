#!/bin/bash
#
# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0 as shown at  https://oss.oracle.com/licenses/upl/

source ../../_installation_tools.sh

upgrade_pip

python -m pip install -e . -c constraints/constraints.txt
