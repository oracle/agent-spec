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


class AgentSpecLoader(AdapterAgnosticAgentSpecLoader):
    """Helper class to convert Agent Spec configurations to CrewAI objects."""

    def __init__(
        self,
        tool_registry: Optional[Dict[str, Any]] = None,
        plugins: Optional[List[Any]] = None,
        *,
        enable_agentspec_tracing: bool = True,
    ) -> None:
        super().__init__(tool_registry=tool_registry, plugins=plugins)
        self._enable_agentspec_tracing = enable_agentspec_tracing

    @property
    def agentspec_to_runtime_converter(self) -> AgentSpecToRuntimeConverter:
        return AgentSpecToCrewAIConverter(enable_agentspec_tracing=self._enable_agentspec_tracing)

    @property
    def runtime_to_agentspec_converter(self) -> RuntimeToAgentSpecConverter:
        return CrewAIToAgentSpecConverter()
