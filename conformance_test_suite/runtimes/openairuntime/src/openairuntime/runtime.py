# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


"""OpenAI Agents-based Agent Spec Runtime for CTS.

Implements the agentspec_cts_sdk.AgentSpecLoader protocol and provides a
RunnableComponent that executes either:
  - an Agent (OpenAI Agents SDK Agent), or
  - a Flow compiled to Python via the OpenAI adapter codegen (async function).

ClientTools are not supported in this runtime and will raise.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Dict, List, Literal, Optional, Union, cast

from pyagentspec.adapters.openaiagents import OpenAIAgentSpecLoader as AdapterLoader  # type: ignore
from pyagentspec.adapters.openaiagents._openaiagentsconverter import (
    AgentSpecToOpenAIConverter,
)

# --- CTS protocol data classes ---


@dataclass
class ToolResult:
    content: Any
    tool_request_id: str


@dataclass
class AgentSpecFinishedExecutionStatus:
    outputs: Dict[str, Any]
    agent_messages: List[str]


@dataclass
class ToolRequest:
    name: str
    args: Dict[str, Any]
    tool_request_id: str


@dataclass
class AgentSpecToolRequestExecutionStatus:
    tool_requests: List[ToolRequest]


@dataclass
class AgentSpecToolExecutionConfirmationStatus:
    tool_requests: List[ToolRequest]


@dataclass
class AgentSpecUserMessageRequestExecutionStatus:
    agent_messages: List[str]


class _FlowWrapper:
    """Wrap a generated OpenAI Agents Python workflow module into a runnable callable."""

    def __init__(self, mod: ModuleType):
        self._mod = mod
        try:
            self._run = getattr(mod, "run_workflow")
            self._WorkflowInput = getattr(mod, "WorkflowInput")
        except AttributeError as e:
            raise ValueError(f"Generated module missing required symbols: {e}")

    async def run(
        self, inputs: Dict[str, Any], tools: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        wi = self._WorkflowInput(**inputs) if inputs is not None else self._WorkflowInput()
        # Generated run_workflow returns a dict end_result
        if tools is None:
            return cast(Dict[str, Any], await self._run(wi))
        return cast(Dict[str, Any], await self._run(wi, tools=tools))


class OpenAIAgentSpecRunnableComponent:
    """Runnable component for Agent or Flow compiled to OpenAI Agents runtime."""

    def __init__(self, obj: Any, *, tools: Optional[Dict[str, Any]] = None):
        self._obj = obj
        self._pending_messages: List[str] = []
        self._inputs: Dict[str, Any] = {}
        self._tools = tools or {}

    def start(self, inputs: Optional[Dict[str, Any]] = None) -> None:
        self._inputs = inputs or {}

    def run(
        self,
    ) -> Union[
        AgentSpecFinishedExecutionStatus,
        AgentSpecToolRequestExecutionStatus,
        AgentSpecUserMessageRequestExecutionStatus,
        AgentSpecToolExecutionConfirmationStatus,
    ]:
        # Flow path: run the compiled async function and return final outputs
        if isinstance(self._obj, _FlowWrapper):
            out = asyncio.run(self._obj.run(self._inputs, tools=self._tools or None))
            return AgentSpecFinishedExecutionStatus(outputs=out or {}, agent_messages=[])

        # Agent path: use Agents SDK Runner
        from agents.items import ItemHelpers, MessageOutputItem
        from agents.run import RunConfig, Runner

        # Build initial input list from pending messages and provided inputs
        input_items: List[Any] = []
        for m in self._pending_messages:
            input_items.append({"role": "user", "content": m})

        # Allow tests to set {"messages": [...]} directly
        if "messages" in self._inputs and isinstance(self._inputs["messages"], list):
            input_items.extend(self._inputs["messages"])
        elif "user_input" in self._inputs:
            input_items.append({"role": "user", "content": self._inputs["user_input"]})

        result = asyncio.run(
            Runner.run(
                self._obj,
                input=input_items or "",
                run_config=RunConfig(trace_metadata={"__trace_source__": "agentspec-cts"}),
            )
        )

        # Collect agent message text
        agent_messages: List[str] = []
        for item in result.new_items:
            if isinstance(item, MessageOutputItem):
                txt = ItemHelpers.text_message_output(item)
                if txt:
                    agent_messages.append(txt)

        # If model produced function tool calls, expose them as ClientTool requests is not supported here
        # The OpenAI Agents SDK executes FunctionTools immediately when present; thus if tools are used,
        # their outputs are already present in new_items and final_output, and there is no pause state.
        return AgentSpecUserMessageRequestExecutionStatus(agent_messages=agent_messages)

    def append_user_message(self, user_message: str) -> None:
        self._pending_messages.append(user_message)

    def append_tool_results(self, tool_result: Union[ToolResult, list[ToolResult]]) -> None:
        raise NotImplementedError("ClientTool interactions are not supported in OpenAI runtime")

    def confirm_or_reject_tool_confirmation(
        self, tool_request: ToolRequest, decision: Literal["accept", "reject"]
    ) -> None:
        raise NotImplementedError("Tool Confirmation is not supported in the OpenAI adapter")


class OpenAIAgentSpecLoader:
    """CTS-compatible loader that bridges Agent Spec to OpenAI Agents runtime."""

    @staticmethod
    def load(
        agentspec_config: str,
        tool_registry: Optional[Dict[str, Any]] = None,
        components_registry: Optional[Dict[str, Any]] = None,
    ) -> OpenAIAgentSpecRunnableComponent:
        agentspec_component = OpenAIAgentSpecLoader._parse_agentspec(
            agentspec_config, components_registry
        )

        OpenAIAgentSpecLoader._prepare_env_for_llm(agentspec_component)
        OpenAIAgentSpecLoader._validate_no_clienttools(agentspec_component)

        # If this is a top-level Agent, construct an OpenAI Agents SDK Agent directly so we
        # can support VllmConfig and tool registries precisely.
        try:
            from pyagentspec.agent import Agent as _ASAgent
            from pyagentspec.llms.openaicompatibleconfig import (
                OpenAiCompatibleConfig as _ASOpenAICompat,
            )
            from pyagentspec.llms.openaiconfig import OpenAiConfig as _ASOpenAI
            from pyagentspec.llms.vllmconfig import VllmConfig as _ASVllm
            from pyagentspec.tools import Tool as _ASTool
        except Exception:
            _ASAgent = _ASTool = _ASOpenAI = _ASOpenAICompat = _ASVllm = None  # type: ignore

        if _ASAgent and isinstance(agentspec_component, _ASAgent):  # type: ignore[truthy-function]
            # Build model
            model: Any
            if _ASOpenAI and isinstance(agentspec_component.llm_config, _ASOpenAI):  # type: ignore[truthy-function]
                model = agentspec_component.llm_config.model_id
            elif _ASOpenAICompat and isinstance(agentspec_component.llm_config, _ASOpenAICompat):  # type: ignore[truthy-function]
                from agents.models.openai_provider import OpenAIProvider
                from openai import AsyncOpenAI

                client = AsyncOpenAI(api_key="", base_url=str(agentspec_component.llm_config.url))
                provider = OpenAIProvider(openai_client=client)
                model = provider.get_model(agentspec_component.llm_config.model_id)
            elif _ASVllm and isinstance(agentspec_component.llm_config, _ASVllm):  # type: ignore[truthy-function]
                from agents.models.openai_provider import OpenAIProvider
                from openai import AsyncOpenAI

                base_url = OpenAIAgentSpecLoader._canon_url(str(agentspec_component.llm_config.url))
                client = AsyncOpenAI(api_key="", base_url=base_url)
                provider = OpenAIProvider(openai_client=client)
                model = provider.get_model(agentspec_component.llm_config.model_id)
            else:
                raise NotImplementedError(
                    f"Unsupported LLM config for OpenAI runtime: {type(agentspec_component.llm_config)}"
                )

            # Convert tools via the adapter's converter to respect JSON schemas
            tools: List[Any] = []
            if agentspec_component.tools:
                conv = AgentSpecToOpenAIConverter()
                reg = tool_registry or {}
                for t in agentspec_component.tools:
                    tools.append(conv.convert(t, reg))

            from agents.agent import Agent as OAAgent

            oa_agent = OAAgent(
                name=agentspec_component.name,
                instructions=agentspec_component.system_prompt,
                model=model,
                tools=tools,
            )
            return OpenAIAgentSpecRunnableComponent(oa_agent)

        # Otherwise, use the adapter for flows and other supported conversions
        loader = AdapterLoader(tool_registry=tool_registry)
        obj = loader.load_component(agentspec_component)

        # Flow codegen returns str of Python code. Compile to module and wrap.
        if isinstance(obj, str):
            mod = OpenAIAgentSpecLoader._module_from_code(obj)
            return OpenAIAgentSpecRunnableComponent(_FlowWrapper(mod), tools=tool_registry)

        # Otherwise, obj is an OpenAI Agents SDK Agent
        return OpenAIAgentSpecRunnableComponent(obj)

    @staticmethod
    def _module_from_code(code: str) -> ModuleType:
        mod = ModuleType("agentspec_codegen_flow")
        exec(compile(code, "agentspec_codegen_flow.py", "exec"), mod.__dict__)  # nosec
        return mod

    @staticmethod
    def _parse_agentspec(
        agentspec_config: str, components_registry: Optional[Dict[str, Any]] = None
    ) -> Any:
        from pyagentspec.serialization import AgentSpecDeserializer

        return AgentSpecDeserializer().from_yaml(
            agentspec_config, components_registry=components_registry
        )

    @staticmethod
    def _prepare_env_for_llm(comp: Any) -> None:
        """If the AgentSpec uses an OpenAI-compatible endpoint, configure env for Agents SDK.

        Sets OPENAI_BASE_URL (with scheme and /v1) and ensures OPENAI_API_KEY exists.
        """
        import os
        from urllib.parse import urljoin

        try:
            from pyagentspec.llms.vllmconfig import VllmConfig
        except Exception:
            VllmConfig = None  # type: ignore

        def _canon(base: str) -> str:
            url = base
            if not url.lower().startswith(("http://", "https://")):
                url = (
                    "http://" if base.split(":")[0].replace(".", "").isdigit() else "https://"
                ) + base
            u = url.rstrip("/")
            if not u.endswith("/v1"):
                u = urljoin(u + "/", "v1")
            return u

        url: Optional[str] = None
        # Agent
        try:
            from pyagentspec.agent import Agent as _ASAgent
            from pyagentspec.flows.flow import Flow as _ASFlow
            from pyagentspec.flows.nodes.llmnode import LlmNode as _LlmNode
        except Exception:
            _ASAgent = _ASFlow = _LlmNode = None  # type: ignore

        if _ASAgent and isinstance(comp, _ASAgent):  # type: ignore[truthy-function]
            if VllmConfig and isinstance(comp.llm_config, VllmConfig):  # type: ignore[truthy-function]
                url = comp.llm_config.url
        elif _ASFlow and isinstance(comp, _ASFlow):  # type: ignore[truthy-function]
            # Find any LlmNode with VllmConfig
            for n in comp.nodes:
                if _LlmNode and isinstance(n, _LlmNode):  # type: ignore[truthy-function]
                    if VllmConfig and isinstance(n.llm_config, VllmConfig):  # type: ignore[truthy-function]
                        url = n.llm_config.url
                        break
        if url:
            os.environ.setdefault("OPENAI_BASE_URL", _canon(url))
            os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))

    @staticmethod
    def _canon_url(base: str) -> str:
        from urllib.parse import urljoin

        url = base
        if not url.lower().startswith(("http://", "https://")):
            url = (
                "http://" if base.split(":")[0].replace(".", "").isdigit() else "https://"
            ) + base
        u = url.rstrip("/")
        if not u.endswith("/v1"):
            u = urljoin(u + "/", "v1")
        return u

    @staticmethod
    def _validate_no_clienttools(comp: Any) -> None:
        """Raise if the AgentSpec contains ClientTool; OpenAI runtime cannot pause for client tools."""
        try:
            from pyagentspec.agent import Agent as _ASAgent
            from pyagentspec.flows.flow import Flow as _ASFlow
            from pyagentspec.flows.nodes.toolnode import ToolNode as _ToolNode
            from pyagentspec.tools.clienttool import ClientTool
        except Exception:
            return

        if isinstance(comp, _ASAgent):
            for t in comp.tools or []:
                if isinstance(t, ClientTool):
                    raise NotImplementedError("ClientTool is not supported by the OpenAI runtime")
        elif isinstance(comp, _ASFlow):
            for n in comp.nodes or []:
                if (
                    isinstance(n, _ToolNode)
                    and n.tool is not None
                    and isinstance(n.tool, ClientTool)
                ):
                    raise NotImplementedError(
                        "ClientTool in Flow is not supported by the OpenAI runtime"
                    )
