# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import List, Optional

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from pyagentspec.agent import Agent
from pyagentspec.agenticcomponent import AgenticComponent
from pyagentspec.component import ComponentWithIO
from pyagentspec.property import Property, deduplicate_properties_by_title_and_type
from pyagentspec.templating import get_placeholder_properties_from_json_object
from pyagentspec.tools.tool import Tool
from pyagentspec.versioning import AgentSpecVersionEnum


class AgentSpecializationParameters(ComponentWithIO):
    """Parameters used to specialize an agent for a certain goal or task."""

    additional_instructions: Optional[str] = None
    """Additional instructions that will be merged with the generic agent's system prompt."""

    additional_tools: Optional[List[Tool]] = None
    """Additional tool set that will extend the generic agent's tools."""

    human_in_the_loop: Optional[bool] = None
    """Overwrites the generic agent's human_in_the_loop behaviour, if not None."""

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v25_4_2, init=False, exclude=True
    )

    def _get_inferred_inputs(self) -> List[Property]:
        # Extract all the placeholders in the prompt and make them string inputs by default
        return get_placeholder_properties_from_json_object(
            getattr(self, "additional_instructions", "") or ""
        )

    def _get_inferred_outputs(self) -> List[Property]:
        return []


class SpecializedAgent(AgenticComponent):
    """
    A specialized agent is an agent that uses an existing generic agent and
    specializes it to solve a given task.

    It can be executed anywhere an Agent can be executed.

    Examples
    --------
    >>> from pyagentspec.agent import Agent
    >>> from pyagentspec.property import StringProperty
    >>> from pyagentspec.specialized_agent import AgentSpecializationParameters, SpecializedAgent
    >>> from pyagentspec.tools import ServerTool
    >>> expertise_property = StringProperty(title="domain_of_expertise")
    >>> system_prompt = '''You are an expert in {{domain_of_expertise}}.
    ... Please help the users with their requests.'''
    >>> agent = Agent(
    ...     name="Adaptive expert agent",
    ...     system_prompt=system_prompt,
    ...     llm_config=llm_config,
    ...     inputs=[expertise_property],
    ... )
    >>> websearch_tool = ServerTool(
    ...     name="websearch_tool",
    ...     description="Search the web for information",
    ...     inputs=[StringProperty(title="query")],
    ...     outputs=[StringProperty(title="search_result")],
    ... )
    >>> agent_specialization_parameters = AgentSpecializationParameters(
    ...     name="essay_agent",
    ...     additional_instructions="Your goal is to help the user write an essay around the domain of expertise.",
    ...     additional_tools=[websearch_tool]
    ... )

    """

    agent: Agent
    """Agent to be specialized"""

    agent_specialization_parameters: AgentSpecializationParameters
    """Parameters used to specialize the agent"""

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v25_4_2, init=False, exclude=True
    )

    def _get_inferred_inputs(self) -> List[Property]:
        inputs_from_agent = (self.agent.inputs or []) if getattr(self, "agent", None) else []
        inputs_from_specialization_parameters = (
            (self.agent_specialization_parameters.inputs or [])
            if getattr(self, "agent_specialization_parameters", None)
            else []
        )
        return deduplicate_properties_by_title_and_type(
            inputs_from_agent + inputs_from_specialization_parameters
        )

    def _get_inferred_outputs(self) -> List[Property]:
        outputs_from_agent = (self.agent.outputs or []) if getattr(self, "agent", None) else []
        outputs_from_specialization_parameters = (
            (self.agent_specialization_parameters.outputs or [])
            if getattr(self, "agent_specialization_parameters", None)
            else []
        )
        return deduplicate_properties_by_title_and_type(
            outputs_from_agent + outputs_from_specialization_parameters
        )
