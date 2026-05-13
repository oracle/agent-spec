# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Callable, Dict, List, Optional, Union, cast, overload

from pyagentspec.adapters._agentspecloader import AdapterAgnosticAgentSpecLoader
from pyagentspec.adapters.openaiagents._agentspecconverter import OpenAIToAgentSpecConverter
from pyagentspec.adapters.openaiagents._openaiagentsconverter import (
    AgentSpecToOpenAIConverter,
    _TargetTool,
)
from pyagentspec.adapters.openaiagents._types import OAAgent
from pyagentspec.adapters.openaiagents.flows._rulepack_registry import resolve_rulepack
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.flows.flow import Flow as AgentSpecFlow
from pyagentspec.serialization import ComponentDeserializationPlugin
from pyagentspec.serialization.componentpolicy import ComponentPolicyInput

_OAComponent = Union[OAAgent, str]


def _load_component(
    agent_spec_loader: AdapterAgnosticAgentSpecLoader,
    agentspec_component: AgentSpecComponent,
    output_path: str | None = None,
    module_name: str | None = None,
    rulepack_version: str | None = None,
) -> Any:
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
        # Flow codegen bypasses the base loader's conversion path, so enforce the
        # component policy here before generating executable Python source.
        agent_spec_loader.component_load_policy.validate_component_tree(agentspec_component)
        pack = resolve_rulepack(rulepack_version)
        ir = pack.agentspec_to_ir(agentspec_component, strict=True)
        mod = pack.codegen(ir, module_name=module_name)
        code = mod.code
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(code)
        return code

    return AdapterAgnosticAgentSpecLoader.load_component(agent_spec_loader, agentspec_component)


