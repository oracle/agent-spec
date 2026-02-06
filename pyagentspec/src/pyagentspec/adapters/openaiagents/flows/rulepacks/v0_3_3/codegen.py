# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from pyagentspec.adapters.openaiagents.flows._flow_ir import IRFlow, IRNode
from pyagentspec.adapters.openaiagents.flows.errors import UnsupportedPatternError


@dataclass
class _BuiltModule:
    code: str


def _snake_case(name: str) -> str:
    s = name.strip()
    # Replace non-word with underscores
    s = re.sub(r"[^0-9A-Za-z]+", "_", s)
    # Lowercase
    s = s.lower().strip("_")
    if not s:
        s = "agent"
    if s[0].isdigit():
        s = f"a_{s}"
    return s


def _collect(ir: IRFlow) -> tuple[dict[str, IRNode], dict[str, list[tuple[str, Optional[str]]]]]:
    nodes_by_id: dict[str, IRNode] = {n.id: n for n in ir.nodes}
    out_edges: dict[str, list[tuple[str, Optional[str]]]] = {}
    for e in ir.edges_control:
        out_edges.setdefault(e.from_id, []).append((e.to_id, e.branch))
    return nodes_by_id, out_edges


def _collect_all_agents(ir: IRFlow) -> list[IRNode]:
    nodes_by_id, out_edges = _collect(ir)
    visited: Set[str] = set()
    stack = [ir.start_id]
    agents: list[IRNode] = []
    while stack:
        nid = stack.pop()
        if nid in visited:
            continue
        visited.add(nid)
        n = nodes_by_id[nid]
        if n.kind == "agent":
            agents.append(n)
        for to_id, _branch in out_edges.get(nid, []):
            stack.append(to_id)
    return agents


def _next_successor(
    out_edges: dict[str, list[Tuple[str, Optional[str]]]], node_id: str
) -> Optional[str]:
    outs = out_edges.get(node_id, [])
    # Choose edge with label None or 'next'
    nexts = [to_id for (to_id, label) in outs if label in (None, "next")]
    if len(nexts) > 1:
        raise UnsupportedPatternError(
            code="MULTI_SUCCESSOR",
            message="Node has multiple 'next' successors",
            details={"node": node_id},
        )
    return nexts[0] if nexts else None


def _branch_out_map(
    out_edges: dict[str, list[Tuple[str, Optional[str]]]], node_id: str
) -> dict[str, str]:
    # Map branch label -> to_id (label may include 'default')
    m: dict[str, str] = {}
    for to_id, label in out_edges.get(node_id, []):
        m[(label or "next")] = to_id
    return m


def _determine_branch_source(
    ir: IRFlow, branch_node: IRNode, last_agent_id: Optional[str]
) -> Optional[str]:
    # Prefer explicit data edge source if available
    input_key = (branch_node.meta or {}).get("input_key")
    if input_key:
        for e in ir.edges_data:
            if e.dest_id == branch_node.id and e.dest_input == input_key and e.source_id:
                return e.source_id
    return last_agent_id


def _map_schema_type(t: str) -> str:
    return {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "array": "list",
    }.get(t, "str")


def _default_value_expr_for_type(t: str) -> str:
    # Return a Python literal string for a given schema type
    m = {
        "string": '""',
        "integer": "0",
        "number": "0.0",
        "boolean": "False",
        "array": "[]",
    }
    return m.get(t, "None")


def _edge_map_to_end(ir: IRFlow, end_node_id: str) -> dict[str, tuple[str, str]]:
    # Returns mapping: dest_input -> (source_id, source_output)
    m: dict[str, tuple[str, str]] = {}
    for e in ir.edges_data:
        if e.dest_id == end_node_id:
            key = e.dest_input
            if key in m:
                raise UnsupportedPatternError(
                    code="AMBIGUOUS_END_INPUT",
                    message="Multiple data edges feed the same End output",
                    details={"end": end_node_id, "input": key},
                )
            m[key] = (e.source_id, e.source_output)
    return m


