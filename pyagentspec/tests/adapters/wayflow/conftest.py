# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pathlib import Path
from typing import Any

from ..conftest import skip_tests_if_dependency_not_installed


def pytest_collection_modifyitems(config: Any, items: Any):
    # We skip all the tests in this folder if wayflow is not installed
    skip_tests_if_dependency_not_installed(
        module_name="wayflowcore",
        directory=Path(__file__).parent,
        items=items,
    )
