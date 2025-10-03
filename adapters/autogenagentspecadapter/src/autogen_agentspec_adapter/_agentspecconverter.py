# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

import json
import types
from typing import Any, Dict, Optional, Union, cast, get_args, get_origin

from autogen_agentchat.agents import AssistantAgent as AutogenAssistantAgent
from autogen_agentchat.agents import BaseChatAgent as AutogenBaseAgent
from autogen_core import Component as AutogenComponent
from autogen_core.models import ChatCompletionClient as AutogenChatCompletionClient
from autogen_core.tools import BaseTool as AutogenBaseTool
from autogen_core.tools import FunctionTool as AutogenFunctionTool
from autogen_ext.models.ollama import (
    OllamaChatCompletionClient as AutogenOllamaChatCompletionClient,
)
from autogen_ext.models.openai import (
    OpenAIChatCompletionClient as AutogenOpenAIChatCompletionClient,
)

from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.llms import LlmConfig as AgentSpecLlmConfig
from pyagentspec.llms.ollamaconfig import OllamaConfig as AgentSpecOllamaModel
from pyagentspec.llms.openaiconfig import OpenAiConfig as AgentSpecOpenAiModel
from pyagentspec.llms.vllmconfig import VllmConfig as AgentSpecVllmModel
from pyagentspec.property import BooleanProperty as AgentSpecBooleanProperty
from pyagentspec.property import FloatProperty as AgentSpecFloatProperty
from pyagentspec.property import IntegerProperty as AgentSpecIntegerProperty
from pyagentspec.property import ListProperty as AgentSpecListProperty
from pyagentspec.property import NullProperty as AgentSpecNullProperty
from pyagentspec.property import ObjectProperty as AgentSpecObjectProperty
from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.property import StringProperty as AgentSpecStringProperty
from pyagentspec.property import UnionProperty as AgentSpecUnionProperty
from pyagentspec.tools import ServerTool as AgentSpecServerTool
from pyagentspec.tools import Tool as AgentSpecTool


