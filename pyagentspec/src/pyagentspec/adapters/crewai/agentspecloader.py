# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


from typing import Dict, List, Optional, cast

from pyagentspec.adapters.crewai._crewaiconverter import AgentSpecToCrewAIConverter
from pyagentspec.adapters.crewai._types import (
    CrewAIComponent,
    CrewAIServerToolType,
)
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.serialization import AgentSpecDeserializer, ComponentDeserializationPlugin


class AgentSpecLoader:
    """Helper class to convert Agent Spec configurations to CrewAI objects."""

    def __init__(
        self,
        tool_registry: Optional[Dict[str, CrewAIServerToolType]] = None,
        plugins: Optional[List[ComponentDeserializationPlugin]] = None,
    ):
        """
        Parameters
        ----------

        tool_registry:
            Optional dictionary to enable converting/loading assistant configurations involving the
            use of tools. Keys must be the tool names as specified in the serialized configuration, and
            the values are the tool objects.
        plugins:
            Optional list of plugins to enable converting/loading assistant configurations involving
            non-core Agent Spec components.
        """
        self.tool_registry = tool_registry or {}
        self.plugins = plugins
        self._enable_agentspec_tracing = True

    def load_yaml(self, serialized_assistant: str) -> CrewAIComponent:
        """
        Transform the given Agent Spec YAML representation into the respective CrewAI Component

        Parameters
        ----------

        serialized_assistant:
            Serialized Agent Spec configuration to be converted to a CrewAI Component.
        """
        agentspec_assistant = AgentSpecDeserializer(plugins=self.plugins).from_yaml(
            serialized_assistant
        )
        return self.load_component(agentspec_assistant)

    def load_json(self, serialized_assistant: str) -> CrewAIComponent:
        """
        Transform the given Agent Spec JSON representation into the respective CrewAI Component

        Parameters
        ----------

        serialized_assistant:
            Serialized Agent Spec configuration to be converted to a CrewAI Component.
        """
        agentspec_assistant = AgentSpecDeserializer(plugins=self.plugins).from_json(
            serialized_assistant
        )
        return self.load_component(agentspec_assistant)

    def load_component(self, agentspec_component: AgentSpecComponent) -> CrewAIComponent:
        """
        Transform the given PyAgentSpec Component into the respective CrewAI Component

        Parameters
        ----------

        agentspec_component:
            PyAgentSpec Component to be converted to a CrewAI Component.
        """
        return cast(
            CrewAIComponent,
            AgentSpecToCrewAIConverter(
                enable_agentspec_tracing=self._enable_agentspec_tracing,
            ).convert(agentspec_component, self.tool_registry),
        )