def _expr_for_source(
    ir: IRFlow,
    source_id: str,
    source_output: str,
    agent_vars: dict[str, str],
    output_types: dict[str, Optional[str]],
) -> str:
    # Resolve a Python expression for a given data edge source
    nodes_by_id, _ = _collect(ir)
    src = nodes_by_id[source_id]
    if src.kind == "start":
        key = _py_str(_snake_case(source_output))
        return f"workflow[{key}]"
    if src.kind == "agent":
        var = agent_vars.get(source_id)
        if not var:
            raise UnsupportedPatternError(
                code="UNKNOWN_SOURCE_AGENT",
                message="Agent variable not found for data edge source",
                details={"node": source_id},
            )
        base = _snake_case(var)
        if output_types.get(source_id):
            field_key = _py_str(_snake_case(source_output))
            return f'{base}_result["output_parsed"].get({field_key})'
        else:
            # Only support output_text wiring for unstructured outputs
            if source_output not in {"output_text", "text", "result"}:
                raise UnsupportedPatternError(
                    code="UNSTRUCTURED_SOURCE_FIELD",
                    message="Cannot address field on unstructured agent output",
                    details={"field": source_output},
                )
            return f'{base}_result["output_text"]'
    # Branch and other kinds unsupported as sources for End values in this generator
    raise UnsupportedPatternError(
        code="UNSUPPORTED_END_SOURCE",
        message="Unsupported source node kind for End output mapping",
        details={"kind": src.kind, "node": src.id},
    )


def _emit_preamble(needs_function_tool: bool, *, needs_literal: bool = False) -> list[str]:
    lines: list[str] = []
    if needs_function_tool:
        lines.append(
            "from agents import function_tool, Agent, ModelSettings, TResponseInputItem, Runner, RunConfig, trace"
        )
    else:
        lines.append(
            "from agents import Agent, ModelSettings, TResponseInputItem, Runner, RunConfig, trace"
        )
    lines.append("from pydantic import BaseModel")
    if needs_literal:
        lines.append("from typing import Any, Literal")
    else:
        lines.append("from typing import Any")
    lines.append("")
    lines.append(
        "# Tool registry is filled at runtime by run_workflow(tools=...) and used by @function_tool stubs"
    )
    lines.append("_TOOL_REGISTRY: dict[str, Any] = {}")
    lines.append("")
    return lines


def _emit_workflow_input(start_node: IRNode) -> list[str]:
    # Build WorkflowInput from start_node.meta.inputs (list of {title, type})
    meta = start_node.meta or {}
    inputs = meta.get("inputs") or []
    lines: list[str] = []
    lines.append("class WorkflowInput(BaseModel):")
    if not inputs:
        lines.append("  input_as_text: str")
    else:
        for p in inputs:
            title = p.get("title") or "input_as_text"
            t = _map_schema_type(str(p.get("type", "string")))
            safe = _snake_case(title)
            lines.append(f"  {safe}: {t}")
    lines.append("")
    return lines


def _parse_agent_yaml(agent_yaml: str) -> dict[str, Any]:
    # Import locally to avoid heavy deps at module import
    try:
        from pyagentspec.serialization.deserializer import AgentSpecDeserializer
        from pyagentspec.serialization.serializer import AgentSpecSerializer
    except Exception as e:  # pragma: no cover - environment specific
        raise UnsupportedPatternError(
            code="DESERIALIZER_MISSING",
            message="AgentSpec deserializer not available",
            details={"error": str(e)},
        )
    comp = AgentSpecDeserializer().from_yaml(agent_yaml)
    # Use AgentSpecSerializer to produce a Python dict with proper serialization context
    data = AgentSpecSerializer().to_dict(comp)
    # Expect structure: {'name':..., 'system_prompt':..., 'llm_config': {'model_id':..., 'default_generation_parameters': {...}}, 'tools': [...]}
    return data


