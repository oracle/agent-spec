# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


from typing import Any, Dict, List, Optional, Union, cast

from pyagentspec.adapters._agentspecloader import AdapterAgnosticAgentSpecLoader
from pyagentspec.adapters.langgraph._agentspecconverter import LangGraphToAgentSpecConverter
from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter
from pyagentspec.adapters.langgraph._types import (
    Checkpointer,
    LangGraphComponentsRegistryT,
    LangGraphRuntimeComponent,
    RunnableConfig,
)
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.serialization import ComponentDeserializationPlugin


class AgentSpecLoader(AdapterAgnosticAgentSpecLoader):
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
        super().__init__(plugins=plugins, tool_registry=tool_registry)
        self.checkpointer = checkpointer
        self.config = config

    @property
    def agentspec_to_runtime_converter(self) -> AgentSpecToLangGraphConverter:
        return AgentSpecToLangGraphConverter()

    @property
    def runtime_to_agentspec_converter(self) -> LangGraphToAgentSpecConverter:
        return LangGraphToAgentSpecConverter()

    def load_yaml(
        self,
        serialized_assistant: str,
        components_registry: Optional[LangGraphComponentsRegistryT] = None,
        import_only_referenced_components: bool = False,
    ) -> Union[LangGraphRuntimeComponent, Dict[str, LangGraphRuntimeComponent]]:
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

        Alternatively, you can deserialize the disaggregated components with the pyagentspec deserializer and pass them into the load of the main component:

        >>> from pyagentspec.serialization import AgentSpecDeserializer
        >>> deserializer = AgentSpecDeserializer()
        >>> referenced_components = deserializer.from_yaml(disag_yaml, import_only_referenced_components=True)
        >>> agentspec_agent = deserializer.from_yaml(main_yaml, components_registry=referenced_components)
        >>> compiled = loader.load_component(agentspec_agent)

        """
        return super().load_yaml(
            serialized_assistant,
            components_registry=components_registry,
            import_only_referenced_components=import_only_referenced_components,
        )

    def load_json(
        self,
        serialized_assistant: str,
        components_registry: Optional[LangGraphComponentsRegistryT] = None,
        import_only_referenced_components: bool = False,
    ) -> Union[LangGraphRuntimeComponent, Dict[str, LangGraphRuntimeComponent]]:
        """
        Transform the given Agent Spec JSON into LangGraph components, with support for disaggregated configurations.

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
        >>> agent = Agent(id="agent_id", name="A", system_prompt="You are helpful.", llm_config=OllamaConfig(id="llm_id", name="m", model_id="llama3.1", url="http://localhost:11434"))
        >>> main_json, disag_json = AgentSpecSerializer().to_json(
        ...     agent, disaggregated_components=[(agent.llm_config, "llm_id")], export_disaggregated_components=True
        ... )
        >>> from pyagentspec.adapters.langgraph import AgentSpecLoader
        >>> loader = AgentSpecLoader()
        >>> registry = loader.load_json(disag_json, import_only_referenced_components=True)
        >>> langgraph = loader.load_json(main_json, components_registry=registry)

        Alternatively, you can deserialize the disaggregated components with the pyagentspec deserializer and pass them into the load of the main component:

        >>> from pyagentspec.serialization import AgentSpecDeserializer
        >>> deserializer = AgentSpecDeserializer()
        >>> referenced_components = deserializer.from_json(disag_json, import_only_referenced_components=True)
        >>> agentspec_agent = deserializer.from_json(main_json, components_registry=referenced_components)
        >>> compiled = loader.load_component(agentspec_agent)

        """
        return super().load_json(
            serialized_assistant,
            components_registry=components_registry,
            import_only_referenced_components=import_only_referenced_components,
        )

    def load_dict(
        self,
        serialized_assistant: Dict[str, Any],
        components_registry: Optional[LangGraphComponentsRegistryT] = None,
        import_only_referenced_components: bool = False,
    ) -> Union[LangGraphRuntimeComponent, Dict[str, LangGraphRuntimeComponent]]:
        """
        Transform the given Agent Spec JSON into LangGraph components, with support for disaggregated configurations.

        Parameters
        ----------
        serialized_assistant:
            Serialized Agent Spec configuration as a dictionary.
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
        >>> agent = Agent(id="agent_id", name="A", system_prompt="You are helpful.", llm_config=OllamaConfig(id="llm_id", name="m", model_id="llama3.1", url="http://localhost:11434"))
        >>> main_dict, disag_dict = AgentSpecSerializer().to_dict(
        ...     agent, disaggregated_components=[(agent.llm_config, "llm_id")], export_disaggregated_components=True
        ... )
        >>> from pyagentspec.adapters.langgraph import AgentSpecLoader
        >>> loader = AgentSpecLoader()
        >>> registry = loader.load_dict(disag_dict, import_only_referenced_components=True)
        >>> langgraph = loader.load_dict(main_dict, components_registry=registry)

        Alternatively, you can deserialize the disaggregated components with the pyagentspec deserializer and pass them into the load of the main component:

        >>> from pyagentspec.serialization import AgentSpecDeserializer
        >>> deserializer = AgentSpecDeserializer()
        >>> referenced_components = deserializer.from_dict(disag_dict, import_only_referenced_components=True)
        >>> agentspec_agent = deserializer.from_dict(main_dict, components_registry=referenced_components)
        >>> compiled = loader.load_component(agentspec_agent)

        """
        return super().load_dict(
            serialized_assistant,
            components_registry=components_registry,
            import_only_referenced_components=import_only_referenced_components,
        )

    def load_component(self, agentspec_component: AgentSpecComponent) -> LangGraphRuntimeComponent:
        # Need to override to make it use config and checkpointer
        return cast(
            LangGraphRuntimeComponent,
            self.agentspec_to_runtime_converter.convert(
                agentspec_component,
                tool_registry=self.tool_registry,
                checkpointer=self.checkpointer,
                config=self.config,
            ),
        )
