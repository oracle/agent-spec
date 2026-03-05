# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Dict, Optional, Union

from pyagentspec.adapters._agentspecloader import (
    AdapterAgnosticAgentSpecLoader,
    AgentSpecToRuntimeConverter,
    RuntimeToAgentSpecConverter,
)
from pyagentspec.adapters.autogen._agentspecconverter import AutogenToAgentSpecConverter
from pyagentspec.adapters.autogen._autogenconverter import AgentSpecToAutogenConverter


class AgentSpecLoader(AdapterAgnosticAgentSpecLoader):
    """Helper class to convert Agent Spec configurations to AutoGen objects."""

    @property
    def agentspec_to_runtime_converter(self) -> AgentSpecToRuntimeConverter:
        return AgentSpecToAutogenConverter()

    @property
    def runtime_to_agentspec_converter(self) -> RuntimeToAgentSpecConverter:
        return AutogenToAgentSpecConverter()

    def load_yaml(
        self,
        serialized_assistant: str,
        components_registry: Optional[Dict[str, Any]] = None,
        import_only_referenced_components: bool = False,
    ) -> Union[Any, Dict[str, Any]]:
        """
        Transform the given Agent Spec YAML into AutoGen components, with support for
        disaggregated configurations.

        Parameters
        ----------
        serialized_assistant:
            Serialized Agent Spec configuration.
        components_registry:
            Optional registry mapping ids to AutoGen components/values. The loader will
            convert these back to Agent Spec components/values internally to resolve
            references during deserialization.
        import_only_referenced_components:
            When ``True``, loads only the referenced/disaggregated components and returns a
            dictionary mapping component id to AutoGen components/values. These can be
            used as the ``components_registry`` when loading the main configuration. When
            ``False``, loads the main component and returns the compiled AutoGen graph.

        Returns
        -------
        If ``import_only_referenced_components`` is ``False``

        Any
            The converted AutoGen component.

        If ``import_only_referenced_components`` is ``True``

        Dict[str, Any]
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
        >>> from pyagentspec.adapters.autogen import AgentSpecLoader
        >>> loader = AgentSpecLoader()
        >>> registry = loader.load_yaml(disag_yaml, import_only_referenced_components=True)
        >>> compiled = loader.load_yaml(main_yaml, components_registry=registry)

        """
        return super().load_yaml(
            serialized_assistant,
            components_registry=components_registry,
            import_only_referenced_components=import_only_referenced_components,
        )

    def load_json(
        self,
        serialized_assistant: str,
        components_registry: Optional[Dict[str, Any]] = None,
        import_only_referenced_components: bool = False,
    ) -> Union[Any, Dict[str, Any]]:
        """
        Transform the given Agent Spec JSON into AutoGen components, with support for disaggregated configurations.

        Parameters
        ----------
        serialized_assistant:
            Serialized Agent Spec configuration.
        components_registry:
            Optional registry mapping ids to AutoGen components/values. The loader will
            convert these back to Agent Spec components/values internally to resolve
            references during deserialization.
        import_only_referenced_components:
            When ``True``, loads only the referenced/disaggregated components and returns a
            dictionary mapping component id to AutoGen components/values. These can be
            used as the ``components_registry`` when loading the main configuration. When
            ``False``, loads the main component and returns the compiled AutoGen graph.

        Returns
        -------
        If ``import_only_referenced_components`` is ``False``

        Any
            The converted AutoGen component.

        If ``import_only_referenced_components`` is ``True``

        Dict[str, Any]
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
        >>> from pyagentspec.adapters.autogen import AgentSpecLoader
        >>> loader = AgentSpecLoader()
        >>> registry = loader.load_json(disag_json, import_only_referenced_components=True)
        >>> autogen = loader.load_json(main_json, components_registry=registry)

        Alternatively, you can deserialize the disaggregated components with the pyagentspec deserializer and pass them into the load of the main component:

        >>> from pyagentspec.serialization import AgentSpecDeserializer
        >>> deserializer = AgentSpecDeserializer()
        >>> referenced_components = deserializer.from_json(disag_json, import_only_referenced_components=True)
        >>> agentspec_agent = deserializer.from_json(main_json, components_registry=referenced_components)
        >>> autogen_agent = loader.load_component(agentspec_agent)

        """
        return super().load_json(
            serialized_assistant,
            components_registry=components_registry,
            import_only_referenced_components=import_only_referenced_components,
        )

    def load_dict(
        self,
        serialized_assistant: Dict[str, Any],
        components_registry: Optional[Dict[str, Any]] = None,
        import_only_referenced_components: bool = False,
    ) -> Union[Any, Dict[str, Any]]:
        """
        Transform the given Agent Spec JSON into AutoGen components, with support for disaggregated configurations.

        Parameters
        ----------
        serialized_assistant:
            Serialized Agent Spec configuration.
        components_registry:
            Optional registry mapping ids to AutoGen components/values. The loader will
            convert these back to Agent Spec components/values internally to resolve
            references during deserialization.
        import_only_referenced_components:
            When ``True``, loads only the referenced/disaggregated components and returns a
            dictionary mapping component id to AutoGen components/values. These can be
            used as the ``components_registry`` when loading the main configuration. When
            ``False``, loads the main component and returns the compiled AutoGen graph.

        Returns
        -------
        If ``import_only_referenced_components`` is ``False``

        AutogenAssistantAgent
            The AutoGen component.

        If ``import_only_referenced_components`` is ``True``

        Dict[str, AutogenAssistantAgent]
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
        >>> from pyagentspec.adapters.autogen import AgentSpecLoader
        >>> loader = AgentSpecLoader()
        >>> registry = loader.load_dict(disag_dict, import_only_referenced_components=True)
        >>> autogen = loader.load_dict(main_dict, components_registry=registry)

        Alternatively, you can deserialize the disaggregated components with the pyagentspec deserializer and pass them into the load of the main component:

        >>> from pyagentspec.serialization import AgentSpecDeserializer
        >>> deserializer = AgentSpecDeserializer()
        >>> referenced_components = deserializer.from_dict(disag_dict, import_only_referenced_components=True)
        >>> agentspec_agent = deserializer.from_dict(main_dict, components_registry=referenced_components)
        >>> autogen_agent = loader.load_component(agentspec_agent)

        """
        return super().load_dict(
            serialized_assistant,
            components_registry=components_registry,
            import_only_referenced_components=import_only_referenced_components,
        )