def _emit_agents(
    nodes: list[IRNode],
) -> tuple[list[str], list[tuple[str, str]], dict[str, Optional[str]], list[dict[str, Any]], bool]:
    lines: list[str] = []
    name_pairs: list[tuple[str, str]] = []  # (node_id -> var_name)
    output_type_by_id: dict[str, Optional[str]] = {}
    used_vars: set[str] = set()
    all_tools: list[dict[str, Any]] = []
    needs_literal_import = False
    for n in nodes:
        if n.kind != "agent":
            continue
        meta = n.meta or {}
        agent_yaml = meta.get("agent_spec_yaml")
        if not agent_yaml:
            raise UnsupportedPatternError(
                code="AGENT_YAML_MISSING", message=f"Agent node '{n.name}' missing agent_spec_yaml"
            )
        info = _parse_agent_yaml(agent_yaml)
        human_name = info.get("name") or n.name
        var = _snake_case(human_name)
        # Ensure unique variable names
        base = var
        i = 2
        while var in used_vars:
            var = f"{base}_{i}"
            i += 1
        used_vars.add(var)
        name_pairs.append((n.id, var))

        # Require explicit model_id; do not silently default in strict codegen
        model = (info.get("llm_config") or {}).get("model_id")
        if not model:
            raise UnsupportedPatternError(
                code="MODEL_ID_MISSING",
                message="Agent is missing llm_config.model_id; cannot default model in strict mode",
                details={"agent": human_name},
            )
        sys_prompt = info.get("system_prompt") or ""
        outputs = info.get("outputs") or []

        # Router agents often have outputs schema on the Agent component itself.
        # Preserve it by generating a Pydantic model and using it as output_type.
        output_model_name: Optional[str] = None
        if outputs:
            output_model_name = _derive_model_name(human_name)
            lines.append(f"class {output_model_name}(BaseModel):")
            for p in outputs:
                title = p.get("title") or "result"
                # Determine annotation: prefer enum -> Literal[...]
                p_type = str(p.get("type", "string"))
                js = p.get("json_schema") or {}
                enum_vals = js.get("enum") if isinstance(js, dict) else None
                if isinstance(enum_vals, list) and enum_vals:
                    # Build Literal annotation; quote strings, keep numbers/bools raw
                    literal_elems: list[str] = []
                    for v in enum_vals:
                        if isinstance(v, str):
                            literal_elems.append(repr(v))
                        else:
                            literal_elems.append(str(v))
                    ann = f"Literal[{', '.join(literal_elems)}]"
                    needs_literal_import = True
                else:
                    t = _map_schema_type(p_type)
                    ann = "list[str]" if t == "list" else t
                safe_field = _snake_case(title)
                lines.append(f"  {safe_field}: {ann}")
            lines.append("")
        output_type_by_id[n.id] = output_model_name
        gen = (info.get("llm_config") or {}).get("default_generation_parameters") or {}
        # Only keep supported keys
        supported = {k: v for k, v in gen.items() if k in {"temperature", "top_p", "max_tokens"}}

        # output_type_by_id set above

        # Collect tools on this agent (server tools only for now)
        agent_tools = info.get("tools") or []
        for td in agent_tools:
            # Expect component_type: ServerTool
            if not isinstance(td, dict):
                continue
            if td.get("component_type") != "ServerTool":
                continue
            all_tools.append(td)

        lines.append(f"{var} = Agent(")
        lines.append(f"  name={_py_str(human_name)},")
        lines.append(f"  instructions={_py_triple_str(sys_prompt)},")
        lines.append(f"  model={_py_str(model)},")
        if output_model_name:
            lines.append(f"  output_type={output_model_name},")
        if supported:
            lines.append("  model_settings=ModelSettings(")
            for k in ("temperature", "top_p", "max_tokens"):
                if k in supported and supported[k] is not None:
                    if k == "max_tokens":
                        try:
                            val = int(supported[k])
                        except Exception:
                            val = supported[k]
                        lines.append(f"    {k}={val},")
                    else:
                        lines.append(f"    {k}={supported[k]},")
            lines.append("")
            # Close ModelSettings call and ensure this argument is comma-terminated
            # so additional args (e.g., tools) can follow.
            lines.append("  ),")
        lines.append(")")
        # tools list for this agent
        if info.get("tools"):
            # Map tool names to emitted function names
            tool_vars: List[str] = []
            tools_list_any = info.get("tools") or []
            tools_list: List[Dict[str, Any]] = (
                tools_list_any if isinstance(tools_list_any, list) else []
            )
            for td in tools_list:
                if not isinstance(td, dict):
                    continue
                nm = td.get("name") or "tool"
                tool_vars.append(_tool_func_name(nm))
            if tool_vars:
                # Insert tools argument before model_settings if present
                insert_at = len(lines) - 1 if lines and lines[-1] == ")" else len(lines)
                # Rebuild agent call with tools if needed
                # Since we're appending, just insert before closing parenthesis
                # Add commas after each tool to form a valid Python list
                tools_block = (
                    [
                        "  tools=[",
                    ]
                    + [f"    {tv}," for tv in tool_vars]
                    + [
                        "  ],",
                    ]
                )
                lines[-1:-1] = (
                    tools_block  # insert before the last appended line (which is either model_settings closing or end)
                )

        lines.append("")
    return lines, name_pairs, output_type_by_id, all_tools, needs_literal_import


def _tool_func_name(display_name: str) -> str:
    return _snake_case(display_name)


def _tool_short_id(display_name: str) -> str:
    s = _snake_case(display_name)
    s = re.sub(r"^(calculate_)?", "", s)
    s = re.sub(r"(?:_function|_tool)$", "", s)
    return s


