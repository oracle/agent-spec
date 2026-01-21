# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


from typing import Any, Dict, List, Optional, Union, cast, overload

from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter
from pyagentspec.adapters.langgraph._types import (
    Checkpointer,
    CompiledStateGraph,
    LangGraphComponentsRegistryT,
    LangGraphRuntimeComponent,
    RunnableConfig,
)
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.serialization import AgentSpecDeserializer, ComponentDeserializationPlugin
from pyagentspec.serialization.types import ComponentsRegistryT as AgentSpecComponentsRegistryT


class AgentSpecLoader:
    """Helper class to convert Agent Spec configuration into LangGraph objects.

    Parameters
    ----------
    tool_registry:
        Optional dictionary to enable converting/loading assistant configurations involving
        the use of tools. Keys must be the tool names as specified in the serialized
        configuration, and values are either LangGraph/LCEL tools (e.g., ``StructuredTool``)
        or plain callables that will be wrapped.
    plugins:
        Optional list of Agent Spec deserialization plugins. If omitted, the builtin
        plugins compatible with the latest supported Agent Spec version are used.
    checkpointer:
        Optional LangGraph checkpointer. If provided, it is wired into created graphs and
        enables features that require a checkpointer (e.g., client tools).
    config:
        Optional ``RunnableConfig`` to pass to created runnables/graphs.
    """

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
        components_registry: Optional[LangGraphComponentsRegistryT],
    ) -> CompiledStateGraph[Any, Any, Any]: ...

    @overload
    def load_yaml(
        self,
        serialized_assistant: str,
        *,
        import_only_referenced_components: bool,
    ) -> Union[CompiledStateGraph[Any, Any, Any], Dict[str, LangGraphRuntimeComponent]]: ...

    @overload
    def load_yaml(
        self,
        serialized_assistant: str,
        components_registry: Optional[LangGraphComponentsRegistryT],
        import_only_referenced_components: bool,
    ) -> Union[CompiledStateGraph[Any, Any, Any], Dict[str, LangGraphRuntimeComponent]]: ...

    def load_yaml(
        self,
        serialized_assistant: str,
        components_registry: Optional[LangGraphComponentsRegistryT] = None,
        import_only_referenced_components: bool = False,
    ) -> Union[CompiledStateGraph[Any, Any, Any], Dict[str, LangGraphRuntimeComponent]]:
        """
        Transform the given Agent Spec YAML into LangGraph components, with support for
        disaggregated configurations.

        Parameters
        ----------
        serialized_assistant:
            Serialized Agent Spec configuration.
        components_registry:
            Optional registry mapping ids to LangGraph components/values. The loader will
            convert these back to Agent Spec components/values internally to resolve
            references during deserialization.
        import_only_referenced_components:
            When ``True``, loads only the referenced/disaggregated components and returns a
            dictionary mapping component id to LangGraph components/values. These can be
            used as the ``components_registry`` when loading the main configuration. When
            ``False``, loads the main component and returns the compiled LangGraph graph.

        Returns
        -------
        If ``import_only_referenced_components`` is ``False``

        CompiledStateGraph
            The compiled LangGraph component.

        If ``import_only_referenced_components`` is ``True``

        Dict[str, LangGraphRuntimeComponent]
            A dictionary containing the converted referenced components.

        Examples
        --------
        Basic two-phase loading with disaggregation:

        >>> from pyagentspec.agent import Agent
        >>> from pyagentspec.llms import OllamaConfig
        >>> from pyagentspec.serialization import AgentSpecSerializer
        >>> agent = Agent(id="agent_id", name="A", system_prompt="You are helpful.", llm_config=OllamaConfig(name="m", model_id="llama3.1", url="http://localhost:11434"))
        >>> main_yaml, disag_yaml = AgentSpecSerializer().to_yaml(
        ...     agent, disaggregated_components=[(agent.llm_config, "llm_id")], export_disaggregated_components=True
        ... )
        >>> from pyagentspec.adapters.langgraph import AgentSpecLoader
        >>> loader = AgentSpecLoader()
        >>> registry = loader.load_yaml(disag_yaml, import_only_referenced_components=True)
        >>> compiled = loader.load_yaml(main_yaml, components_registry=registry)

        """
        deserializer = AgentSpecDeserializer(plugins=self.plugins)
        converted_registry: Optional[AgentSpecComponentsRegistryT] = (
            self._convert_component_registry(components_registry) if components_registry else None
        )
        if import_only_referenced_components:
            # Load and return the disaggregated Agent Spec components
            agentspec_referenced_components = deserializer.from_yaml(
                serialized_assistant,
                components_registry=converted_registry,
                import_only_referenced_components=True,
            )
            # Convert each referenced Agent Spec component to its LangGraph counterpart
            converted: Dict[str, LangGraphRuntimeComponent] = {}
            for component_id, agentspec_component_ in agentspec_referenced_components.items():
                converted_value = cast(
                    LangGraphRuntimeComponent, self.load_component(agentspec_component_)
                )
                converted[component_id] = converted_value
            return converted

        # Else, load the main component
        agentspec_assistant: AgentSpecComponent = deserializer.from_yaml(
            serialized_assistant,
            components_registry=converted_registry,
            import_only_referenced_components=False,
        )
        loaded = self.load_component(agentspec_assistant)
        return cast(CompiledStateGraph[Any, Any, Any], loaded)

    @overload
    def load_json(self, serialized_assistant: str) -> CompiledStateGraph[Any, Any, Any]: ...

    @overload
    def load_json(
        self,
        serialized_assistant: str,
        components_registry: Optional[LangGraphComponentsRegistryT],
    ) -> CompiledStateGraph[Any, Any, Any]: ...

    @overload
    def load_json(
        self,
        serialized_assistant: str,
        *,
        import_only_referenced_components: bool,
    ) -> Union[CompiledStateGraph[Any, Any, Any], Dict[str, LangGraphRuntimeComponent]]: ...

    @overload
    def load_json(
        self,
        serialized_assistant: str,
        components_registry: Optional[LangGraphComponentsRegistryT],
        import_only_referenced_components: bool,
    ) -> Union[CompiledStateGraph[Any, Any, Any], Dict[str, LangGraphRuntimeComponent]]: ...

    def load_json(
        self,
        serialized_assistant: str,
        components_registry: Optional[LangGraphComponentsRegistryT] = None,
        import_only_referenced_components: bool = False,
    ) -> Union[CompiledStateGraph[Any, Any, Any], Dict[str, LangGraphRuntimeComponent]]:
        """
        Transform the given Agent Spec JSON into LangGraph components, with support for
        disaggregated configurations.

        Parameters
        ----------
        serialized_assistant:
            Serialized Agent Spec configuration.
        components_registry:
            Optional registry mapping ids to LangGraph components/values. The loader will
            convert these back to Agent Spec components/values internally to resolve
            references during deserialization.
        import_only_referenced_components:
            When ``True``, loads only the referenced/disaggregated components and returns a
            dictionary mapping component id to LangGraph components/values. These can be
            used as the ``components_registry`` when loading the main configuration. When
            ``False``, loads the main component and returns the compiled LangGraph graph.

        Returns
        -------
        If ``import_only_referenced_components`` is ``False``

        CompiledStateGraph
            The compiled LangGraph component.

        If ``import_only_referenced_components`` is ``True``

        Dict[str, LangGraphRuntimeComponent]
            A dictionary containing the converted referenced components.

        Examples
        --------
        Basic two-phase loading with disaggregation:

        >>> from pyagentspec.agent import Agent
        >>> from pyagentspec.llms import OllamaConfig
        >>> from pyagentspec.serialization import AgentSpecSerializer
        >>> agent = Agent(id="agent_id", name="A", system_prompt="You are helpful.", llm_config=OllamaConfig(name="m", model_id="llama3.1", url="http://localhost:11434"))
        >>> main_json, disag_json = AgentSpecSerializer().to_json(
        ...     agent, disaggregated_components=[(agent.llm_config, "llm_id")], export_disaggregated_components=True
        ... )
        >>> from pyagentspec.adapters.langgraph import AgentSpecLoader
        >>> loader = AgentSpecLoader()
        >>> registry = loader.load_json(disag_json, import_only_referenced_components=True)
        >>> compiled = loader.load_json(main_json, components_registry=registry)

        """
        deserializer = AgentSpecDeserializer(plugins=self.plugins)
        converted_registry: Optional[AgentSpecComponentsRegistryT] = (
            self._convert_component_registry(components_registry) if components_registry else None
        )
        if import_only_referenced_components:
            # Load and return the disaggregated Agent Spec components
            agentspec_referenced_components = deserializer.from_json(
                serialized_assistant,
                components_registry=converted_registry,
                import_only_referenced_components=True,
            )
            converted: Dict[str, LangGraphRuntimeComponent] = {}
            for component_id, agentspec_component_ in agentspec_referenced_components.items():
                converted_value = cast(
                    LangGraphRuntimeComponent, self.load_component(agentspec_component_)
                )
                converted[component_id] = converted_value
            return converted

        # Else, load the main component
        agentspec_assistant: AgentSpecComponent = deserializer.from_json(
            serialized_assistant,
            components_registry=converted_registry,
            import_only_referenced_components=False,
        )
        loaded = self.load_component(agentspec_assistant)
        return cast(CompiledStateGraph[Any, Any, Any], loaded)

    def load_component(self, agentspec_component: AgentSpecComponent) -> Any:
        """
        Transform the given PyAgentSpec Component into the respective LangGraph component

        Parameters
        ----------

        agentspec_component:
            PyAgentSpec Component to be converted to a LangGraph runtime component
            (e.g., compiled graph, model, tool).
        """
        return AgentSpecToLangGraphConverter().convert(
            agentspec_component=agentspec_component,
            tool_registry=self.tool_registry,
            checkpointer=self.checkpointer,
            config=self.config,
        )

    def _convert_component_registry(
        self, registry: LangGraphComponentsRegistryT
    ) -> AgentSpecComponentsRegistryT:
        """
        Convert a registry of LangGraph components/values back to Agent Spec components/values
        so it can be used by the AgentSpec deserializer to resolve references.
        """
        from pyagentspec.adapters.langgraph._agentspecconverter import (
            LangGraphToAgentSpecConverter,
        )

        converter = LangGraphToAgentSpecConverter()

        converted: Dict[str, Any] = {}
        for custom_id, value in registry.items():
            converted_value = converter.convert_runtime_value(value)
            if converted_value is not None:
                converted[custom_id] = converted_value
            elif isinstance(value, AgentSpecComponent):
                converted[custom_id] = value
            else:
                raise NotImplementedError(
                    f"Unsupported registry value for back-conversion: {value}"
                )

        return converted
