# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os
from typing import Any

import pytest


def pytest_collection_modifyitems(config: Any, items: Any):
    # We skip all the tests in this folder if crewai is not installed
    try:
        import crewai  # type: ignore

        dependency_missing = False
    except ImportError:
        dependency_missing = True

    for item in items:
        if dependency_missing:
            # If the dependency is missing we run only the test to check that the right error is raised
            if item.name != "test_import_raises_if_crewai_not_installed":
                item.add_marker(pytest.mark.skip(reason="CrewAI is not installed"))
        else:
            # If the dependency is installed we run all the tests except the one that checks the import error
            if item.name == "test_import_raises_if_crewai_not_installed":
                item.add_marker(pytest.mark.skip(reason="CrewAI is installed"))


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
