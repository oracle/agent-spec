# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""This module defines several Agent Spec components."""

from typing import List

from pydantic import Field, SerializeAsAny

from pyagentspec.agenticcomponent import AgenticComponent
from pyagentspec.llms.llmconfig import LlmConfig
from pyagentspec.property import Property
from pyagentspec.templating import get_placeholder_properties_from_string
from pyagentspec.tools.tool import Tool


class Agent(AgenticComponent):
    """
    An agent is a component that can do several rounds of conversation to solve a task.

    It can be executed by itself, or be executed in a flow using an AgentNode.


    Examples
    --------
    >>> from pyagentspec.agent import Agent
    >>> from pyagentspec.property import Property
    >>> expertise_property=Property(
    ...     json_schema={"title": "domain_of_expertise", "type": "string"}
    ... )
    >>> system_prompt = '''You are an expert in {{domain_of_expertise}}.
    ... Please help the users with their requests.'''
    >>> agent = Agent(
    ...     name="Adaptive expert agent",
    ...     system_prompt=system_prompt,
    ...     llm_config=llm_config,
    ...     inputs=[expertise_property],
    ... )

    """

    llm_config: SerializeAsAny[LlmConfig]
    """Configuration of the LLM to use for this Agent"""
    system_prompt: str
    """Initial system prompt used for the initialization of the agent's context"""
    tools: List[SerializeAsAny[Tool]] = Field(default_factory=list)
    """List of tools that the agent can use to fulfil user requests"""

    def _get_inferred_inputs(self) -> List[Property]:
        # Extract all the placeholders in the prompt and make them string inputs by default
        return get_placeholder_properties_from_string(getattr(self, "system_prompt", ""))

    def _get_inferred_outputs(self) -> List[Property]:
        return self.outputs or []
