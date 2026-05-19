# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.adapters.openaiagents._types import OAAgent


def test_import_raises_if_agents_not_installed():
    with pytest.raises(ImportError, match="Package agents is not installed."):
        OAAgent(name="assistant", instructions="You are helpful.", model="gpt-4.1", tools=[])
