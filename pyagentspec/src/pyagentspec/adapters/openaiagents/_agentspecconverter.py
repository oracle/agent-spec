# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from __future__ import annotations

# OpenAI Agents SDK model classes for detection
from typing import Any, Dict, Optional, Sequence, Union, cast, get_args

from pyagentspec.adapters.openaiagents._types import (
    OAAgent,
    OAChatCompletionsModel,
    OAFunctionTool,
    OAResponsesModel,
)
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.llms import LlmConfig as AgentSpecLlmConfig
from pyagentspec.llms.openaicompatibleconfig import (
    OpenAiCompatibleConfig as AgentSpecOpenAiCompatibleConfig,
)
from pyagentspec.llms.openaiconfig import OpenAiConfig as AgentSpecOpenAiConfig
from pyagentspec.property import BooleanProperty as AgentSpecBooleanProperty
from pyagentspec.property import FloatProperty as AgentSpecFloatProperty
from pyagentspec.property import IntegerProperty as AgentSpecIntegerProperty
from pyagentspec.property import ListProperty as AgentSpecListProperty
from pyagentspec.property import NullProperty as AgentSpecNullProperty
from pyagentspec.property import ObjectProperty as AgentSpecObjectProperty
from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.property import StringProperty as AgentSpecStringProperty
from pyagentspec.property import UnionProperty as AgentSpecUnionProperty
from pyagentspec.tools import Tool as AgentSpecTool
from pyagentspec.tools.remotetool import RemoteTool as AgentSpecRemoteTool
from pyagentspec.tools.servertool import ServerTool as AgentSpecServerTool

from ._types import OAComponent, OAHostedTool


