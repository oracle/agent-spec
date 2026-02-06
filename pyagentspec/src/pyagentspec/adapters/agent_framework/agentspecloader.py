# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.adapters.agent_framework._agentframeworkconverter import (
    AgentSpecToAgentFrameworkConverter,
)
from pyagentspec.adapters.agent_framework._types import (
    AgentFrameworkComponent,
    AgentFrameworkTool,
)
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.serialization import AgentSpecDeserializer, ComponentDeserializationPlugin


class AgentSpecLoader:
    """Helper class to convert Agent Spec configurations to Microsoft Agent Framework objects."""

    def __init__(
        self,
        tool_registry: dict[str, AgentFrameworkTool] | None = None,
        plugins: list[ComponentDeserializationPlugin] | None = None,
    ):
        """
        Parameters
        ----------

        tool_registry:
            Optional dictionary to enable converting/loading assistant configurations involving the
            use of tools. Keys must be the tool names as specified in the serialized configuration, and
            the values are the tool objects.
        plugins:
            Optional list of plugins to enable converting/loading assistant configurations involving
            non-standard Agent Spec components.
        """
        self.tool_registry = tool_registry or {}
        self.plugins = plugins

    def load_yaml(self, serialized_assistant: str) -> AgentFrameworkComponent:
        """
        Transform the given Agent Spec YAML representation into the respective Microsoft Agent Framework Component

        Parameters
        ----------

        serialized_assistant:
            Serialized Agent Spec configuration to be converted to a Microsoft Agent Framework Component.
        """
        agentspec_assistant = AgentSpecDeserializer(plugins=self.plugins).from_yaml(
            serialized_assistant
        )
        return self.load_component(agentspec_assistant)

    def load_json(self, serialized_assistant: str) -> AgentFrameworkComponent:
        """
        Transform the given Agent Spec JSON representation into the respective Microsoft Agent Framework Component

        Parameters
        ----------

        serialized_assistant:
            Serialized Agent Spec configuration to be converted to a Microsoft Agent Framework Component.
        """
        agentspec_assistant = AgentSpecDeserializer(plugins=self.plugins).from_json(
            serialized_assistant
        )
        return self.load_component(agentspec_assistant)

    def load_component(self, agentspec_component: AgentSpecComponent) -> AgentFrameworkComponent:
        """
        Transform the given PyAgentSpec Component into the respective Microsoft Agent Framework Component

        Parameters
        ----------

        agentspec_component:
            PyAgentSpec Component to be converted to a Microsoft Agent Framework Component.
        """
        agent_framework_component = AgentSpecToAgentFrameworkConverter().convert(
            agentspec_component, self.tool_registry
        )
        return agent_framework_component