def _emit_tools(tools: list[dict[str, Any]]) -> tuple[list[str], bool]:
    # Deduplicate by name; emit @function_tool wrappers that delegate to a runtime registry
    seen: set[str] = set()
    lines: list[str] = []
    needs_function_tool = False
    for td in tools:
        name = td.get("name") or "tool"
        if name in seen:
            continue
        seen.add(name)
        fname = _tool_func_name(name)
        ins = td.get("inputs") or []
        outs = td.get("outputs") or []
        # Determine return annotation
        if len(outs) == 0:
            ret_ann = "None"
        elif len(outs) == 1:
            ret_ann = _map_schema_type(str(outs[0].get("type", "string")))
        else:
            raise UnsupportedPatternError(
                code="MULTI_OUTPUT_TOOL_UNSUPPORTED",
                message=f"Tool '{name}' has multiple outputs; cannot map to single return type",
            )
        # Build signature
        sig_parts = []
        for p in ins:
            title = _snake_case(p.get("title") or "arg")
            t = _map_schema_type(str(p.get("type", "string")))
            sig_parts.append(f"{title}: {t}")
        sig = ", ".join(sig_parts)
        lines.append("@function_tool")
        needs_function_tool = True
        lines.append(f"def {fname}({sig}) -> {ret_ann}:")
        ident = td.get("name") or name
        lines.append(f"  impl = _TOOL_REGISTRY.get({_py_str(ident)})")
        lines.append(f"  if impl is None:")
        lines.append(f"    raise RuntimeError('Required tool not provided: {name}')")
        call_args = ", ".join([_snake_case(p.get("title") or "arg") for p in ins])
        lines.append(f"  return impl({call_args})")
        lines.append("")
    return lines, needs_function_tool


def _py_str(s: str) -> str:
    return repr(s)


def _py_triple_str(s: str) -> str:
    if not s:
        return repr("")
    if "\n" not in s:
        return repr(s)
    # Use triple quotes for readability; escape triple quotes if present
    safe = s.replace('"""', '"""')
    return f'"""{safe}\n"""'


def _emit_run_workflow(
    ir: IRFlow,
    linear_nodes: list[IRNode],
    agent_vars: dict[str, str],
    output_types: dict[str, Optional[str]],
) -> list[str]:
    lines: list[str] = []
    lines.append("# Main code entrypoint")
    lines.append(
        "async def run_workflow(workflow_input: WorkflowInput, tools: dict | None = None):"
    )
    lines.append("  global _TOOL_REGISTRY")
    lines.append("  _TOOL_REGISTRY.clear()")
    lines.append("  if tools:")
    lines.append("    _TOOL_REGISTRY.update(tools)")
    lines.append(f"  with trace({_py_str(ir.name or 'New workflow')}):")
    lines.append("    state = {")
    lines.append("")
    lines.append("    }")
    lines.append("    workflow = workflow_input.model_dump()")
    # Conversation history bootstrap: pick first input field
    start = next((n for n in linear_nodes if n.kind == "start"), None)
    first_key = "input_as_text"
    if start and (start.meta or {}).get("inputs"):
        ins = (start.meta or {}).get("inputs") or []
        if ins:
            first_key = _snake_case(ins[0].get("title") or first_key)
    lines.append("    conversation_history: list[TResponseInputItem] = [")
    lines.append("      {")
    lines.append('        "role": "user",')
    lines.append('        "content": [')
    lines.append("          {")
    lines.append('            "type": "input_text",')
    lines.append(f'            "text": workflow[{_py_str(first_key)}]')
    lines.append("          }")
    lines.append("        ]")
    lines.append("      }")
    lines.append("    ]")

    # Emit sequential agent runs until End
    for n in linear_nodes:
        if n.kind != "agent":
            continue
        var = agent_vars[n.id]
        base = _snake_case(var)
        temp_name = f"{base}_result_temp"
        lines.append(f"    {temp_name} = await Runner.run(")
        lines.append(f"      {var},")
        lines.append("      input=[")
        lines.append("        *conversation_history")
        lines.append("      ],")
        lines.append("      run_config=RunConfig(trace_metadata={")
        lines.append('        "__trace_source__": "agent-builder",')
        lines.append('        "workflow_id": "wf_auto_generated"')
        lines.append("      })")
        lines.append("    )")
        lines.append("")
        lines.append(
            f"    conversation_history.extend([item.to_input_item() for item in {temp_name}.new_items])"
        )
        lines.append("")
        # Emit result materialization pattern
        if output_types.get(n.id):
            lines.append(f"    {base}_result = {{")
            lines.append(f'      "output_text": {temp_name}.final_output.model_dump_json(),')
            lines.append(f'      "output_parsed": {temp_name}.final_output.model_dump()')
            lines.append("    }")
        else:
            lines.append(f"    {base}_result = {{")
            lines.append(f'      "output_text": {temp_name}.final_output_as(str)')
            lines.append("    }")
    # Return last available result if any, else empty dict
    last_agent = next((n for n in reversed(linear_nodes) if n.kind == "agent"), None)
    if last_agent:
        last_var = _snake_case(agent_vars[last_agent.id])
        lines.append(f"    return {last_var}_result")
    else:
        lines.append("    return {}")
    return lines