class AgentSpecLoader(AdapterAgnosticAgentSpecLoader):
    """Helper class to convert Agent Spec configurations to OpenAI Agents SDK objects.

    ``allowed_components`` and ``blocked_components`` can be used to constrain
    which Agent Spec component types load. Resolvable type names and Component
    classes match subclasses; unresolved type names match only the exact serialized
    component type. When allow and block entries both match, the closest match
    in the component class hierarchy wins; block entries win same-distance ties.
    """

    def __init__(
        self,
        tool_registry: Optional[Dict[str, _TargetTool]] = None,
        plugins: Optional[List[ComponentDeserializationPlugin]] = None,
        *,
        allowed_components: Optional[ComponentPolicyInput] = None,
        blocked_components: Optional[ComponentPolicyInput] = None,
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
        allowed_components:
            Optional iterable of Agent Spec component type names or Component classes allowed
            to be loaded. If omitted, all component types are allowed unless blocked.
        blocked_components:
            Optional iterable of Agent Spec component type names or Component classes blocked
            from loading. If omitted, stdio MCP transports are blocked by default.
            Resolvable type names and Component classes also match subclasses; unresolved
            type names match only the exact serialized component type. When allow and
            block entries both match, the closest match in the component class hierarchy
            wins; block entries win same-distance ties.
        """
        super().__init__(
            plugins=plugins,
            tool_registry=tool_registry,
            allowed_components=allowed_components,
            blocked_components=blocked_components,
        )

    @property
    def agentspec_to_runtime_converter(self) -> AgentSpecToOpenAIConverter:
        return AgentSpecToOpenAIConverter()

    @property
    def runtime_to_agentspec_converter(self) -> OpenAIToAgentSpecConverter:
        return OpenAIToAgentSpecConverter()

    def _patch_load_component(
        self,
        output_path: str | None,
        module_name: str | None,
        rulepack_version: str | None,
    ) -> Callable[[AgentSpecComponent], _OAComponent]:

        def _patched_load_component(agentspec_component: AgentSpecComponent) -> Any:
            return _load_component(
                agent_spec_loader=self,
                agentspec_component=agentspec_component,
                output_path=output_path,
                module_name=module_name,
                rulepack_version=rulepack_version,
            )

        return _patched_load_component

    def load_yaml(
        self,
        serialized_assistant: str,
        components_registry: Dict[str, Any] | None = None,
        import_only_referenced_components: bool = False,
        output_path: str | None = None,
        module_name: str | None = None,
        rulepack_version: str | None = None,
    ) -> Union[_OAComponent, Dict[str, _OAComponent]]:
        """
        Transform the given Agent Spec YAML representation into an OpenAI Agents component.

        Parameters
        ----------
        serialized_assistant: Agent Spec describing the agent or flow to load.
        components_registry:
            Optional registry mapping ids to OpenAI components/values. The loader will
            convert these back to Agent Spec components/values internally to resolve
            references during deserialization.
        import_only_referenced_components:
            When ``True``, loads only the referenced/disaggregated components and returns a
            dictionary mapping component id to OpenAI components/values. These can be
            used as the ``components_registry`` when loading the main configuration. When
            ``False``, loads the main component and returns the OpenAI component.
        output_path: Optional file path to write the generated source.
        module_name: Optional module name to stamp in generated code.
        rulepack_version: Optional explicit RulePack version; defaults to SDK version.

        Notes
        -----
        - If the YAML represents an Agent Spec component (e.g., Agent), returns an OpenAI Agent.
        - If the YAML represents an Agent Spec Flow, returns the generated Python source as a string.

        Examples
        --------
        Load an Agent Spec agent as an OpenAI Agents SDK Agent:

        >>> from pyagentspec.agent import Agent
        >>> from pyagentspec.llms import OllamaConfig
        >>> from pyagentspec.serialization import AgentSpecSerializer
        >>> agentspec_agent = Agent(
        ...     id="agent_id",
        ...     name="A",
        ...     system_prompt="You are helpful.",
        ...     llm_config=OllamaConfig(name="m", model_id="llama3.1", url="http://localhost:11434"),
        ... )
        >>> yaml_str = AgentSpecSerializer().to_yaml(agentspec_agent)
        >>> from pyagentspec.adapters.openaiagents import AgentSpecLoader
        >>> loader = AgentSpecLoader()
        >>> oa_agent = loader.load_yaml(yaml_str)

        Generate Python source for an Agent Spec Flow:

        >>> from pyagentspec.adapters.openaiagents import AgentSpecLoader
        >>> from pyagentspec.flows.nodes import StartNode, EndNode
        >>> from pyagentspec.flows.flow import Flow
        >>> from pyagentspec.flows.edges import ControlFlowEdge
        >>> start_node = StartNode(name="start")
        >>> end_node = EndNode(name="end")
        >>> flow = Flow(
        ...     name="F",
        ...     start_node=start_node,
        ...     nodes=[start_node, end_node],
        ...     control_flow_connections=[ControlFlowEdge(name="c", from_node=start_node, to_node=end_node)],
        ... )
        >>> flow_yaml = AgentSpecSerializer().to_yaml(flow)
        >>> source = AgentSpecLoader().load_yaml(flow_yaml, module_name="my_flow")

        """
        # mypy: this adapter intentionally extends the base `load_yaml` signature
        # with codegen-only params (output_path/module_name/rulepack_version).
        # Behavior remains identical when those params are unused.
        # This adapter's extra arguments are used only for flow codegen.
        # When omitted, behavior matches AdapterAgnosticAgentSpecLoader.
        if output_path is None and module_name is None and rulepack_version is None:
            return cast(
                Union[_OAComponent, Dict[str, _OAComponent]],
                super().load_yaml(
                    serialized_assistant,
                    components_registry=components_registry,
                    import_only_referenced_components=import_only_referenced_components,
                ),
            )

        try:
            patched_load_component = self._patch_load_component(
                output_path=output_path,
                module_name=module_name,
                rulepack_version=rulepack_version,
            )
            original_load_component = self.load_component
            self.load_component = patched_load_component  # type: ignore
            return cast(
                Union[_OAComponent, Dict[str, _OAComponent]],
                super().load_yaml(
                    serialized_assistant,
                    components_registry=components_registry,
                    import_only_referenced_components=import_only_referenced_components,
                ),
            )
        finally:
            self.load_component = original_load_component  # type: ignore

    @overload
    def load_json(self, serialized_assistant: str) -> _OAComponent: ...

    @overload
    def load_json(
        self,
        serialized_assistant: str,
        components_registry: Dict[str, Any] | None = None,
    ) -> _OAComponent: ...

    @overload
    def load_json(
        self,
        serialized_assistant: str,
        *,
        import_only_referenced_components: bool,
    ) -> Union[_OAComponent, Dict[str, _OAComponent]]: ...

    @overload
    def load_json(
        self,
        serialized_assistant: str,
        components_registry: Dict[str, Any] | None = None,
        import_only_referenced_components: bool = False,
    ) -> Union[_OAComponent, Dict[str, _OAComponent]]: ...

    def load_json(
        self,
        serialized_assistant: str,
        components_registry: Dict[str, Any] | None = None,
        import_only_referenced_components: bool = False,
        output_path: str | None = None,
        module_name: str | None = None,
        rulepack_version: str | None = None,
    ) -> Union[_OAComponent, Dict[str, _OAComponent]]:
        """
        Transform the given Agent Spec JSON representation into an OpenAI Agents component.

        Parameters
        ----------
        serialized_assistant: Agent Spec describing the agent or flow to load.
        components_registry:
            Optional registry mapping ids to OpenAI components/values. The loader will
            convert these back to Agent Spec components/values internally to resolve
            references during deserialization.
        import_only_referenced_components:
            When ``True``, loads only the referenced/disaggregated components and returns a
            dictionary mapping component id to OpenAI components/values. These can be
            used as the ``components_registry`` when loading the main configuration. When
            ``False``, loads the main component and returns the OpenAI component.
        output_path: Optional file path to write the generated source.
        module_name: Optional module name to stamp in generated code.
        rulepack_version: Optional explicit RulePack version; defaults to SDK version.

        Notes
        -----
        - If the JSON represents an Agent Spec component (e.g., Agent), returns an OpenAI Agent.
        - If the JSON represents an Agent Spec Flow, returns the generated Python source as a string.

        Examples
        --------
        Load an Agent Spec agent as an OpenAI Agents SDK Agent:

        >>> from pyagentspec.agent import Agent
        >>> from pyagentspec.llms import OllamaConfig
        >>> from pyagentspec.serialization import AgentSpecSerializer
        >>> agentspec_agent = Agent(
        ...     id="agent_id",
        ...     name="A",
        ...     system_prompt="You are helpful.",
        ...     llm_config=OllamaConfig(id="llm_id", name="m", model_id="llama3.1", url="http://localhost:11434"),
        ... )
        >>> json_str = AgentSpecSerializer().to_json(agentspec_agent)
        >>> from pyagentspec.adapters.openaiagents import AgentSpecLoader
        >>> loader = AgentSpecLoader()
        >>> oa_agent = loader.load_json(json_str)

        Generate Python source for an Agent Spec Flow:

        >>> from pyagentspec.flows.edges import ControlFlowEdge
        >>> start_node = StartNode(name="start")
        >>> end_node = EndNode(name="end")
        >>> flow = Flow(
        ...     name="F",
        ...     start_node=start_node,
        ...     nodes=[start_node, end_node],
        ...     control_flow_connections=[ControlFlowEdge(name="c", from_node=start_node, to_node=end_node)],
        ... )
        >>> flow_json = AgentSpecSerializer().to_json(flow)
        >>> source = AgentSpecLoader().load_json(flow_json, module_name="my_flow")

        """
        if output_path is None and module_name is None and rulepack_version is None:
            return cast(
                Union[_OAComponent, Dict[str, _OAComponent]],
                super().load_json(
                    serialized_assistant,
                    components_registry=components_registry,
                    import_only_referenced_components=import_only_referenced_components,
                ),
            )

        try:
            patched_load_component = self._patch_load_component(
                output_path=output_path,
                module_name=module_name,
                rulepack_version=rulepack_version,
            )
            original_load_component = self.load_component
            self.load_component = patched_load_component  # type: ignore
            return cast(
                Union[_OAComponent, Dict[str, _OAComponent]],
                super().load_json(
                    serialized_assistant,
                    components_registry=components_registry,
                    import_only_referenced_components=import_only_referenced_components,
                ),
            )
        finally:
            self.load_component = original_load_component  # type: ignore

    @overload
    def load_dict(self, serialized_assistant: Dict[str, Any]) -> _OAComponent: ...

    @overload
    def load_dict(
        self,
        serialized_assistant: Dict[str, Any],
        components_registry: Dict[str, Any] | None = None,
    ) -> _OAComponent: ...

    @overload
    def load_dict(
        self,
        serialized_assistant: Dict[str, Any],
        *,
        import_only_referenced_components: bool,
    ) -> Union[_OAComponent, Dict[str, _OAComponent]]: ...

    @overload
    def load_dict(
        self,
        serialized_assistant: Dict[str, Any],
        components_registry: Dict[str, Any] | None = None,
        import_only_referenced_components: bool = False,
    ) -> Union[_OAComponent, Dict[str, _OAComponent]]: ...

    def load_dict(
        self,
        serialized_assistant: Dict[str, Any],
        components_registry: Dict[str, Any] | None = None,
        import_only_referenced_components: bool = False,
        output_path: str | None = None,
        module_name: str | None = None,
        rulepack_version: str | None = None,
    ) -> Union[_OAComponent, Dict[str, _OAComponent]]:
        """
        Transform the given Agent Spec dict representation into an OpenAI Agents component.

        Parameters
        ----------
        serialized_assistant: Agent Spec describing the agent or flow to load.
        components_registry:
            Optional registry mapping ids to OpenAI components/values. The loader will
            convert these back to Agent Spec components/values internally to resolve
            references during deserialization.
        import_only_referenced_components:
            When ``True``, loads only the referenced/disaggregated components and returns a
            dictionary mapping component id to OpenAI components/values. These can be
            used as the ``components_registry`` when loading the main configuration. When
            ``False``, loads the main component and returns the OpenAI component.
        output_path: Optional file path to write the generated source.
        module_name: Optional module name to stamp in generated code.
        rulepack_version: Optional explicit RulePack version; defaults to SDK version.

        Notes
        -----
        - If the dict represents an Agent Spec component (e.g., Agent), returns an OpenAI Agent.
        - If the dict represents an Agent Spec Flow, returns the generated Python source as a string.

        Examples
        --------
        Load an Agent Spec agent as an OpenAI Agents SDK Agent:

        >>> from pyagentspec.agent import Agent
        >>> from pyagentspec.llms import OllamaConfig
        >>> agentspec_agent = Agent(
        ...     id="agent_id",
        ...     name="A",
        ...     system_prompt="You are helpful.",
        ...     llm_config=OllamaConfig(id="llm_id", name="m", model_id="llama3.1", url="http://localhost:11434"),
        ... )
        >>> from pyagentspec.serialization import AgentSpecSerializer
        >>> agentspec_dict = AgentSpecSerializer().to_dict(agentspec_agent)
        >>> from pyagentspec.adapters.openaiagents import AgentSpecLoader
        >>> loader = AgentSpecLoader()
        >>> oa_agent = loader.load_dict(agentspec_dict)

        Generate Python source for an Agent Spec Flow:

        >>> from pyagentspec.adapters.openaiagents import AgentSpecLoader
        >>> from pyagentspec.flows.nodes import StartNode, EndNode
        >>> from pyagentspec.flows.flow import Flow
        >>> from pyagentspec.flows.edges import ControlFlowEdge
        >>> start_node = StartNode(name="start")
        >>> end_node = EndNode(name="end")
        >>> flow = Flow(
        ...     name="F",
        ...     start_node=start_node,
        ...     nodes=[start_node, end_node],
        ...     control_flow_connections=[ControlFlowEdge(name="c", from_node=start_node, to_node=end_node)],
        ... )
        >>> flow_dict = AgentSpecSerializer().to_dict(flow)
        >>> source = AgentSpecLoader().load_dict(flow_dict, module_name="my_flow")

        """
        if output_path is None and module_name is None and rulepack_version is None:
            return cast(
                Union[_OAComponent, Dict[str, _OAComponent]],
                super().load_dict(
                    serialized_assistant,
                    components_registry=components_registry,
                    import_only_referenced_components=import_only_referenced_components,
                ),
            )

        try:
            patched_load_component = self._patch_load_component(
                output_path=output_path,
                module_name=module_name,
                rulepack_version=rulepack_version,
            )
            original_load_component = self.load_component
            self.load_component = patched_load_component  # type: ignore
            return cast(
                Union[_OAComponent, Dict[str, _OAComponent]],
                super().load_dict(
                    serialized_assistant,
                    components_registry=components_registry,
                    import_only_referenced_components=import_only_referenced_components,
                ),
            )
        finally:
            self.load_component = original_load_component  # type: ignore

    def load_component(
        self,
        agentspec_component: AgentSpecComponent,
        output_path: str | None = None,
        module_name: str | None = None,
        rulepack_version: str | None = None,
    ) -> _OAComponent:
        return cast(
            _OAComponent,
            _load_component(
                agent_spec_loader=self,
                agentspec_component=agentspec_component,
                output_path=output_path,
                module_name=module_name,
                rulepack_version=rulepack_version,
            ),
        )
