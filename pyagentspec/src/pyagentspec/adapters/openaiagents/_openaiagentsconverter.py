# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from __future__ import annotations

import inspect
import json
from typing import Any, Callable, Dict, List, Optional, Union

from pyagentspec.adapters._tools_common import _create_remote_tool_func
from pyagentspec.adapters.openaiagents._types import (
    OAAgent,
    OAChatCompletionsModel,
    OAFunctionTool,
    OAToolContext,
)
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.llms import LlmConfig as AgentSpecLlmConfig
from pyagentspec.llms.openaicompatibleconfig import (
    OpenAiCompatibleConfig as AgentSpecOpenAiCompatibleConfig,
)
from pyagentspec.llms.openaiconfig import OpenAiConfig as AgentSpecOpenAiConfig
from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.tools import Tool as AgentSpecTool
from pyagentspec.tools.clienttool import ClientTool as AgentSpecClientTool
from pyagentspec.tools.remotetool import RemoteTool as AgentSpecRemoteTool
from pyagentspec.tools.servertool import ServerTool as AgentSpecServerTool

_TargetTool = Union[OAFunctionTool, Callable[..., Any]]


class AgentSpecToOpenAIConverter:
    """
    Convert PyAgentSpec components to OpenAI Agents SDK equivalents.

    Supported:
      - AgentSpec OpenAiConfig -> model string
      - AgentSpec Agent -> agents.agent.Agent
      - AgentSpec Tools:
          * ServerTool -> OA FunctionTool from registry (prebuilt or wrapped callable)
          * ClientTool -> OA FunctionTool that prompts via input()
          * RemoteTool -> OA FunctionTool that performs HTTP request
    """

    def convert(
        self,
        comp: AgentSpecComponent,
        tool_registry: Dict[str, _TargetTool],
        conversion_cache: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if conversion_cache is None:
            conversion_cache = {}
        if comp.id in conversion_cache:
            return conversion_cache[comp.id]

        if isinstance(comp, AgentSpecLlmConfig):
            obj = self._llm_convert_to_openai(comp)
        elif isinstance(comp, AgentSpecAgent):
            obj = self._agent_convert_to_openai(comp, tool_registry, conversion_cache)
        elif isinstance(comp, AgentSpecTool):
            obj = self._tool_convert_to_openai(comp, tool_registry)
        elif isinstance(comp, AgentSpecComponent):
            raise NotImplementedError(
                f"The Agent Spec Component type '{comp.__class__.__name__}' is not yet supported "
                f"for conversion to OpenAI Agents."
            )
        else:
            raise TypeError(
                f"Expected object of type 'pyagentspec.component.Component', but got {type(comp)} instead"
            )

        conversion_cache[comp.id] = obj
        return obj

    def _llm_convert_to_openai(self, llm: AgentSpecLlmConfig) -> Any:
        if isinstance(llm, AgentSpecOpenAiConfig):
            # OpenAI Agents accepts model as str for default OpenAI models
            return llm.model_id
        elif isinstance(llm, AgentSpecOpenAiCompatibleConfig):
            from openai import AsyncOpenAI

            # Map any OpenAI-compatible endpoint via OAOpenAIProvider with custom base_url.
            # Construct a client with empty API key so it works for local/self-hosted deployments.
            base_url = llm.url
            if not base_url.startswith("http"):
                base_url = "http://" + base_url
            if not base_url.endswith("v1"):
                base_url += "/v1"
            client = AsyncOpenAI(api_key=llm.api_key or "", base_url=base_url)
            return OAChatCompletionsModel(llm.model_id, client)
        else:
            raise NotImplementedError(f"Unsupported LlmConfig: {type(llm)}")

    def _agent_convert_to_openai(
        self,
        agent: AgentSpecAgent,
        tool_registry: Dict[str, _TargetTool],
        conversion_cache: Dict[str, Any],
    ) -> OAAgent:
        model = self.convert(agent.llm_config, tool_registry, conversion_cache)
        tools = [self.convert(t, tool_registry, conversion_cache) for t in agent.tools]
        return OAAgent(
            name=agent.name,
            instructions=agent.system_prompt,
            model=model,
            tools=tools,
        )

    def _make_params_schema(self, props: List[AgentSpecProperty]) -> Dict[str, Any]:
        # Build strict JSON schema for FunctionTool params from AgentSpec properties
        properties: Dict[str, Dict[str, Any]] = {}
        required: List[str] = []
        for p in props or []:
            js: Dict[str, Any] = p.json_schema if isinstance(p.json_schema, dict) else {}
            title = js.get("title") or p.title
            # Use provided schema but drop the top-level "title" to avoid redundancy inside properties
            properties[title] = {k: v for k, v in js.items() if k != "title"}
            # Consider a field required if no default is defined in the schema
            if "default" not in js:
                required.append(title)
        schema: Dict[str, Any] = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        if required:
            schema["required"] = required
        return schema

    def _wrap_callable_as_function_tool(
        self, name: str, description: str, params_schema: Dict[str, Any], func: Callable[..., Any]
    ) -> OAFunctionTool:
        async def on_invoke_tool(ctx: "OAToolContext[Any]", input_json: str) -> Any:
            args = json.loads(input_json) if input_json else {}
            result = func(**args)
            if inspect.isawaitable(result):
                result = await result
            return result

        return OAFunctionTool(
            name=name,
            description=description or "",
            params_json_schema=params_schema,
            on_invoke_tool=on_invoke_tool,
            strict_json_schema=True,
        )

    def _client_function_tool(self, t: AgentSpecClientTool) -> OAFunctionTool:
        params_schema = self._make_params_schema(t.inputs or [])

        async def on_invoke_tool(ctx: "OAToolContext[Any]", input_json: str) -> Any:
            args = json.loads(input_json) if input_json else {}
            prompt = {
                "type": "client_tool_request",
                "name": t.name,
                "description": t.description,
                "inputs": args,
            }
            return input(f"{prompt} -> ")

        return OAFunctionTool(
            name=t.name,
            description=t.description or "",
            params_json_schema=params_schema,
            on_invoke_tool=on_invoke_tool,
            strict_json_schema=True,
        )

    def _remote_function_tool(self, t: AgentSpecRemoteTool) -> OAFunctionTool:
        params_schema = self._make_params_schema(t.inputs or [])
        remote_tool_func = _create_remote_tool_func(t)

        async def on_invoke_tool(ctx: "OAToolContext[Any]", input_json: str) -> Any:
            args = json.loads(input_json) if input_json else {}
            return remote_tool_func(**args)

        return OAFunctionTool(
            name=t.name,
            description=t.description or "",
            params_json_schema=params_schema,
            on_invoke_tool=on_invoke_tool,
            strict_json_schema=True,
        )

    def _tool_convert_to_openai(
        self,
        t: AgentSpecTool,
        tool_registry: Dict[str, _TargetTool],
    ) -> OAFunctionTool:
        if isinstance(t, AgentSpecServerTool):
            if t.name in tool_registry:
                impl = tool_registry[t.name]
                if isinstance(impl, OAFunctionTool):
                    return impl
                if callable(impl):
                    params_schema = self._make_params_schema(t.inputs or [])
                    return self._wrap_callable_as_function_tool(
                        name=t.name,
                        description=t.description or "",
                        params_schema=params_schema,
                        func=impl,
                    )
                raise ValueError(
                    f"Unsupported registry value type for tool '{t.name}': {type(impl)}"
                )
            raise ValueError(
                f"The implementation of the ServerTool '{t.name}' must be provided in the tool registry"
            )
        if isinstance(t, AgentSpecClientTool):
            return self._client_function_tool(t)
        if isinstance(t, AgentSpecRemoteTool):
            return self._remote_function_tool(t)
        raise TypeError(f"AgentSpec Tool of type {type(t)} is not supported")
