# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import importlib.util
from typing import Any, List

import pytest


def pytest_configure(config: Any) -> None:
    config.addinivalue_line(
        "markers",
        "requires_litellm: marks tests that require the optional litellm dependency",
    )


def pytest_collection_modifyitems(config: Any, items: List[pytest.Item]) -> None:
    if importlib.util.find_spec("litellm") is not None:
        return

    skip_litellm = pytest.mark.skip(reason="`litellm` is not installed")
    for item in items:
        if "requires_litellm" in item.keywords:
            item.add_marker(skip_litellm)
