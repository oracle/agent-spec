# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Tests for bare LlmConfig adapter dispatch via CrewAI."""

import pytest

from pyagentspec.llms import LlmConfig


@pytest.fixture
def bare_llmconfig_unsupported() -> LlmConfig:
    return LlmConfig(name="test", model_id="some-model", api_provider="unsupported_provider")


class TestCrewAiDispatch:
    def test_unsupported_provider_raises(self, bare_llmconfig_unsupported: LlmConfig) -> None:
        from pyagentspec.adapters.crewai._crewaiconverter import CrewAiConverter

        converter = CrewAiConverter()
        with pytest.raises(NotImplementedError, match="unsupported_provider"):
            converter._llm_convert_to_crewai(bare_llmconfig_unsupported)
