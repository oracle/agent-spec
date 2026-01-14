# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from __future__ import annotations

from typing import Dict, List, Optional, cast

from pyagentspec.adapters.openaiagents._openaiagentsconverter import (
    AgentSpecToOpenAIConverter,
    _TargetTool,
)
from pyagentspec.adapters.openaiagents._types import OAAgent
from pyagentspec.adapters.openaiagents.flows._rulepack_registry import resolve_rulepack
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.flows.flow import Flow as AgentSpecFlow
from pyagentspec.serialization import AgentSpecDeserializer, ComponentDeserializationPlugin


class AgentSpecLoader:
    """Helper class to convert Agent Spec configurations to OpenAI Agents SDK objects."""

    def __init__(
        self,
        tool_registry: Optional[Dict[str, _TargetTool]] = None,
        plugins: Optional[List[ComponentDeserializationPlugin]] = None,
    ):
        """
        Parameters
        ----------
        tool_registry:
            Optional dictionary to enable converting/loading assistant configurations involving the
            use of tools. Keys must be the tool names as specified in the serialized configuration, and
            the values are the tool objects (prebuilt OpenAI FunctionTool or callable).
        plugins:
            Optional list of deserialization plugins for PyAgentSpec.
        """
        self.tool_registry = tool_registry or {}
        self.plugins = plugins

    def load_yaml(
        self,
        serialized_assistant: str,
        output_path: str | None = None,
        module_name: str | None = None,
        rulepack_version: str | None = None,
    ) -> "OAAgent | str":
        """
        Transform the given Agent Spec YAML representation into an OpenAI Agents component.

        Parameters
        ----------
        serialized_assistant: Agent Spec describing the agent or flow to load.
        output_path: Optional file path to write the generated source.
        module_name: Optional module name to stamp in generated code.
        rulepack_version: Optional explicit RulePack version; defaults to SDK version.

        Notes
        -----
        - If the YAML represents an Agent Spec component (e.g., Agent), returns an OpenAI Agent.
        - If the YAML represents an Agent Spec Flow, returns the generated Python source as a string.
        """
        agentspec_obj = AgentSpecDeserializer(plugins=self.plugins).from_yaml(serialized_assistant)
        return self.load_component(
            agentspec_obj,
            output_path=output_path,
            module_name=module_name,
            rulepack_version=rulepack_version,
        )

    def load_json(
        self,
        serialized_assistant: str,
        output_path: str | None = None,
        module_name: str | None = None,
        rulepack_version: str | None = None,
    ) -> "OAAgent | str":
        """
        Transform the given Agent Spec JSON representation into an OpenAI Agents component.

        Parameters
        ----------
        serialized_assistant: Agent Spec describing the agent or flow to load.
        output_path: Optional file path to write the generated source.
        module_name: Optional module name to stamp in generated code.
        rulepack_version: Optional explicit RulePack version; defaults to SDK version.

        Notes
        -----
        - If the JSON represents an Agent Spec component (e.g., Agent), returns an OpenAI Agent.
        - If the JSON represents an Agent Spec Flow, returns the generated Python source as a string.
        """
        agentspec_obj = AgentSpecDeserializer(plugins=self.plugins).from_json(serialized_assistant)
        return self.load_component(
            agentspec_obj,
            output_path=output_path,
            module_name=module_name,
            rulepack_version=rulepack_version,
        )

    def load_component(
        self,
        agentspec_component: AgentSpecComponent,
        output_path: str | None = None,
        module_name: str | None = None,
        rulepack_version: str | None = None,
    ) -> "OAAgent | str":
        """
        Transform the given PyAgentSpec object into an OpenAI Agents component or Python flow source.

        Behavior
        --------
        - If `agentspec_component` is a standard Agent Spec component (e.g., Agent), returns an
          OpenAI Agents SDK component (Agent).
        - If `agentspec_component` is an Agent Spec Flow, generates and returns the Python source
          for the OpenAI Agents workflow. When `output_path` is provided, writes the source to the
          given path as well.

        Parameters
        ----------
        agentspec_component: The PyAgentSpec object to convert to OpenAI Agents.
        output_path: Optional file path to write the generated source.
        module_name: Optional module name to stamp in generated code.
        rulepack_version: Optional explicit RulePack version; defaults to SDK version.
        """
        is_flow = isinstance(agentspec_component, cast(type, AgentSpecFlow))
        if is_flow:
            pack = resolve_rulepack(rulepack_version)
            ir = pack.agentspec_to_ir(agentspec_component, strict=True)
            mod = pack.codegen(ir, module_name=module_name)
            code = mod.code
            if output_path:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(code)
            return code  # type: ignore

        # Non-flow component → convert to OpenAI Agents component
        openai_component = AgentSpecToOpenAIConverter().convert(
            agentspec_component, tool_registry=self.tool_registry
        )
        return openai_component  # type: ignore
