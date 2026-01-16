# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os
from pathlib import Path

from setuptools import setup

VERSION = os.environ.get("BUILD_VERSION")
if VERSION is None:
    VERSION = Path("../VERSION").read_text().strip()

setup(
    version=VERSION,
)
