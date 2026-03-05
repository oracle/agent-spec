# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any

from pyagentspec.adapters._agentspecloader import AdapterAgnosticAgentSpecLoader
from pyagentspec.adapters.agent_framework._agentframeworkconverter import (
    AgentSpecToAgentFrameworkConverter,
)
from pyagentspec.adapters.agent_framework._agentspecconverter import (
    AgentFrameworkToAgentSpecConverter,
)


class AgentSpecLoader(AdapterAgnosticAgentSpecLoader):
    """Helper class to convert Agent Spec configurations to Microsoft Agent Framework objects."""

    @property
    def agentspec_to_runtime_converter(self) -> AgentSpecToAgentFrameworkConverter:
        return AgentSpecToAgentFrameworkConverter()

    @property
    def runtime_to_agentspec_converter(self) -> AgentFrameworkToAgentSpecConverter:
        return AgentFrameworkToAgentSpecConverter()

    def load_yaml(
        self,
        serialized_assistant: str,
        components_registry: dict[str, Any] | None = None,
        import_only_referenced_components: bool = False,
    ) -> object | dict[str, Any]:
        """
        Transform the given Agent Spec YAML into Microsoft Agent Framework components, with
        support for disaggregated configurations.

        Parameters
        ----------
        serialized_assistant:
            Serialized Agent Spec configuration.
        components_registry:
            Optional registry mapping ids to Microsoft Agent Framework components/values.
            The loader will convert these back to Agent Spec components/values internally
            to resolve references during deserialization.
        import_only_referenced_components:
            When ``True``, loads only the referenced/disaggregated components and returns a
            dictionary mapping component id to Microsoft Agent Framework components/values.
            These can be used as the ``components_registry`` when loading the main
            configuration. When ``False``, loads the main component and returns the
            compiled Microsoft Agent Framework object.

        Returns
        -------
        If ``import_only_referenced_components`` is ``False``

        object
            The converted Microsoft Agent Framework component.

        If ``import_only_referenced_components`` is ``True``

        dict[str, Any]
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
        >>> from pyagentspec.adapters.agent_framework import AgentSpecLoader
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
        components_registry: dict[str, Any] | None = None,
        import_only_referenced_components: bool = False,
    ) -> object | dict[str, Any]:
        """
        Transform the given Agent Spec JSON into Microsoft Agent Framework components, with
        support for disaggregated configurations.

        Parameters
        ----------
        serialized_assistant:
            Serialized Agent Spec configuration.
        components_registry:
            Optional registry mapping ids to Microsoft Agent Framework components/values.
            The loader will convert these back to Agent Spec components/values internally
            to resolve references during deserialization.
        import_only_referenced_components:
            When ``True``, loads only the referenced/disaggregated components and returns a
            dictionary mapping component id to Microsoft Agent Framework components/values.
            These can be used as the ``components_registry`` when loading the main
            configuration. When ``False``, loads the main component and returns the
            compiled Microsoft Agent Framework object.

        Returns
        -------
        If ``import_only_referenced_components`` is ``False``

        object
            The converted Microsoft Agent Framework component.

        If ``import_only_referenced_components`` is ``True``

        dict[str, Any]
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
        >>> from pyagentspec.adapters.agent_framework import AgentSpecLoader
        >>> loader = AgentSpecLoader()
        >>> registry = loader.load_json(disag_json, import_only_referenced_components=True)
        >>> compiled = loader.load_json(main_json, components_registry=registry)

        """
        return super().load_json(
            serialized_assistant,
            components_registry=components_registry,
            import_only_referenced_components=import_only_referenced_components,
        )

    def load_dict(
        self,
        serialized_assistant: dict[str, Any],
        components_registry: dict[str, Any] | None = None,
        import_only_referenced_components: bool = False,
    ) -> object | dict[str, Any]:
        """
        Transform the given Agent Spec dictionary into Microsoft Agent Framework components,
        with support for disaggregated configurations.

        Parameters
        ----------
        serialized_assistant:
            Serialized Agent Spec configuration as a dictionary.
        components_registry:
            Optional registry mapping ids to Microsoft Agent Framework components/values.
            The loader will convert these back to Agent Spec components/values internally
            to resolve references during deserialization.
        import_only_referenced_components:
            When ``True``, loads only the referenced/disaggregated components and returns a
            dictionary mapping component id to Microsoft Agent Framework components/values.
            These can be used as the ``components_registry`` when loading the main
            configuration. When ``False``, loads the main component and returns the
            compiled Microsoft Agent Framework object.

        Returns
        -------
        If ``import_only_referenced_components`` is ``False``

        object
            The converted Microsoft Agent Framework component.

        If ``import_only_referenced_components`` is ``True``

        dict[str, Any]
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
        >>> from pyagentspec.adapters.agent_framework import AgentSpecLoader
        >>> loader = AgentSpecLoader()
        >>> registry = loader.load_dict(disag_dict, import_only_referenced_components=True)
        >>> compiled = loader.load_dict(main_dict, components_registry=registry)

        """
        return super().load_dict(
            serialized_assistant,
            components_registry=components_registry,
            import_only_referenced_components=import_only_referenced_components,
        )
