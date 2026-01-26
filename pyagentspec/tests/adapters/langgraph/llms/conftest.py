# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.llms.llmgenerationconfig import LlmGenerationConfig


@pytest.fixture
def default_generation_parameters() -> LlmGenerationConfig:
    return LlmGenerationConfig(temperature=0.4, max_tokens=256, top_p=0.9)
