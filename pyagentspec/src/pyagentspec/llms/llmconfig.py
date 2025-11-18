# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the base class for all LLM configuration component."""

from typing import Any, Optional

from pyagentspec.component import Component
from pyagentspec.llms.llmgenerationconfig import LlmGenerationConfig


class LlmConfig(Component, abstract=True):
    """
    A LLM configuration defines how to connect to a LLM to do generation requests.

    This class provides the base class, while concrete classes provide the required
    configuration to connect to specific LLM providers.
    """

    default_generation_parameters: Optional[LlmGenerationConfig] = None
    """Parameters used for the generation call of this LLM"""
