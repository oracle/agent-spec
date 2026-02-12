# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


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
