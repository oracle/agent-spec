# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Provide the CrewAI adapter Agent Spec loader."""

from typing import Any, Dict, List, Optional

from pyagentspec.adapters._agentspecloader import (
    AdapterAgnosticAgentSpecLoader,
    AgentSpecToRuntimeConverter,
    RuntimeToAgentSpecConverter,
)
from pyagentspec.adapters.crewai._agentspecconverter import CrewAIToAgentSpecConverter
from pyagentspec.adapters.crewai._crewaiconverter import AgentSpecToCrewAIConverter
from pyagentspec.serialization.componentpolicy import ComponentPolicyInput


class AgentSpecLoader(AdapterAgnosticAgentSpecLoader):
    """Helper class to convert Agent Spec configurations to CrewAI objects.

    ``allowed_components`` and ``blocked_components`` can be used to constrain
    which Agent Spec component types load. Resolvable type names and Component
    classes match subclasses; unresolved type names match only the exact serialized
    component type. When allow and block entries both match, the closest match
    in the component class hierarchy wins; block entries win same-distance ties.
    If ``blocked_components`` is omitted, ``StdioTransport`` and its subclasses
    are blocked by default.
    """

    def __init__(
        self,
        tool_registry: Optional[Dict[str, Any]] = None,
        plugins: Optional[List[Any]] = None,
        *,
        allowed_components: Optional[ComponentPolicyInput] = None,
        blocked_components: Optional[ComponentPolicyInput] = None,
        enable_agentspec_tracing: bool = True,
    ) -> None:
        super().__init__(
            tool_registry=tool_registry,
            plugins=plugins,
            allowed_components=allowed_components,
            blocked_components=blocked_components,
        )
        self._enable_agentspec_tracing = enable_agentspec_tracing

    @property
    def agentspec_to_runtime_converter(self) -> AgentSpecToRuntimeConverter:
        return AgentSpecToCrewAIConverter(enable_agentspec_tracing=self._enable_agentspec_tracing)

    @property
    def runtime_to_agentspec_converter(self) -> RuntimeToAgentSpecConverter:
        return CrewAIToAgentSpecConverter()

    def load_yaml(
        self,
        serialized_assistant: str,
        components_registry: Optional[Dict[str, Any]] = None,
        import_only_referenced_components: bool = False,
    ) -> Any:
        """
        Transform the given Agent Spec YAML into CrewAI components, with support for
        disaggregated configurations.

        Parameters
        ----------
        serialized_assistant:
            Serialized Agent Spec configuration.
        components_registry:
            Optional registry mapping ids to CrewAI components/values. The loader will
            convert these back to Agent Spec components/values internally to resolve
            references during deserialization.
        import_only_referenced_components:
            When ``True``, loads only the referenced/disaggregated components and returns a
            dictionary mapping component id to CrewAI components/values. These can be
            used as the ``components_registry`` when loading the main configuration. When
            ``False``, loads the main component and returns the compiled CrewAI graph.

        Returns
        -------
        If ``import_only_referenced_components`` is ``False``

        Any
            The converted CrewAI component.

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
        >>> from pyagentspec.adapters.crewai import AgentSpecLoader
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
    ) -> Any:
        """
        Transform the given Agent Spec JSON into CrewAI components, with support for
        disaggregated configurations.

        Parameters
        ----------
        serialized_assistant:
            Serialized Agent Spec configuration.
        components_registry:
            Optional registry mapping ids to CrewAI components/values. The loader will
            convert these back to Agent Spec components/values internally to resolve
            references during deserialization.
        import_only_referenced_components:
            When ``True``, loads only the referenced/disaggregated components and returns a
            dictionary mapping component id to CrewAI components/values. These can be
            used as the ``components_registry`` when loading the main configuration. When
            ``False``, loads the main component and returns the compiled CrewAI graph.

        Returns
        -------
        If ``import_only_referenced_components`` is ``False``

        Any
            The converted CrewAI component.

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
        >>> from pyagentspec.adapters.crewai import AgentSpecLoader
        >>> loader = AgentSpecLoader()
        >>> registry = loader.load_json(disag_json, import_only_referenced_components=True)
        >>> crewai = loader.load_json(main_json, components_registry=registry)

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
    ) -> Any:
        """
        Transform the given Agent Spec dictionary into CrewAI components, with support
        for disaggregated configurations.

        Parameters
        ----------
        serialized_assistant:
            Serialized Agent Spec configuration as a dictionary.
        components_registry:
            Optional registry mapping ids to CrewAI components/values. The loader will
            convert these back to Agent Spec components/values internally to resolve
            references during deserialization.
        import_only_referenced_components:
            When ``True``, loads only the referenced/disaggregated components and returns a
            dictionary mapping component id to CrewAI components/values. These can be
            used as the ``components_registry`` when loading the main configuration. When
            ``False``, loads the main component and returns the compiled CrewAI graph.

        Returns
        -------
        If ``import_only_referenced_components`` is ``False``

        Any
            The converted CrewAI component.

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
        >>> main_dict, disag_dict = AgentSpecSerializer().to_dict(
        ...     agent, disaggregated_components=[(agent.llm_config, "llm_id")], export_disaggregated_components=True
        ... )
        >>> from pyagentspec.adapters.crewai import AgentSpecLoader
        >>> loader = AgentSpecLoader()
        >>> registry = loader.load_dict(disag_dict, import_only_referenced_components=True)
        >>> crewai = loader.load_dict(main_dict, components_registry=registry)

        """
        return super().load_dict(
            serialized_assistant,
            components_registry=components_registry,
            import_only_referenced_components=import_only_referenced_components,
        )