class OpenAIToAgentSpecConverter:
    """
    Convert OpenAI Agents SDK components to PyAgentSpec components.

    Supported:
      - agents.agent.Agent -> AgentSpec Agent
      - agents.tool.FunctionTool -> AgentSpec ServerTool
      - model (str) -> AgentSpec OpenAiConfig
    """

    def convert(
        self,
        obj: Union[OAComponent, Any],
        referenced_objects: Optional[Dict[str, AgentSpecComponent]] = None,
    ) -> AgentSpecComponent:
        if referenced_objects is None:
            referenced_objects = {}

        ref = f"{obj.__class__.__name__.lower()}/{id(obj)}"
        if ref in referenced_objects:
            return referenced_objects[ref]

        if isinstance(obj, OAAgent):
            comp: AgentSpecComponent = self._agent_convert_to_agentspec(obj, referenced_objects)
        elif isinstance(obj, OAFunctionTool):
            comp = self._tool_convert_to_agentspec(obj, referenced_objects)
        elif isinstance(obj, (str, OAResponsesModel, OAChatCompletionsModel)):
            comp = self._llm_convert_to_agentspec(obj, referenced_objects)
        elif isinstance(obj, get_args(OAHostedTool)):
            comp = self._hosted_tool_to_remote_tool(obj)
        else:
            raise NotImplementedError(f"Unsupported OpenAI Agents type: {type(obj)}.")

        referenced_objects[ref] = comp
        return comp

    def _agent_convert_to_agentspec(
        self, agent: OAAgent, referenced: Dict[str, AgentSpecComponent]
    ) -> AgentSpecAgent:
        # instructions must be a string for serialization (per plan)
        if agent.instructions is None or not isinstance(agent.instructions, str):
            raise NotImplementedError(
                "Only string Agent.instructions are supported for export to AgentSpec."
            )

        llm = self.convert(agent.model, referenced)
        agentspec_tools: list[AgentSpecComponent] = []
        for t in getattr(agent, "tools", []) or []:
            agentspec_tools.append(self.convert(t, referenced))

        # Attempt to map OpenAI Agent's structured output_type to AgentSpec outputs
        outputs: list[AgentSpecProperty] = []
        try:
            output_type = getattr(agent, "output_type", None)
            if output_type is not None and hasattr(output_type, "model_json_schema"):
                # Use the existing JSON Schema -> AgentSpec conversion helpers
                js = output_type.model_json_schema()  # pydantic v2
                outputs = self._agentspec_properties_from_params_schema(js)
        except Exception:
            outputs = []

        return AgentSpecAgent(
            name=agent.name,
            llm_config=cast(AgentSpecLlmConfig, llm),
            system_prompt=agent.instructions,
            tools=cast("list[AgentSpecTool]", agentspec_tools),
            outputs=outputs,
        )

    def _llm_convert_to_agentspec(
        self,
        model: Any,
        referenced: Dict[str, AgentSpecComponent],
    ) -> AgentSpecOpenAiConfig | AgentSpecOpenAiCompatibleConfig:
        # String model names map directly to OpenAI config
        if isinstance(model, str):
            return AgentSpecOpenAiConfig(name=model, model_id=model)

        # Detect OpenAI Agents SDK model instances (Responses/ChatCompletions)
        if isinstance(model, (OAResponsesModel, OAChatCompletionsModel)):
            raw_model_name = getattr(model, "model", None)
            model_name = str(raw_model_name) if raw_model_name is not None else ""
            if not model_name:
                raise ValueError(
                    "Cannot infer model_id from OpenAI Agents SDK model: missing 'model' field. "
                    "Pass a string model id (e.g., 'gpt-4.1') or ensure the SDK model exposes a non-empty 'model'."
                )

            # Probe for a base_url in several likely locations to avoid silent misclassification
            # Priority: model.base_url -> model._client.base_url -> model._client._base_url
            base_url = getattr(model, "base_url", None)
            if base_url is None:
                client = getattr(model, "_client", None)
                if client is None:
                    raise ValueError(
                        "Cannot determine endpoint for OpenAI Agents SDK model: missing '_client' and 'base_url'. "
                        "Without a resolvable base_url, we cannot guarantee whether this is OpenAI or compatible."
                    )
                base_url = getattr(client, "base_url", None)
                if base_url is None:
                    base_url = getattr(client, "_base_url", None)
                if base_url is None:
                    raise ValueError(
                        "Cannot determine endpoint for OpenAI Agents SDK model: client has no 'base_url'. "
                        "Please configure a base_url or provide the model as a string when targeting OpenAI."
                    )

            url_str = str(base_url)
            norm_url = url_str.rstrip("/") if url_str else None

            # If default OpenAI URL, treat as pure OpenAI model; otherwise, OpenAI-compatible
            if norm_url and "api.openai.com" not in norm_url:
                return AgentSpecOpenAiCompatibleConfig(
                    name=model_name, model_id=model_name, url=norm_url
                )
            if norm_url is None:
                # Should not happen due to guards above, but keep a defensive check
                raise ValueError(
                    "Ambiguous endpoint: resolved base_url is empty. Cannot safely infer provider."
                )
            return AgentSpecOpenAiConfig(name=model_name, model_id=model_name)

        raise NotImplementedError(
            f"Unsupported model type for export: {type(model)}. Expected str or OpenAIAgents Model."
        )

    def _tool_convert_to_agentspec(
        self, tool: OAFunctionTool, referenced: Dict[str, AgentSpecComponent]
    ) -> AgentSpecServerTool:
        inputs = self._agentspec_properties_from_params_schema(tool.params_json_schema)
        # FunctionTool has no declared return schema; default to a single string "Output"
        outputs: Sequence[AgentSpecProperty] = [AgentSpecStringProperty(title="Output")]
        return AgentSpecServerTool(
            name=tool.name,
            description=tool.description or "",
            inputs=inputs,
            outputs=list(outputs),
        )

    def _hosted_tool_to_remote_tool(self, tool: Any) -> AgentSpecRemoteTool:
        name = getattr(tool, "name", tool.__class__.__name__.lower())
        description = getattr(tool, "description", "") if hasattr(tool, "description") else ""
        url = f"openai://hosted/{name}"
        return AgentSpecRemoteTool(
            name=name,
            description=description,
            http_method="POST",
            url=url,
            headers={},
            query_params={},
            data={},
            inputs=[],
            outputs=[AgentSpecStringProperty(title="Output")],
        )

    # ----- JSON schema -> AgentSpec Property conversion helpers -----

    def _agentspec_properties_from_params_schema(
        self, schema: Dict[str, Any]
    ) -> list[AgentSpecProperty]:
        # Expect type object with properties; convert recursively
        if not schema or schema.get("type") != "object":
            return []
        props_schema = cast(Dict[str, Any], schema.get("properties") or {})
        props: list[AgentSpecProperty] = []
        for k, v in props_schema.items():
            props.append(self._from_json_schema(v, title=k))
        return props

    def _from_json_schema(self, js: Dict[str, Any], title: str) -> AgentSpecProperty:
        # anyOf -> UnionProperty
        if "anyOf" in js:
            return AgentSpecUnionProperty(
                title=title,
                any_of=[self._from_json_schema(x, title=title) for x in js["anyOf"]],
                description=js.get("description", ""),
            )
        t = js.get("type")
        if isinstance(t, list):
            # collapse type list to Union
            return AgentSpecUnionProperty(
                title=title,
                any_of=[
                    self._from_json_schema(
                        {"type": x, **({"items": js.get("items")} if x == "array" else {})},
                        title=title,
                    )
                    for x in t
                ],
                description=js.get("description", ""),
            )

        if t == "array":
            item_schema = js.get("items", {}) or {}
            item_prop = self._from_json_schema(item_schema, title=title)
            return AgentSpecListProperty(
                title=title, item_type=item_prop, description=js.get("description", "")
            )

        if t == "object":
            properties: Dict[str, AgentSpecProperty] = {
                name: self._from_json_schema(val, title=name)
                for name, val in cast(Dict[str, Any], js.get("properties") or {}).items()
            }
            # If additionalProperties is present and not False, map to DictProperty semantics by merging into properties
            if "additionalProperties" in js and js["additionalProperties"] not in (False, None, {}):
                # Represent as object with additionalProperties; AgentSpec doesn't have an explicit flag,
                # but we can approximate with ObjectProperty and allow runtime to accept additional props.
                pass
            return AgentSpecObjectProperty(
                title=title, properties=properties, description=js.get("description", "")
            )

        if t == "string":
            return AgentSpecStringProperty(title=title, description=js.get("description", ""))
        if t == "integer":
            return AgentSpecIntegerProperty(title=title, description=js.get("description", ""))
        if t == "number":
            return AgentSpecFloatProperty(title=title, description=js.get("description", ""))
        if t == "boolean":
            return AgentSpecBooleanProperty(title=title, description=js.get("description", ""))
        if t == "null":
            return AgentSpecNullProperty(title=title, description=js.get("description", ""))

        # Fallback to string to keep schema permissive
        return AgentSpecStringProperty(title=title, description=js.get("description", ""))