def _emit_run_workflow_any(
    ir: IRFlow, agent_vars: dict[str, str], output_types: dict[str, Optional[str]]
) -> list[str]:
    nodes_by_id, out_edges = _collect(ir)

    # Header and common prologue
    lines: list[str] = []
    lines.append("# Main code entrypoint")
    lines.append(
        "async def run_workflow(workflow_input: WorkflowInput, tools: dict | None = None):"
    )
    lines.append("  global _TOOL_REGISTRY")
    lines.append("  _TOOL_REGISTRY.clear()")
    lines.append("  if tools:")
    lines.append("    _TOOL_REGISTRY.update(tools)")
    lines.append(f"  with trace({_py_str(ir.name or 'New workflow')}):")
    lines.append("    state = {")
    lines.append("")
    lines.append("    }")
    lines.append("    workflow = workflow_input.model_dump()")
    # Conversation history bootstrap
    start = next((n for n in ir.nodes if n.kind == "start"), None)
    first_key = "input_as_text"
    if start and (start.meta or {}).get("inputs"):
        ins = (start.meta or {}).get("inputs") or []
        if ins:
            first_key = _snake_case(ins[0].get("title") or first_key)
    lines.append("    conversation_history: list[TResponseInputItem] = [")
    lines.append("      {")
    lines.append('        "role": "user",')
    lines.append('        "content": [')
    lines.append("          {")
    lines.append('            "type": "input_text",')
    lines.append(f'            "text": workflow[{_py_str(first_key)}]')
    lines.append("          }")
    lines.append("        ]")
    lines.append("      }")
    lines.append("    ]")

    # Emit body via recursive walk from start
    lines.extend(
        _emit_from_node(
            ir,
            ir.start_id,
            agent_vars,
            output_types,
            visiting=set(),
            last_agent_id=None,
            indent="    ",
        )
    )
    return lines


