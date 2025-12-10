# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os
from pathlib import Path
from typing import Any

import pytest

from ..conftest import skip_tests_if_dependency_not_installed


def pytest_collection_modifyitems(config: Any, items: Any):
    # We skip all the tests in this folder if crewai is not installed
    skip_tests_if_dependency_not_installed(
        module_name="crewai",
        directory=Path(__file__).parent,
        items=items,
    )


@pytest.fixture(scope="package", autouse=True)
def _disable_tracing():
    """Disable the automatic tracing of crewai"""
    old_value = os.environ.get("CREWAI_DISABLE_TELEMETRY", None)
    os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
    try:
        yield
    finally:
        if old_value is not None:
            os.environ["CREWAI_DISABLE_TELEMETRY"] = old_value