class AutogenToAgentSpecConverter:
    """
    Provides methods to convert various types of Autogen components into their corresponding PyAgentSpec components.
    """

    def convert(
        self,
        autogen_component: Union[
            AutogenComponent[Any],
            AutogenBaseTool[Any, Any],
            AutogenChatCompletionClient,
        ],
        referenced_objects: Optional[Dict[str, AgentSpecComponent]] = None,
    ) -> AgentSpecComponent:
        """
        Convert an Autogen component to its corresponding PyAgentSpec component.

        Parameters:
        - autogen_component: The Autogen component to be converted.
        - referenced_objects: A dictionary to keep track of already converted objects.

        Returns:
        -------
        AgentSpecComponent
            The converted PyAgentSpec component.
        """

        if referenced_objects is None:
            referenced_objects = dict()

        # Reuse the same object multiple times in order to exploit the referencing system
        object_reference = _get_obj_reference(autogen_component)
        if object_reference in referenced_objects:
            return referenced_objects[object_reference]

        # If we did not find the object, we create it, and we record it in the referenced_objects registry
        agentspec_component: AgentSpecComponent
        if isinstance(autogen_component, AutogenChatCompletionClient):
            agentspec_component = self._llm_convert_to_agentspec(
                autogen_component, referenced_objects
            )
        elif isinstance(autogen_component, AutogenBaseAgent):
            agentspec_component = self._agent_convert_to_agentspec(
                autogen_component, referenced_objects
            )
        elif isinstance(autogen_component, AutogenBaseTool):
            agentspec_component = self._tool_convert_to_agentspec(
                autogen_component, referenced_objects
            )
        else:
            raise NotImplementedError(
                f"The autogen type '{autogen_component.__class__.__name__}' is not yet supported "
                f"for conversion. It is very easy to add support, you should do it!"
            )
        referenced_objects[object_reference] = agentspec_component
        return referenced_objects[object_reference]

    def _llm_convert_to_agentspec(
        self,
        autogen_llm: AutogenChatCompletionClient,
        referenced_objects: Optional[Dict[str, Any]] = None,
    ) -> AgentSpecLlmConfig:
        """
        Convert an AutogenChatCompletionClient to an AgentSpecLlmConfig.

        Parameters:
        - autogen_llm: The Autogen LLM to be converted.
        - referenced_objects: A dictionary to keep track of already converted objects.

        Returns:
        -------
        AgentSpecLlmConfig
            The converted AgentSpecLlmConfig.

        Raises:
        ------
        ValueError
            If the type of LLM is unsupported.
        """
        if isinstance(autogen_llm, AutogenOllamaChatCompletionClient):
            _autogen_component = autogen_llm.dump_component()
            return AgentSpecOllamaModel(
                name=_autogen_component.config["model"],
                model_id=_autogen_component.config["model"],
                url=_autogen_component.config["host"],
            )
        elif isinstance(autogen_llm, AutogenOpenAIChatCompletionClient):
            _autogen_component = autogen_llm.dump_component()
            if "base_url" in _autogen_component.config and _autogen_component.config["base_url"]:
                return AgentSpecVllmModel(
                    name=_autogen_component.config["model"],
                    model_id=_autogen_component.config["model"],
                    url=_autogen_component.config["base_url"],
                    metadata={
                        "model_info": json.dumps(_autogen_component.config.get("model_info", {})),
                    },
                )
            return AgentSpecOpenAiModel(
                name=_autogen_component.config["model"],
                model_id=_autogen_component.config["model"],
            )
        raise ValueError(f"Unsupported type of LLM in agentspec: {type(autogen_llm)}")

    def _agentspec_input_property_from_type(
        self, prop_val: Dict[str, Any], title: str, description: str
    ) -> AgentSpecProperty:
        if prop_val["type"] == "string":
            return AgentSpecStringProperty(title=title, description=description)
        elif prop_val["type"] == "integer":
            return AgentSpecIntegerProperty(title=title, description=description)
        elif prop_val["type"] == "boolean":
            return AgentSpecBooleanProperty(title=title, description=description)
        elif prop_val["type"] == "number":
            return AgentSpecFloatProperty(title=title, description=description)
        elif prop_val["type"] == "null":
            return AgentSpecNullProperty(title=title, description=description)
        else:
            raise NotImplementedError(f"Unsupported type of output property: {prop_val['type']}")

    def _agentspec_output_property_from_type(
        self, _type: Any, title: str = "Output"
    ) -> AgentSpecProperty:
        """Map a Python/typing type to a corresponding AgentSpec/pyagentspec Property."""
        # Handle built-ins and simple types
        type_name = getattr(_type, "__name__", str(_type))
        if type_name == "str":
            return AgentSpecStringProperty(title=title)
        elif type_name == "int":
            return AgentSpecIntegerProperty(title=title)
        elif type_name == "float":
            return AgentSpecFloatProperty(title=title)
        elif type_name == "bool":
            return AgentSpecBooleanProperty(title=title)
        elif type_name == "NoneType":
            return AgentSpecNullProperty(title=title)
        raise NotImplementedError(f"Unsupported type of output property: {type_name}")

    def make_agentspec_output_property(
        self, _type: Any, title: str = "Output"
    ) -> AgentSpecProperty:
        origin = get_origin(_type)
        args = get_args(_type)
        if (origin is Union) or (hasattr(types, "UnionType") and origin is types.UnionType):
            union_properties = [
                self.make_agentspec_output_property(arg, title=title) for arg in args
            ]
            return AgentSpecUnionProperty(title=title, any_of=union_properties)
        elif origin is list:
            inner_type = args[0] if args else Any
            item_property = self.make_agentspec_output_property(inner_type, title=title)
            return AgentSpecListProperty(title=title, item_type=item_property)
        elif origin is dict:
            object_properties = {
                prop_name: self.make_agentspec_output_property(prop_type, title=prop_name)
                for prop_name, prop_type in getattr(_type, "__annotations__", {}).items()
            }
            return AgentSpecObjectProperty(title=title, properties=object_properties)
        else:
            return self._agentspec_output_property_from_type(_type, title=title)

    def make_agentspec_input_property(
        self, prop_val: Dict[str, Any], title: str, description: str
    ) -> AgentSpecProperty:

        if "anyOf" in prop_val:
            union_items = prop_val.get("anyOf") or []
            union_properties = [
                self.make_agentspec_input_property(item, title=title, description=description)
                for item in union_items
            ]
            return AgentSpecUnionProperty(
                title=title, description=description, any_of=union_properties
            )
        elif prop_val["type"] == "array":
            item_property = self.make_agentspec_input_property(
                prop_val["items"], title=title, description=description
            )
            return AgentSpecListProperty(
                title=title, description=description, item_type=item_property
            )
        elif prop_val["type"] == "object":
            props = prop_val.get("properties", {})
            dict_properties = {
                k: self.make_agentspec_input_property(
                    v, title=k, description=v.get("description", "")
                )
                for k, v in props.items()
            }
            return AgentSpecObjectProperty(
                title=title, description=description, properties=dict_properties
            )
        else:
            return self._agentspec_input_property_from_type(
                prop_val, title=title, description=description
            )

    def _tool_convert_to_agentspec(
        self,
        autogen_tool: AutogenBaseTool[Any, Any],
        referenced_objects: Optional[Dict[str, Any]] = None,
    ) -> AgentSpecTool:
        """
        Convert an AutogenBaseTool to an AgentSpecTool.

        Parameters:
        - autogen_tool: The Autogen tool to be converted.
        - referenced_objects: A dictionary to keep track of already converted objects.

        Returns:
        -------
        AgentSpecTool
            The converted AgentSpecTool.

        Raises:
        ------
        ValueError
            If the type of tool is unsupported.
        """
        if isinstance(autogen_tool, AutogenFunctionTool):
            _schema = autogen_tool.schema
            _schema_properties = _schema["parameters"]["properties"]
            _return_type = autogen_tool._signature.return_annotation
            _inputs = []
            for prop_val in _schema_properties.values():
                _input = self.make_agentspec_input_property(
                    prop_val=prop_val, title=prop_val["title"], description=prop_val["description"]
                )
                _inputs.append(_input)

            _outputs = []
            _output = self.make_agentspec_output_property(_return_type)
            _outputs.append(_output)

            return AgentSpecServerTool(
                name=_schema["name"],
                description=_schema["description"],
                inputs=_inputs,
                outputs=_outputs,
            )
        raise ValueError(f"Unsupported type of Tool in AgentSpec: {type(autogen_tool)}")

    def _agent_convert_to_agentspec(
        self, autogen_agent: AutogenBaseAgent, referenced_objects: Optional[Dict[str, Any]] = None
    ) -> AgentSpecAgent:
        """
        Convert an AutogenBaseAgent to an AgentSpecAgent.

        Parameters:
        - autogen_agent: The Autogen agent to be converted.
        - referenced_objects: A dictionary to keep track of already converted objects.

        Returns:
        -------
        AgentSpecAgent
            The converted AgentSpecAgent.

        Raises:
        ------
        ValueError
            If the type of agent is unsupported.
        """
        if isinstance(autogen_agent, AutogenAssistantAgent):
            _autogen_component = autogen_agent.dump_component()
            agentspec_llm_config = self.convert(autogen_agent._model_client, referenced_objects)
            agentspec_tools = [
                t
                for t in (self.convert(_tool, referenced_objects) for _tool in autogen_agent._tools)
                if isinstance(t, AgentSpecTool)
            ]
            return AgentSpecAgent(
                name=_autogen_component.config["name"],
                description=_autogen_component.description,
                llm_config=cast(AgentSpecLlmConfig, agentspec_llm_config),
                system_prompt=_autogen_component.config["system_message"],
                tools=agentspec_tools,
            )
        raise ValueError(f"Unsupported type of agent in AgentSpec: {type(autogen_agent)}")


def _get_obj_reference(obj: Any) -> str:
    return f"{obj.__class__.__name__.lower()}/{id(obj)}"