def _emit_from_node(
    ir: IRFlow,
    node_id: str,
    agent_vars: dict[str, str],
    output_types: dict[str, Optional[str]],
    visiting: Set[str],
    last_agent_id: Optional[str],
    indent: str,
) -> list[str]:
    nodes_by_id, out_edges = _collect(ir)
    node = nodes_by_id[node_id]
    lines: list[str] = []
    # Prevent infinite loops (track nodes on the current path)
    if node_id in visiting:
        raise UnsupportedPatternError(
            code="CFG_CYCLE",
            message="Cycle detected during code emission",
            details={"node": node_id},
        )
    visiting.add(node_id)

    if node.kind == "agent":
        var = agent_vars.get(node.id)
        if not var:
            return lines
        base = _snake_case(var)
        temp_name = f"{base}_result_temp"
        lines.append(f"{indent}{temp_name} = await Runner.run(")
        lines.append(f"{indent}  {var},")
        lines.append(f"{indent}  input=[")
        lines.append(f"{indent}    *conversation_history")
        lines.append(f"{indent}  ],")
        lines.append(f"{indent}  run_config=RunConfig(trace_metadata={{")
        lines.append(f'{indent}    "__trace_source__": "agent-builder",')
        lines.append(f'{indent}    "workflow_id": "wf_auto_generated"')
        lines.append(f"{indent}  }})")
        lines.append(f"{indent})")
        lines.append("")
        lines.append(
            f"{indent}conversation_history.extend([item.to_input_item() for item in {temp_name}.new_items])"
        )
        lines.append("")
        if output_types.get(node.id):
            lines.append(f"{indent}{base}_result = {{")
            lines.append(f'{indent}  "output_text": {temp_name}.final_output.model_dump_json(),')
            lines.append(f'{indent}  "output_parsed": {temp_name}.final_output.model_dump()')
            lines.append(f"{indent}}}")
        else:
            lines.append(f"{indent}{base}_result = {{")
            lines.append(f'{indent}  "output_text": {temp_name}.final_output_as(str)')
            lines.append(f"{indent}}}")
        # Continue along 'next'/None edge
        nxt = _next_successor(out_edges, node_id)
        if nxt:
            lines.extend(
                _emit_from_node(
                    ir,
                    nxt,
                    agent_vars,
                    output_types,
                    visiting,
                    last_agent_id=node.id,
                    indent=indent,
                )
            )
        else:
            # No successor: implicit return of last result
            lines.append(f"{indent}return {base}_result")
        visiting.remove(node_id)
        return lines

    if node.kind == "branch":
        # Determine branch expression
        input_key = (node.meta or {}).get("input_key")
        if not input_key:
            raise UnsupportedPatternError(
                code="BRANCH_INPUT_KEY_MISSING",
                message="Branch node missing input_key in IR; parser should supply it in strict mode",
            )
        # Determine best source node for branch value
        source_id = _determine_branch_source(ir, node, last_agent_id)
        if source_id and source_id in agent_vars:
            src_var = _snake_case(agent_vars[source_id])
            if output_types.get(source_id):
                # Use exact key from IR (parser must ensure it's present)
                key_expr = _py_str(input_key)
                branch_expr = f'{src_var}_result["output_parsed"][{key_expr}]'
            else:
                branch_expr = f'{src_var}_result["output_text"]'
        else:
            branch_expr = f"workflow[{_py_str(_snake_case(input_key))}]"
        # Build label->to_id map and generate ladder
        out_map = _branch_out_map(out_edges, node_id)
        mapping = (node.meta or {}).get("mapping") or {}
        # Emit if/elif for each literal in stable order
        sorted_lits = sorted(mapping.keys())
        first = True
        for lit in sorted_lits:
            to_id = out_map.get(mapping[lit])
            kw = "if" if first else "elif"
            first = False
            lines.append(f"{indent}{kw} {branch_expr} == {_py_str(lit)}:")
            if to_id:
                lines.extend(
                    _emit_from_node(
                        ir,
                        to_id,
                        agent_vars,
                        output_types,
                        visiting,
                        last_agent_id=last_agent_id,
                        indent=indent + "  ",
                    )
                )
            else:
                lines.append(f"{indent}  return {{}}")
        # Default arm
        default_to = out_map.get("default") or out_map.get("next")
        lines.append(f"{indent}else:")
        if default_to:
            lines.extend(
                _emit_from_node(
                    ir,
                    default_to,
                    agent_vars,
                    output_types,
                    visiting,
                    last_agent_id=last_agent_id,
                    indent=indent + "  ",
                )
            )
        else:
            lines.append(f"{indent}  return {{}}")
        visiting.remove(node_id)
        return lines

    if node.kind == "end":
        # Materialize EndNode outputs from explicit data edges, if any
        outs = (node.meta or {}).get("outputs") or []
        edge_map = _edge_map_to_end(ir, node.id)
        if outs:
            lines.append(f"{indent}end_result = {{")
            for p in outs:
                title = p.get("title") or "result"
                t = str(p.get("type", "string"))
                key = _py_str(title)
                if title in edge_map:
                    src_id, src_out = edge_map[title]
                    value = _expr_for_source(ir, src_id, src_out, agent_vars, output_types)
                else:
                    # Fallback to workflow input title or type default
                    wf_key = _py_str(_snake_case(title))
                    value = f"workflow.get({wf_key}, {_default_value_expr_for_type(t)})"
                lines.append(f"{indent}  {key}: {value},")
            lines.append(f"{indent}}}")
            lines.append(f"{indent}return end_result")
        else:
            # No explicit schema; if there are data edges to End, synthesize dict from them
            if edge_map:
                lines.append(f"{indent}end_result = {{")
                for dest_input, (src_id, src_out) in edge_map.items():
                    key = _py_str(dest_input)
                    value = _expr_for_source(ir, src_id, src_out, agent_vars, output_types)
                    lines.append(f"{indent}  {key}: {value},")
                lines.append(f"{indent}}}")
                lines.append(f"{indent}return end_result")
            else:
                # Fall back to last agent result if available, else empty dict
                if last_agent_id and last_agent_id in agent_vars:
                    last_var = _snake_case(agent_vars[last_agent_id])
                    lines.append(f"{indent}return {last_var}_result")
                else:
                    lines.append(f"{indent}return {{}}")
        return lines

    # Skip unsupported nodes silently but keep traversal going if possible
    nxt = _next_successor(out_edges, node_id)
    if nxt:
        lines.extend(
            _emit_from_node(
                ir,
                nxt,
                agent_vars,
                output_types,
                visiting,
                last_agent_id=last_agent_id,
                indent=indent,
            )
        )
    visiting.remove(node_id)
    return lines


