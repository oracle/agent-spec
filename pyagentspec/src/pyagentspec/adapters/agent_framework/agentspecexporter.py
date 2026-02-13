# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.adapters._agentspecexporter import AdapterAgnosticAgentSpecExporter
from pyagentspec.adapters._agentspecloader import RuntimeToAgentSpecConverter
from pyagentspec.adapters.agent_framework._agentspecconverter import (
    AgentFrameworkToAgentSpecConverter,
)


class AgentSpecExporter(AdapterAgnosticAgentSpecExporter):
    """Helper class to convert Microsoft Agent Framework objects to Agent Spec configurations."""

    @property
    def runtime_to_agentspec_converter(self) -> RuntimeToAgentSpecConverter:
        return AgentFrameworkToAgentSpecConverter()
