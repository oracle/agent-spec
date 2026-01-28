# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.adapters.crewai._agentspecconverter import CrewAIToAgentSpecConverter
from pyagentspec.adapters.crewai._types import CrewAIAgent, CrewAIComponent, CrewAIFlow
from pyagentspec.component import Component
from pyagentspec.serialization import AgentSpecSerializer as PyAgentSpecSerializer


class AgentSpecExporter:
    """Helper class to convert CrewAI objects to Agent Spec configurations."""

    def to_yaml(self, crewai_component: CrewAIComponent) -> str:
        """
        Transform the given CrewAI component into the respective Agent Spec YAML representation.

        Parameters
        ----------

        crewai_component:
            CrewAI Component to serialize to an Agent Spec configuration.
        """
        agentlang_assistant = self.to_component(crewai_component)
        return PyAgentSpecSerializer().to_yaml(agentlang_assistant)

    def to_json(self, crewai_component: CrewAIComponent) -> str:
        """
        Transform the given CrewAI component into the respective Agent Spec JSON representation.

        Parameters
        ----------

        crewai_component:
            CrewAI Component to serialize to an Agent Spec configuration.
        """
        agentlang_assistant = self.to_component(crewai_component)
        return PyAgentSpecSerializer().to_json(agentlang_assistant)

    def to_component(self, crewai_component: CrewAIComponent) -> Component:
        """
        Transform the given CrewAI component into the respective PyAgentSpec Component.

        Parameters
        ----------

        crewai_component:
            CrewAI Component to serialize to a corresponding PyAgentSpec Component.
        """
        if not isinstance(crewai_component, (CrewAIAgent, CrewAIFlow)):
            raise TypeError(
                f"Expected an Agent of Flow, but got '{type(crewai_component)}' instead"
            )
        return CrewAIToAgentSpecConverter().convert(crewai_component)