def _emit_run_workflow_with_branch(
    ir: IRFlow,
    pre_chain: list[IRNode],
    branch_node: IRNode,
    branch_map: dict[str, Optional[IRNode]],
    default_target: Optional[IRNode],
    agent_vars: dict[str, str],
    output_types: dict[str, Optional[str]],
) -> list[str]:
    # Emit pre-branch identical to linear
    lines: list[str] = []
    lines.append("# Main code entrypoint")
    lines.append(
        "async def run_workflow(workflow_input: WorkflowInput, tools: dict | None = None):"
    )
    lines.append("  global _TOOL_REGISTRY")
    lines.append("  _TOOL_REGISTRY.clear()")
    lines.append("  if tools:")
    lines.append("    _TOOL_REGISTRY.update(tools)")
    lines.append(f"  with trace({_py_str(ir.name or 'New workflow')}):")
    lines.append("    state = {")
    lines.append("")
    lines.append("    }")
    lines.append("    workflow = workflow_input.model_dump()")
    first_key = "input_as_text"
    start = next((n for n in pre_chain if n.kind == "start"), None)
    if start and (start.meta or {}).get("inputs"):
        ins = (start.meta or {}).get("inputs") or []
        if ins:
            first_key = _snake_case(ins[0].get("title") or first_key)
    lines.append("    conversation_history: list[TResponseInputItem] = [")
    lines.append("      {")
    lines.append('        "role": "user",')
    lines.append('        "content": [')
    lines.append("          {")
    lines.append('            "type": "input_text",')
    lines.append(f'            "text": workflow[{_py_str(first_key)}]')
    lines.append("          }")
    lines.append("        ]")
    lines.append("      }")
    lines.append("    ]")

    # Pre-branch agent runs
    for n in pre_chain:
        if n.kind != "agent":
            continue
        var = agent_vars[n.id]
        base = _snake_case(var)
        temp_name = f"{base}_result_temp"
        lines.append(f"    {temp_name} = await Runner.run(")
        lines.append(f"      {var},")
        lines.append("      input=[")
        lines.append("        *conversation_history")
        lines.append("      ],")
        lines.append("      run_config=RunConfig(trace_metadata={")
        lines.append('        "__trace_source__": "agent-builder",')
        lines.append('        "workflow_id": "wf_auto_generated"')
        lines.append("      })")
        lines.append("    )")
        lines.append("")
        lines.append(
            f"    conversation_history.extend([item.to_input_item() for item in {temp_name}.new_items])"
        )
        lines.append("")
        if output_types.get(n.id):
            lines.append(f"    {base}_result = {{")
            lines.append(f'      "output_text": {temp_name}.final_output.model_dump_json(),')
            lines.append(f'      "output_parsed": {temp_name}.final_output.model_dump()')
            lines.append("    }")
        else:
            lines.append(f"    {base}_result = {{")
            lines.append(f'      "output_text": {temp_name}.final_output_as(str)')
            lines.append("    }")

    # Emit if/elif ladder using branch mapping
    # We expect branch_map keys are literals and values point to first node in branch (agent or None)
    # Pick an iteration order that is stable: sorted keys
    sorted_lits = sorted(branch_map.keys())
    # Enforce explicit branch input key; avoid silent default
    input_key = (branch_node.meta or {}).get("input_key")
    if not input_key:
        raise UnsupportedPatternError(
            code="BRANCH_INPUT_KEY_MISSING",
            message="Branch node missing input_key in IR; parser should supply it in strict mode",
            details={"node": branch_node.id},
        )
    # Build an expression to read the branch value
    branch_expr = f"{_snake_case(input_key)}"
    # In examples, the value driving branching is usually from previous parsed result; here we assume `*_result[\"output_parsed\"][input_key]`
    # Find last pre-branch agent variable to read from
    last_agent = next((n for n in reversed(pre_chain) if n.kind == "agent"), None)
    if last_agent:
        la = _snake_case(agent_vars[last_agent.id])
        branch_expr = (
            f'{la}_result["output_parsed"][{_py_str(_snake_case(input_key))}]'
            if output_types.get(last_agent.id)
            else f'{la}_result["output_text"]'
        )
    first: bool = True
    for lit in sorted_lits:
        target = branch_map[lit]
        kw = "if" if first else "elif"
        first = False
        lines.append(f"    {kw} {branch_expr} == {_py_str(lit)}:")
        if target and target.kind == "agent":
            vname = agent_vars.get(target.id)
            if vname:
                base = _snake_case(vname)
                temp_name = f"{base}_result_temp"
                lines.append(f"      {temp_name} = await Runner.run(")
                lines.append(f"        {vname},")
                lines.append("        input=[")
                lines.append("          *conversation_history")
                lines.append("        ],")
                lines.append("        run_config=RunConfig(trace_metadata={")
                lines.append('          "__trace_source__": "agent-builder",')
                lines.append('          "workflow_id": "wf_auto_generated"')
                lines.append("        })")
                lines.append("      )")
                lines.append("")
                lines.append(
                    f"      conversation_history.extend([item.to_input_item() for item in {temp_name}.new_items])"
                )
                lines.append("")
                if output_types.get(target.id):
                    lines.append(f"      {base}_result = {{")
                    lines.append(
                        f'        "output_text": {temp_name}.final_output.model_dump_json(),'
                    )
                    lines.append(f'        "output_parsed": {temp_name}.final_output.model_dump()')
                    lines.append("      }")
                else:
                    lines.append(f"      {base}_result = {{")
                    lines.append(f'        "output_text": {temp_name}.final_output_as(str)')
                    lines.append("      }")
                lines.append(f"      return {base}_result")
        else:
            lines.append("      return {}")
    # Else/default
    if default_target:
        vname2: Optional[str] = (
            agent_vars.get(default_target.id) if default_target.kind == "agent" else None
        )
        lines.append("    else:")
        if vname2:
            base = _snake_case(vname2)
            temp_name = f"{base}_result_temp"
            lines.append(f"      {temp_name} = await Runner.run(")
            lines.append(f"        {vname2},")
            lines.append("        input=[")
            lines.append("          *conversation_history")
            lines.append("        ],")
            lines.append("        run_config=RunConfig(trace_metadata={")
            lines.append('          "__trace_source__": "agent-builder",')
            lines.append('          "workflow_id": "wf_auto_generated"')
            lines.append("        })")
            lines.append("      )")
            lines.append("")
            lines.append(
                f"      conversation_history.extend([item.to_input_item() for item in {temp_name}.new_items])"
            )
            lines.append("")
            if output_types.get(default_target.id):
                lines.append(f"      {base}_result = {{")
                lines.append(f'        "output_text": {temp_name}.final_output.model_dump_json(),')
                lines.append(f'        "output_parsed": {temp_name}.final_output.model_dump()')
                lines.append("      }")
            else:
                lines.append(f"      {base}_result = {{")
                lines.append(f'        "output_text": {temp_name}.final_output_as(str)')
                lines.append("      }")
            lines.append(f"      return {base}_result")
        else:
            lines.append("      return {}")
    else:
        # No explicit default; return the pre-branch last result
        if last_agent:
            la = _snake_case(agent_vars[last_agent.id])
            lines.append("    else:")
            lines.append(f"      return {la}_result")
    return lines


