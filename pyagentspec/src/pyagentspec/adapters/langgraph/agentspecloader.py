# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


from typing import Any, Dict, List, Optional, cast

from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter
from pyagentspec.adapters.langgraph._types import Checkpointer, CompiledStateGraph, RunnableConfig
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.serialization import AgentSpecDeserializer, ComponentDeserializationPlugin


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

    def load_yaml(self, serialized_assistant: str) -> CompiledStateGraph[Any, Any, Any]:
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

    def load_json(self, serialized_assistant: str) -> CompiledStateGraph[Any, Any, Any]:
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
    ) -> CompiledStateGraph[Any, Any, Any]:
        """
        Transform the given PyAgentSpec Component into the respective LangGraph Component

        Parameters
        ----------

        agentspec_component:
            PyAgentSpec Component to be converted to a LangGraph Component.
        """
        return cast(
            CompiledStateGraph[Any, Any, Any],
            AgentSpecToLangGraphConverter().convert(
                agentspec_component=agentspec_component,
                tool_registry=self.tool_registry,
                checkpointer=self.checkpointer,
                config=self.config,
            ),
        )
