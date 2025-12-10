# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.adapters.autogen._agentspecconverter import AutogenToAgentSpecConverter
from pyagentspec.adapters.autogen._types import AutogenComponent
from pyagentspec.component import Component
from pyagentspec.serialization import AgentSpecSerializer as PyAgentSpecSerializer


class AgentSpecExporter:
    """Helper class to convert AutoGen objects to Agent Spec configurations."""

    def to_yaml(self, autogen_component: AutogenComponent) -> str:  # type: ignore
        """
        Transform the given AutoGen component into the respective Agent Spec YAML representation.

        Parameters
        ----------
        autogen_component:
            AutoGen Component to serialize to an Agent Spec configuration.

        Returns
        -------
        str
            The Agent Spec YAML representation of the AutoGen component.
        """
        agentlang_assistant = self.to_component(autogen_component)
        return PyAgentSpecSerializer().to_yaml(agentlang_assistant)

    def to_json(self, autogen_component: AutogenComponent) -> str:  # type: ignore
        """
        Transform the given AutoGen component into the respective Agent Spec JSON representation.

        Parameters
        ----------
        autogen_component:
            AutoGen Component to serialize to an Agent Spec configuration.

        Returns
        -------
        str
            The Agent Spec JSON representation of the AutoGen component.
        """
        agentlang_assistant = self.to_component(autogen_component)
        return PyAgentSpecSerializer().to_json(agentlang_assistant)

    def to_component(self, autogen_component: AutogenComponent) -> Component:  # type: ignore
        """
        Transform the given AutoGen component into the respective PyAgentSpec Component.

        Parameters
        ----------
        autogen_component:
            AutoGen Component to transform into a corresponding PyAgentSpec Component.

        Returns
        -------
        Component
            The PyAgentSpec Component corresponding to the AutoGen component.

        Raises
        ------
        TypeError
            If the input is not an AutoGen Component.
        """
        if not isinstance(autogen_component, AutogenComponent):
            raise TypeError(
                f"Expected an AutoGen Agent or Flow, but got '{type(autogen_component)}' instead"
            )
        return AutogenToAgentSpecConverter().convert(autogen_component)
