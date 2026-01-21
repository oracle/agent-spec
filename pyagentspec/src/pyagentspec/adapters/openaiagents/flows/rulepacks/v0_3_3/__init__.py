# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from __future__ import annotations

from dataclasses import asdict
from typing import Any, cast

from pyagentspec.adapters.openaiagents.flows._flow_ir import (
    IRControlEdge,
    IRDataEdge,
    IRFlow,
    IRNode,
)
from pyagentspec.adapters.openaiagents.flows._rulepack_registry import register_rulepack
from pyagentspec.adapters.openaiagents.flows.errors import UnsupportedPatternError
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow as AgentSpecFlow
from pyagentspec.flows.nodes.agentnode import AgentNode
from pyagentspec.flows.nodes.branchingnode import BranchingNode
from pyagentspec.flows.nodes.endnode import EndNode
from pyagentspec.flows.nodes.llmnode import LlmNode
from pyagentspec.flows.nodes.outputmessagenode import OutputMessageNode
from pyagentspec.flows.nodes.startnode import StartNode
from pyagentspec.flows.nodes.toolnode import ToolNode
from pyagentspec.serialization.deserializer import AgentSpecDeserializer
from pyagentspec.serialization.serializer import AgentSpecSerializer


def _sdk_version() -> str:
    try:
        from agents.version import __version__ as sdk_version
    except Exception:
        sdk_version = "0.0.0"
    return sdk_version


# Shared mapping for json-schema type name -> Property class
from pyagentspec.property import (
    BooleanProperty,
    IntegerProperty,
    NumberProperty,
    StringProperty,
)

_TYPE_NAME_TO_PROPERTY_CLASS = {
    "string": StringProperty,
    "integer": IntegerProperty,
    "number": NumberProperty,
    "boolean": BooleanProperty,
}


