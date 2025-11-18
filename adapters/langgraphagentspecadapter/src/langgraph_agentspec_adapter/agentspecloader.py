# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


from typing import Any, Dict, List, Optional

from langgraph.graph.state import CompiledStateGraph as LangGraphComponent
from langgraph.graph.state import RunnableConfig  # type: ignore[attr-defined]
from langgraph.types import Checkpointer
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.serialization import AgentSpecDeserializer, ComponentDeserializationPlugin

from langgraph_agentspec_adapter._langgraphconverter import AgentSpecToLangGraphConverter


class AgentSpecLoader:
    """Helper class to convert Agent Spec configuration into LangGraph objects."""

    def __init__(
        self,
        tool_registry: Optional[Dict[str, Any]] = None,
        plugins: Optional[List[ComponentDeserializationPlugin]] = None,
        checkpointer: Optional[Checkpointer] = None,
        config: Optional[RunnableConfig] = None,
    ) -> None:
        self.tool_registry = tool_registry or {}
        self.plugins = plugins
        self.checkpointer = checkpointer
        self.config = config

    def load_yaml(self, serialized_assistant: str) -> LangGraphComponent[Any, Any, Any]:
        """
        Transform the given Agent Spec YAML representation into the respective LangGraph Component

        Parameters
        ----------

        serialized_assistant:
            SerializedAgent Spec configuration to be converted to a LangGraph Component.
        """
        agentspec_assistant = AgentSpecDeserializer(plugins=self.plugins).from_yaml(
            serialized_assistant
        )
        return self.load_component(agentspec_assistant)

    def load_json(self, serialized_assistant: str) -> LangGraphComponent[Any, Any, Any]:
        """
        Transform the given Agent Spec JSON representation into the respective LangGraph Component

        Parameters
        ----------

        serialized_assistant:
            Serialized Agent Spec configuration to be converted to a LangGraph Component.
        """
        agentspec_assistant = AgentSpecDeserializer(plugins=self.plugins).from_json(
            serialized_assistant
        )
        return self.load_component(agentspec_assistant)

    def load_component(
        self, agentspec_component: AgentSpecComponent
    ) -> LangGraphComponent[Any, Any, Any]:
        """
        Transform the given PyAgentSpec Component into the respective LangGraph Component

        Parameters
        ----------

        agentspec_component:
            PyAgentSpec Component to be converted to a LangGraph Component.
        """
        langgraph_assistant = AgentSpecToLangGraphConverter().convert(
            agentspec_component=agentspec_component,
            tool_registry=self.tool_registry,
            checkpointer=self.checkpointer,
            config=self.config,
        )
        if not isinstance(langgraph_assistant, LangGraphComponent):
            raise TypeError(
                f"Expected an Agent of Flow, but got '{type(langgraph_assistant)}' instead"
            )
        return langgraph_assistant