def _derive_model_name(agent_name: str) -> str:
    # Create a PascalCase schema name like '<AgentName>Schema'
    base = re.sub(r"[^0-9A-Za-z]+", " ", agent_name).strip()
    parts = [p.capitalize() for p in base.split()] or ["Agent"]
    name = "".join(parts) + "Schema"
    # Ensure valid identifier
    if name[0].isdigit():
        name = "A" + name
    return name


def build_module(ir: IRFlow, module_name: str | None = None) -> _BuiltModule:
    # Normalize and validate minimal supported shape
    # Legacy call removed; traversal now handled in _emit_run_workflow_any

    # Collect all agents reachable in the graph (any combination of agents and branch nodes)
    agent_nodes: list[IRNode] = _collect_all_agents(ir)
    agents_src, name_pairs, output_types, all_tools, needs_literal_import = _emit_agents(
        agent_nodes
    )

    # Tools first so agent definitions can reference them
    tool_src, needs_function_tool = _emit_tools(all_tools) if all_tools else ([], False)

    # Preamble and inputs
    code_lines: list[str] = []
    code_lines.extend(
        _emit_preamble(needs_function_tool=needs_function_tool, needs_literal=needs_literal_import)
    )
    if tool_src:
        code_lines.extend(tool_src)

    code_lines.extend(agents_src)

    # WorkflowInput after agents (examples vary; order not critical)
    start_node = next((n for n in ir.nodes if n.kind == "start"), None)
    if not start_node:
        raise UnsupportedPatternError(
            code="MISSING_START", message="Flow must contain a Start node"
        )
    code_lines.extend(_emit_workflow_input(start_node))

    # Entrypoint
    agent_vars = {nid: v for nid, v in name_pairs}
    # Emit run_workflow by traversing from Start handling branches recursively
    code_lines.extend(_emit_run_workflow_any(ir, agent_vars, output_types))

    code = "\n".join(code_lines) + "\n"
    return _BuiltModule(code=code)


__all__ = ["build_module"]
