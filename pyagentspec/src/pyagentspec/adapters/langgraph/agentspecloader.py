# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


from typing import Any, Dict, List, Optional, Union, cast, overload

from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter
from pyagentspec.adapters.langgraph._types import Checkpointer, CompiledStateGraph, RunnableConfig
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.serialization import AgentSpecDeserializer, ComponentDeserializationPlugin
from pyagentspec.serialization.types import ComponentsRegistryT as AgentSpecComponentsRegistryT


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

    @overload
    def load_yaml(self, serialized_assistant: str) -> CompiledStateGraph[Any, Any, Any]: ...

    @overload
    def load_yaml(
        self,
        serialized_assistant: str,
        components_registry: Optional[AgentSpecComponentsRegistryT],
    ) -> CompiledStateGraph[Any, Any, Any]: ...

    @overload
    def load_yaml(
        self,
        serialized_assistant: str,
        *,
        import_only_referenced_components: bool,
    ) -> Union[CompiledStateGraph[Any, Any, Any], Dict[str, AgentSpecComponent]]: ...

    @overload
    def load_yaml(
        self,
        serialized_assistant: str,
        components_registry: Optional[AgentSpecComponentsRegistryT],
        import_only_referenced_components: bool,
    ) -> Union[CompiledStateGraph[Any, Any, Any], Dict[str, AgentSpecComponent]]: ...

    def load_yaml(
        self,
        serialized_assistant: str,
        components_registry: Optional[AgentSpecComponentsRegistryT] = None,
        import_only_referenced_components: bool = False,
    ) -> Union[CompiledStateGraph[Any, Any, Any], Dict[str, AgentSpecComponent]]:
        """
        Transform the given Agent Spec YAML into LangGraph components, with support for
        disaggregated configurations.

        Parameters
        ----------
        serialized_assistant:
            Serialized Agent Spec configuration.
        components_registry:
            Optional registry of Agent Spec components/values to resolve references while
            deserializing the main component or referenced components.
        import_only_referenced_components:
            When True, load only the referenced/disaggregated components and return a
            dictionary mapping component id to Agent Spec components. These components can
            be used as the ``components_registry`` when loading the main configuration.
            When False, load the main component and return the compiled LangGraph graph.
        """
        deserializer = AgentSpecDeserializer(plugins=self.plugins)
        if import_only_referenced_components:
            # Load and return the disaggregated Agent Spec components
            agentspec_referenced_components = deserializer.from_yaml(
                serialized_assistant,
                components_registry=components_registry,
                import_only_referenced_components=True,
            )
            return agentspec_referenced_components

        # Else, load the main component
        agentspec_assistant = deserializer.from_yaml(
            serialized_assistant,
            components_registry=components_registry,
            import_only_referenced_components=False,
        )
        return self.load_component(agentspec_assistant)

    @overload
    def load_json(self, serialized_assistant: str) -> CompiledStateGraph[Any, Any, Any]: ...

    @overload
    def load_json(
        self,
        serialized_assistant: str,
        components_registry: Optional[AgentSpecComponentsRegistryT],
    ) -> CompiledStateGraph[Any, Any, Any]: ...

    @overload
    def load_json(
        self,
        serialized_assistant: str,
        *,
        import_only_referenced_components: bool,
    ) -> Union[CompiledStateGraph[Any, Any, Any], Dict[str, AgentSpecComponent]]: ...

    @overload
    def load_json(
        self,
        serialized_assistant: str,
        components_registry: Optional[AgentSpecComponentsRegistryT],
        import_only_referenced_components: bool,
    ) -> Union[CompiledStateGraph[Any, Any, Any], Dict[str, AgentSpecComponent]]: ...

    def load_json(
        self,
        serialized_assistant: str,
        components_registry: Optional[AgentSpecComponentsRegistryT] = None,
        import_only_referenced_components: bool = False,
    ) -> Union[CompiledStateGraph[Any, Any, Any], Dict[str, AgentSpecComponent]]:
        """
        Transform the given Agent Spec JSON into LangGraph components, with support for
        disaggregated configurations.

        Parameters
        ----------
        serialized_assistant:
            Serialized Agent Spec configuration.
        components_registry:
            Optional registry of Agent Spec components/values to resolve references while
            deserializing the main component or referenced components.
        import_only_referenced_components:
            When True, load only the referenced/disaggregated components and return a
            dictionary mapping component id to Agent Spec components. These components can
            be used as the ``components_registry`` when loading the main configuration.
            When False, load the main component and return the compiled LangGraph graph.
        """
        deserializer = AgentSpecDeserializer(plugins=self.plugins)
        if import_only_referenced_components:
            # Load and return the disaggregated Agent Spec components
            agentspec_referenced_components = deserializer.from_json(
                serialized_assistant,
                components_registry=components_registry,
                import_only_referenced_components=True,
            )
            return agentspec_referenced_components

        # Else, load the main component
        agentspec_assistant = deserializer.from_json(
            serialized_assistant,
            components_registry=components_registry,
            import_only_referenced_components=False,
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
