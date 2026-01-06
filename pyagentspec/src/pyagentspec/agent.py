# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines several Agent Spec components."""

from typing import List

from pydantic import Field, SerializeAsAny

from pyagentspec.agenticcomponent import AgenticComponent
from pyagentspec.llms.llmconfig import LlmConfig
from pyagentspec.property import Property
from pyagentspec.templating import get_placeholder_properties_from_json_object
from pyagentspec.tools.tool import Tool
from pyagentspec.tools.toolbox import ToolBox
from pyagentspec.versioning import AgentSpecVersionEnum


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
    toolboxes: List[SerializeAsAny[ToolBox]] = Field(default_factory=list)
    """List of toolboxes that are passed to the agent."""
    human_in_the_loop: bool = True
    """Flag that determines if the Agent can request input from the user."""

    def _get_inferred_inputs(self) -> List[Property]:
        # Extract all the placeholders in the prompt and make them string inputs by default
        return get_placeholder_properties_from_json_object(getattr(self, "system_prompt", ""))

    def _get_inferred_outputs(self) -> List[Property]:
        return self.outputs or []

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = set()
        if agentspec_version < AgentSpecVersionEnum.v25_4_2:
            fields_to_exclude.add("toolboxes")
            fields_to_exclude.add("human_in_the_loop")
        return fields_to_exclude

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        parent_min_version = super()._infer_min_agentspec_version_from_configuration()
        current_object_min_version = self.min_agentspec_version
        if self.toolboxes or not self.human_in_the_loop:
            # We first check if the component requires toolboxes)
            # If that's the case, we set the min version to 25.4.2, when toolboxes were introduced
            # Similarly, human_in_the_loop was only added in 25.4.2 (human_in_the_loop=True was
            # the de-facto default before)
            current_object_min_version = AgentSpecVersionEnum.v25_4_2
        return max(parent_min_version, current_object_min_version)
