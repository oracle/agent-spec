# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.adapters.agent_framework._agentspecconverter import (
    AgentFrameworkToAgentSpecConverter,
)
from pyagentspec.adapters.agent_framework._types import AgentFrameworkComponent
from pyagentspec.component import Component
from pyagentspec.serialization import AgentSpecSerializer as PyAgentSpecSerializer
from pyagentspec.serialization import ComponentSerializationPlugin


class AgentSpecExporter:
    """Helper class to convert Microsoft Agent Framework objects to Agent Spec configurations."""

    def __init__(self, plugins: list[ComponentSerializationPlugin] | None = None) -> None:
        """
        Parameters
        ----------

        plugins:
            Optional list of plugins to enable converting/loading assistant configurations involving
            non-standard Agent Spec components.
        """
        self.plugins = plugins

    def to_yaml(self, agent_framework_component: AgentFrameworkComponent) -> str:
        """
        Transform the given Microsoft Agent Framework component into the respective Agent Spec YAML representation.

        Parameters
        ----------

        agent_framework_component:
            Microsoft Agent Framework Component to serialize to an Agent Spec configuration.
        """
        agentspec_component = self.to_component(agent_framework_component)
        return PyAgentSpecSerializer(plugins=self.plugins).to_yaml(agentspec_component)

    def to_json(self, agent_framework_component: AgentFrameworkComponent) -> str:
        """
        Transform the given Microsoft Agent Framework component into the respective Agent Spec JSON representation.

        Parameters
        ----------

        agent_framework_component:
            Microsoft Agent Framework Component to serialize to an Agent Spec configuration.
        """
        agentspec_component = self.to_component(agent_framework_component)
        return PyAgentSpecSerializer(plugins=self.plugins).to_json(agentspec_component)

    def to_component(self, agent_framework_component: AgentFrameworkComponent) -> Component:
        """
        Transform the given Microsoft Agent Framework component into the respective PyAgentSpec Component.

        Parameters
        ----------

        agent_framework_component:
            Microsoft Agent Framework Component to serialize to a corresponding PyAgentSpec Component.
        """
        return AgentFrameworkToAgentSpecConverter().convert(agent_framework_component)
