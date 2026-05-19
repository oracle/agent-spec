# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import importlib.util
from pathlib import Path
from typing import Any, List

import pytest

EVALUATION_REQUIRED_MODULES = ("numpy", "pandas")
EVALUATION_TESTS_DIR = Path(__file__).parent


def pytest_configure(config: Any) -> None:
    config.addinivalue_line(
        "markers",
        "requires_litellm: marks tests that require the optional litellm dependency",
    )


def _has_evaluation_required_modules() -> bool:
    return all(
        importlib.util.find_spec(module) is not None for module in EVALUATION_REQUIRED_MODULES
    )


def pytest_collection_modifyitems(config: Any, items: List[pytest.Item]) -> None:
    if not _has_evaluation_required_modules():
        skip_evaluation = pytest.mark.skip(reason="evaluation dependencies are not installed")
        for item in items:
            if item.path.is_relative_to(EVALUATION_TESTS_DIR):
                item.add_marker(skip_evaluation)
        return

    if importlib.util.find_spec("litellm") is not None:
        return

    skip_litellm = pytest.mark.skip(reason="`litellm` is not installed")
    for item in items:
        if "requires_litellm" in item.keywords:
            item.add_marker(skip_litellm)
