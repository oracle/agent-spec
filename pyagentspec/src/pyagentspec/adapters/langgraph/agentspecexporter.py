# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec import Component as AgentSpecComponent
from pyagentspec.adapters.langgraph._agentspecconverter import LangGraphToAgentSpecConverter
from pyagentspec.adapters.langgraph._types import CompiledStateGraph, LangGraphComponent, StateGraph
from pyagentspec.serialization import AgentSpecSerializer as PyAgentSpecSerializer


class AgentSpecExporter:
    """Helper class to convert LangGraph objects into Agent Spec configuration."""

    def to_yaml(self, langgraph_component: LangGraphComponent) -> str:
        """
        Transform the given LangGraph component into the respective AgentSpec YAML representation

        Parameters
        ----------

        langgraph_component:
            LangGraph Component to serialize to an AgentSpec configuration
        """
        assistant = self.to_component(langgraph_component)
        return PyAgentSpecSerializer().to_yaml(assistant)

    def to_json(self, langgraph_component: LangGraphComponent) -> str:
        """
        Transform the given LangGraph component into the respective AgentSpec JSON representation

        Parameters
        ----------

        langgraph_component:
            LangGraph Component to serialize to an AgentSpec configuration
        """
        assistant = self.to_component(langgraph_component)
        return PyAgentSpecSerializer().to_json(assistant)

    def to_component(self, langgraph_component: LangGraphComponent) -> AgentSpecComponent:
        """
        Transform the given LangGraph component into the respective PyAgentSpec Component.

        Parameters
        ----------

        langgraph_component:
            LangGraph Component to serialize to a corresponding PyAgentSpec Component.
        """
        if not isinstance(langgraph_component, (StateGraph, CompiledStateGraph)):
            raise TypeError(
                f"Expected a LangGraph Component, but got '{type(langgraph_component)}' instead"
            )
        return LangGraphToAgentSpecConverter().convert(langgraph_component)