class V0RulePack:
    """Initial RulePack targeting the vendored SDK version.

    Implements IR ↔ Agent Spec mapping and delegates parser/codegen.
    """

    version: str = _sdk_version()

    # ----- Reverse parsing (Python -> IR) -----
    def python_flow_to_ir(self, mod: Any, *, strict: bool = True) -> IRFlow:
        # Delegate to LibCST-based reverse parser for v0
        from .ast_parser import FlowASTParser  # local import

        parser = FlowASTParser(strict=strict)
        src = getattr(mod, "code", None)
        if not isinstance(src, str):
            src = str(mod)
        return parser.parse(src, flow_name="workflow")

    # ----- IR -> Agent Spec -----
    def ir_to_agentspec(self, ir: IRFlow, *, strict: bool = True) -> AgentSpecFlow:
        id_to_node: dict[str, Any] = {}

        for n in ir.nodes:
            node: Any
            if n.kind == "start":
                inputs: list[Any] = []
                start_outputs: list[Any] = []
                try:
                    type_map = _TYPE_NAME_TO_PROPERTY_CLASS
                    meta_io = n.meta
                    for p in meta_io.get("inputs", []) or []:
                        cls = type_map.get(p.get("type"))
                        if cls:
                            inputs.append(cls(title=p.get("title")))
                    for p in meta_io.get("outputs", []) or []:
                        cls = type_map.get(p.get("type"))
                        if cls:
                            start_outputs.append(cls(title=p.get("title")))
                except Exception:
                    inputs = []
                    start_outputs = []
                node = StartNode(name=n.name, inputs=inputs or None, outputs=start_outputs or None)
            elif n.kind == "end":
                end_outputs: list[Any] = []
                type_map = _TYPE_NAME_TO_PROPERTY_CLASS
                for p in n.meta.get("outputs", []) or []:
                    cls = type_map[p["type"]]
                    end_outputs.append(cls(title=p.get("title")))
                node = EndNode(name=n.name, outputs=end_outputs or None)
            elif n.kind == "agent":
                agent_yaml = n.meta.get("agent_spec_yaml")
                if not agent_yaml:
                    if strict:
                        raise UnsupportedPatternError(
                            code="AGENT_YAML_MISSING",
                            message=f"Agent node '{n.name}' lacks agent_spec_yaml for reconstruction",
                            details=asdict(n),
                        )
                    agent_yaml = """
component_type: Agent
agentspec_version: "25.4.1"
name: inline_agent
llm_config:
  component_type: OpenAiConfig
  agentspec_version: "25.4.1"
  name: gpt-4o-mini
  model_id: gpt-4o-mini
system_prompt: ""
tools: []
                    """.strip()
                agent_comp = AgentSpecDeserializer().from_yaml(agent_yaml)
                node = AgentNode(name=n.name, agent=agent_comp)  # type: ignore[arg-type]
            elif n.kind == "llm":
                llm_yaml = n.meta.get("llm_yaml")
                prompt = n.meta.get("prompt_template", "")
                if not llm_yaml:
                    if strict:
                        raise UnsupportedPatternError(
                            code="LLM_YAML_MISSING",
                            message=f"LLM node '{n.name}' lacks llm_yaml for reconstruction",
                            details=asdict(n),
                        )
                    llm_yaml = """
component_type: OpenAiConfig
agentspec_version: "25.4.1"
name: gpt-4o-mini
model_id: gpt-4o-mini
                    """.strip()
                llm_cfg = AgentSpecDeserializer().from_yaml(llm_yaml)
                node = LlmNode(name=n.name, llm_config=llm_cfg, prompt_template=prompt)  # type: ignore[arg-type]
            elif n.kind == "tool":
                # Reconstruct ToolNode from meta.tool_def
                tool_def = n.meta.get("tool_def") or {}
                from pyagentspec.tools.clienttool import ClientTool
                from pyagentspec.tools.servertool import ServerTool

                type_map = _TYPE_NAME_TO_PROPERTY_CLASS
                inputs = []
                outputs = []
                for p in tool_def.get("inputs", []) or []:
                    cls = type_map.get(p.get("type"))
                    if cls:
                        inputs.append(cls(title=p.get("title")))
                for p in tool_def.get("outputs", []) or []:
                    cls = type_map.get(p.get("type"))
                    if cls:
                        outputs.append(cls(title=p.get("title")))
                tool: Any
                if tool_def.get("kind") == "client":
                    tool = ClientTool(
                        name=tool_def.get("name", n.name),
                        inputs=inputs or None,
                        outputs=outputs or None,
                    )
                else:
                    tool = ServerTool(
                        name=tool_def.get("name", n.name),
                        inputs=inputs or None,
                        outputs=outputs or None,
                    )
                node = ToolNode(name=n.name, tool=tool)
            elif n.kind == "message":
                msg = n.meta.get("message_template", "")
                node = OutputMessageNode(name=n.name, message=msg)
            elif n.kind == "branch":
                mapping = n.meta.get("mapping", {})
                input_key = n.meta.get("input_key")
                if input_key:
                    from pyagentspec.property import StringProperty  # local import

                    node = BranchingNode(
                        name=n.name, mapping=mapping, inputs=[StringProperty(title=input_key)]
                    )
                else:
                    node = BranchingNode(name=n.name, mapping=mapping)
            else:
                raise UnsupportedPatternError(
                    code="UNSUPPORTED_NODE_KIND",
                    message=f"Unsupported IR node kind: {n.kind}",
                    details=asdict(n),
                )
            id_to_node[n.id] = node

        control_edges: list[ControlFlowEdge] = []
        for ce in ir.edges_control:
            from_node = id_to_node[ce.from_id]
            to_node = id_to_node[ce.to_id]
            if isinstance(from_node, EndNode):
                continue
            control_edges.append(
                ControlFlowEdge(
                    name=f"{ce.from_id}_to_{ce.to_id}",
                    from_node=from_node,
                    to_node=to_node,
                    from_branch=ce.branch,
                )
            )

        data_edges: list[DataFlowEdge] = []
        for de in ir.edges_data:
            de_any = cast(Any, de)
            data_edges.append(
                DataFlowEdge(
                    name=f"{de_any.source_id}__{de_any.source_output}__to__{de_any.dest_id}__{de_any.dest_input}",
                    source_node=id_to_node[de_any.source_id],
                    source_output=de_any.source_output,
                    destination_node=id_to_node[de_any.dest_id],
                    destination_input=de_any.dest_input,
                )
            )

        flow = AgentSpecFlow(
            name=ir.name,
            start_node=id_to_node[ir.start_id],
            nodes=list(id_to_node.values()),
            control_flow_connections=control_edges,
            data_flow_connections=data_edges or None,
        )
        return flow

    # ----- Agent Spec -> IR -----
    def agentspec_to_ir(self, flow: AgentSpecFlow, *, strict: bool = True) -> IRFlow:
        serializer = AgentSpecSerializer()

        node_map: dict[str, IRNode] = {}
        for node in flow.nodes:
            if isinstance(node, StartNode):
                irn = IRNode(id=node.id, name=node.name, kind="start", meta={})
            elif isinstance(node, EndNode):
                irn = IRNode(id=node.id, name=node.name, kind="end", meta={})
            elif isinstance(node, AgentNode):
                agent_yaml = serializer.to_yaml(node.agent)
                irn = IRNode(
                    id=node.id, name=node.name, kind="agent", meta={"agent_spec_yaml": agent_yaml}
                )
            elif isinstance(node, LlmNode):
                llm_yaml = serializer.to_yaml(node.llm_config)
                prompt = node.prompt_template
                irn = IRNode(
                    id=node.id,
                    name=node.name,
                    kind="llm",
                    meta={"llm_yaml": llm_yaml, "prompt_template": prompt},
                )
            elif isinstance(node, BranchingNode):
                mapping = getattr(node, "mapping", {})
                input_key = None
                if getattr(node, "inputs", None):
                    first = node.inputs[0]  # type: ignore[index]
                    input_key = first.json_schema.get("title")
                if input_key is None:
                    raise ValueError(
                        "Unable to parse the agent spec branching Node, since no input key was found with which to branch."
                    )
                irn = IRNode(
                    id=node.id,
                    name=node.name,
                    kind="branch",
                    meta={"mapping": mapping, "input_key": input_key},
                )
            else:
                raise UnsupportedPatternError(
                    code="UNSUPPORTED_NODE",
                    message=f"Unsupported node type for IR conversion: {type(node).__name__}",
                    details={"node": node.model_dump(mode="python", exclude_none=True)},
                )
            node_map[node.id] = irn

        control_edges: list[IRControlEdge] = []
        for control_edge in flow.control_flow_connections:
            control_edges.append(
                IRControlEdge(
                    from_id=control_edge.from_node.id,
                    to_id=control_edge.to_node.id,
                    branch=getattr(control_edge, "from_branch", None),
                )
            )

        data_edges: list[IRDataEdge] = []
        for data_edge in flow.data_flow_connections or []:
            data_edges.append(
                IRDataEdge(
                    source_id=data_edge.source_node.id,
                    source_output=data_edge.source_output,
                    dest_id=data_edge.destination_node.id,
                    dest_input=data_edge.destination_input,
                )
            )

        start_id = flow.start_node.id
        ir = IRFlow(
            name=flow.name,
            start_id=start_id,
            nodes=list(node_map.values()),
            edges_control=control_edges,
            edges_data=data_edges,
        )
        return ir

    # ----- Codegen (IR -> Python) -----
    def codegen(self, ir: Any, module_name: str | None = None) -> Any:
        from .codegen import build_module  # local import to avoid cycles

        return build_module(ir, module_name=module_name)


# Register RulePack on import
register_rulepack(V0RulePack())

__all__ = ["V0RulePack"]
