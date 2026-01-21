# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import libcst as cst

from pyagentspec.adapters.openaiagents.flows._flow_ir import (
    IRControlEdge,
    IRDataEdge,
    IRFlow,
    IRNode,
)
from pyagentspec.adapters.openaiagents.flows.errors import (
    FlowConversionError,
    UnsupportedPatternError,
)


@dataclass
class _AgentDef:
    var_name: str
    display_name: str
    model_id: Optional[str]
    instructions: Optional[str]
    gen: Optional[Dict[str, Any]]
    tools: List[str]
    output_model: Optional[str] = None


class _ModuleScan(cst.CSTVisitor):
    """Shallow scan of module-level agent definitions and function tools.

    We only extract what we need to produce usable Agent YAML stubs.
    """

    def __init__(self, *, strict: bool) -> None:
        self.agents: dict[str, _AgentDef] = {}
        self.function_tools: dict[str, Dict[str, Any]] = {}
        self.workflow_input: Optional[Dict[str, str]] = None  # title->type
        # class name -> {field: json-schema-like dict}
        # Each field maps to a minimal JSON schema, e.g. {"type":"string"} or {"type":"string","enum":[...]}
        self.pyd_models: Dict[str, Dict[str, Any]] = {}
        self.strict = strict

    def visit_FunctionDef(
        self, node: cst.FunctionDef
    ) -> Optional[bool]:  # pragma: no cover - simple collection
        # Collect function tools decorated with @function_tool
        for dec in node.decorators:
            name = _attr_or_name(dec.decorator)
            if name == "function_tool":
                # Gather signature annotations for inputs and return
                tdef: Dict[str, Any] = {"name": node.name.value, "inputs": [], "outputs": []}
                if node.params:
                    for p in node.params.params:
                        if isinstance(p.name, cst.Name):
                            tdef["inputs"].append(
                                {
                                    "title": p.name.value,
                                    "type": _annotation_to_type_str(p.annotation),
                                }
                            )
                # Return annotation
                if node.returns:
                    rett = _annotation_to_type_str(node.returns)
                    if rett:
                        tdef["outputs"].append({"title": "result", "type": rett})
                if not tdef["outputs"]:
                    if self.strict:
                        raise UnsupportedPatternError(
                            code="TOOL_RETURN_SCHEMA_MISSING",
                            message="@function_tool must declare an encodable return annotation or documented schema",
                            details={"tool": node.name.value},
                        )
                    # Default to a single string result in non-strict mode
                    tdef["outputs"].append({"title": "result", "type": "string"})
                self.function_tools[node.name.value] = tdef
        return None

    def visit_ClassDef(
        self, node: cst.ClassDef
    ) -> Optional[bool]:  # pragma: no cover - simple collection
        # Capture Pydantic BaseModel classes
        # LibCST represents bases as Args; detect "BaseModel" in Arg.value
        def _is_basemodel(arg: cst.Arg) -> bool:
            v = arg.value
            if isinstance(v, cst.Name):
                return v.value == "BaseModel"
            if isinstance(v, cst.Attribute):
                # e.g., pydantic.BaseModel
                return isinstance(v.attr, cst.Name) and v.attr.value == "BaseModel"
            return False

        is_pyd = any(_is_basemodel(b) for b in (node.bases or ()))
        if is_pyd:
            fields: Dict[str, Dict[str, Any]] = {}
            for stmt in node.body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    for small in stmt.body:
                        if isinstance(small, cst.AnnAssign) and isinstance(small.target, cst.Name):
                            title = small.target.value
                            schema = _annotation_to_schema(small.annotation)
                            if schema:
                                fields[title] = schema
            if fields:
                cname = node.name.value
                self.pyd_models[cname] = fields
                if cname == "WorkflowInput":
                    self.workflow_input = {
                        k: str(v.get("type", "string")) for k, v in fields.items()
                    }
        return None

    def visit_SimpleStatementLine(
        self, node: cst.SimpleStatementLine
    ) -> Optional[bool]:  # pragma: no cover - simple collection
        # Detect assignments like: foo = Agent(...)
        for stmt in node.body:
            if isinstance(stmt, cst.Assign) and isinstance(stmt.value, cst.Call):
                call = stmt.value
                func_name = _attr_or_name(call.func)
                if func_name == "Agent" and len(stmt.targets) == 1:
                    target = stmt.targets[0].target
                    if isinstance(target, cst.Name):
                        var_name = target.value
                        display_name, model_id, instructions, gen, tools, output_type = (
                            _extract_agent_args(call, strict=self.strict)
                        )
                        self.agents[var_name] = _AgentDef(
                            var_name=var_name,
                            display_name=display_name or var_name,
                            model_id=model_id,
                            instructions=instructions,
                            gen=gen,
                            tools=tools or [],
                            output_model=output_type,
                        )
        return None


class _RunWorkflowScan(cst.CSTVisitor):
    """Scan the run_workflow function body for Runner.run calls and branching ladders."""

    def __init__(self) -> None:
        self.runner_calls_pre_branch: list[str] = []  # agent var names before first branch
        self.first_if: Optional[cst.If] = None
        self.branch_agent_by_literal: dict[str, Optional[str]] = {}
        self.has_else: bool = False

        self._in_run_workflow = False
        self._seen_first_branch = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        if node.name.value == "run_workflow":
            self._in_run_workflow = True
        return None

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:
        if node.name.value == "run_workflow":
            self._in_run_workflow = False

    def visit_Await(
        self, node: cst.Await
    ) -> Optional[bool]:  # pragma: no cover - simple collection
        if not self._in_run_workflow or self._seen_first_branch:
            return None
        call = node.expression
        if isinstance(call, cst.Call):
            func_name = _attr_or_name(call.func)
            if func_name == "Runner.run":
                agent_name = _first_arg_name(call)
                if agent_name:
                    self.runner_calls_pre_branch.append(agent_name)
        return None

    def visit_If(self, node: cst.If) -> Optional[bool]:  # pragma: no cover - simple collection
        if not self._in_run_workflow:
            return None
        if not self._seen_first_branch:
            self._seen_first_branch = True
            self.first_if = node
            # Extract mapping from this if/elif ladder
            cur: Optional[cst.If] = node
            while cur is not None:
                lit = _eq_rhs_string_literal(cur.test)
                if lit is not None:
                    # For this branch body, try to find first Runner.run call agent
                    agent_in_branch = _find_first_runner_run_in_body(cur.body)
                    self.branch_agent_by_literal[lit] = agent_in_branch
                # Advance to elif/else
                if cur.orelse and isinstance(cur.orelse, cst.If):
                    cur = cur.orelse
                else:
                    # else: block exists when orelse is an Else
                    if cur.orelse and isinstance(cur.orelse, cst.Else):
                        self.has_else = True
                    cur = None
        return None


def _attr_or_name(node: cst.CSTNode) -> str | None:
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        left = _attr_or_name(node.value)
        if left:
            return f"{left}.{node.attr.value}"
    return None


def _extract_agent_args(
    call: cst.Call, *, strict: bool = True
) -> tuple[
    Optional[str], Optional[str], Optional[str], Optional[Dict[str, Any]], list[str], Optional[str]
]:
    display_name: Optional[str] = None
    model_id: Optional[str] = None
    instructions: Optional[str] = None
    gen: Optional[Dict[str, Any]] = None
    tools: list[str] = []
    output_type: Optional[str] = None
    for arg in call.args:
        if not isinstance(arg.keyword, cst.Name):
            continue
        k = arg.keyword.value
        if k == "name":
            display_name = _const_str(arg.value)
        elif k == "model":
            model_id = _const_str(arg.value)
        elif k == "instructions":
            instructions = _const_str(arg.value)
        elif k == "model_settings":
            # Extract supported generation params; fail on unsupported (depends on strict)
            gen = _extract_model_settings(arg.value, strict=strict)
        elif k == "tools":
            tools = _extract_tools_list(arg.value)
        elif k == "output_type":
            if isinstance(arg.value, cst.Name):
                output_type = arg.value.value
    return display_name, model_id, instructions, gen, tools, output_type


def _const_str(node: cst.CSTNode) -> Optional[str]:
    # Support multiple literal forms:
    # - SimpleString: '...', "...", """..."""
    # - ConcatenatedString: implicit adjacent literal concatenation inside parentheses
    # - BinaryOperation with + between constant strings
    # - f-strings with no interpolations (treated as constant)
    # - ParenthesizedExpression wrapper
    if isinstance(node, cst.SimpleString):
        try:
            return ast.literal_eval(node.value)  # type: ignore
        except Exception:  # pragma: no cover - defensive
            return node.value
    # Parentheses wrapper: ( ... )
    if hasattr(cst, "ParenthesizedExpression") and isinstance(node, cst.ParenthesizedExpression):
        return _const_str(node.expression)
    # Implicit concatenation like ("a" "b" "c")
    if hasattr(cst, "ConcatenatedString") and isinstance(node, cst.ConcatenatedString):
        left = _const_str(node.left)
        right = _const_str(node.right)
        if left is not None and right is not None:
            return left + right
        return None
    # Explicit concatenation "a" + "b"
    if isinstance(node, cst.BinaryOperation) and isinstance(node.operator, cst.Add):
        l = _const_str(node.left)
        r = _const_str(node.right)
        if l is not None and r is not None:
            return l + r
        return None
    # f-strings without any expressions (pure text)
    if isinstance(node, cst.FormattedString):
        parts = []
        for p in node.parts:
            if isinstance(p, cst.FormattedStringText):
                parts.append(p.value)
            else:
                return None
        return "".join(parts)
    return None


def _annotation_to_type_str(ann: Optional[cst.Annotation]) -> Optional[str]:
    if not ann:
        return None
    t = ann.annotation
    if isinstance(t, cst.Name):
        m = t.value
        return _map_py_type_to_schema(m)
    if (
        isinstance(t, cst.Subscript)
        and isinstance(t.value, cst.Name)
        and t.value.value in {"list", "List"}
    ):
        # represent lists generically as array of strings (conservative) or as array without item type; we choose string for MVP
        return "array"
    return None


def _map_py_type_to_schema(name: str) -> Optional[str]:
    return {
        "str": "string",
        "bool": "boolean",
        "int": "integer",
        "float": "number",
        "number": "number",
        "integer": "integer",
        "string": "string",
    }.get(name)


def _annotation_to_schema(ann: Optional[cst.Annotation]) -> Optional[Dict[str, Any]]:
    """Return a minimal JSON-schema-like mapping for an annotation.

    Handles:
    - Builtins: str, int, bool, float
    - list[...] generically as type: array
    - Literal[...]: type based on literal kinds and enum with concrete values
    """
    if not ann:
        return None
    t = ann.annotation
    # Builtin names
    if isinstance(t, cst.Name):
        m = _map_py_type_to_schema(t.value)
        return {"type": m} if m else None
    # list[...] – coerce to array
    if (
        isinstance(t, cst.Subscript)
        and isinstance(t.value, cst.Name)
        and t.value.value in {"list", "List"}
    ):
        return {"type": "array"}
    # Literal[...]
    if (
        isinstance(t, cst.Subscript)
        and isinstance(t.value, cst.Name)
        and t.value.value in {"Literal", "typing.Literal"}
    ):
        # Extract allowed values
        enum_vals: list[Any] = []
        # LibCST represents slices differently across versions; handle common forms
        slices = []
        if hasattr(t, "slice"):
            sl = t.slice
            # .slice may be a sequence (tuple/list) of SubscriptElement or a single BaseSlice
            if isinstance(sl, (list, tuple)):
                slices = list(sl)
            else:
                slices = [sl] if sl is not None else []
        for el in slices:
            base_slice = None
            # Normalize to a BaseSlice
            if hasattr(cst, "SubscriptElement") and isinstance(el, cst.SubscriptElement):
                base_slice = el.slice
            else:
                base_slice = getattr(el, "slice", el)
            # Extract the value node from Index if present
            val_node = getattr(base_slice, "value", base_slice)
            if isinstance(val_node, cst.SimpleString):
                try:
                    enum_vals.append(ast.literal_eval(val_node.value))
                except Exception:
                    enum_vals.append(val_node.value.strip("\"'"))
            elif isinstance(val_node, (cst.Integer, cst.Float)):
                try:
                    enum_vals.append(ast.literal_eval(val_node.value))
                except Exception:
                    enum_vals.append(val_node.value)
            elif isinstance(val_node, cst.Name) and val_node.value in {"True", "False"}:
                enum_vals.append(True if val_node.value == "True" else False)
        # Determine the base json schema type from enum values
        base_type = "string"
        if enum_vals and all(isinstance(v, bool) for v in enum_vals):
            base_type = "boolean"
        elif enum_vals and all(isinstance(v, int) and not isinstance(v, bool) for v in enum_vals):
            base_type = "integer"
        elif enum_vals and all(
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in enum_vals
        ):
            base_type = "number"
        return {"type": base_type, "enum": enum_vals} if enum_vals else {"type": base_type}
    return None


def _extract_model_settings(node: cst.CSTNode, *, strict: bool = True) -> Dict[str, Any]:
    # Expect ModelSettings(temperature=..., top_p=..., max_tokens=..., possibly other unsupported fields)
    if not isinstance(node, cst.Call):
        return {}
    name = _attr_or_name(node.func)
    if name != "ModelSettings":
        return {}
    params: Dict[str, Any] = {}
    unsupported: Dict[str, Any] = {}
    for a in node.args:
        k = a.keyword.value if isinstance(a.keyword, cst.Name) else None
        if not k:
            continue
        v = None
        if isinstance(a.value, (cst.Integer, cst.Float)):
            v = float(a.value.value) if isinstance(a.value, cst.Float) else int(a.value.value)
        elif isinstance(a.value, cst.Name) and a.value.value in {"True", "False"}:
            v = a.value.value == "True"
        # Supported
        if k in {"temperature", "top_p", "max_tokens"}:
            params[k] = v
        else:
            unsupported[k] = v
    if unsupported and strict:
        # Fail fast per mapping rules
        raise UnsupportedPatternError(
            code="UNSUPPORTED_MODEL_SETTINGS",
            message="Unsupported model_settings keys present",
            details={"keys": sorted(unsupported)},
        )
    return params


def _extract_tools_list(node: cst.CSTNode) -> list[str]:
    names: list[str] = []
    if isinstance(node, cst.List):
        for el in node.elements:
            v = el.value
            if isinstance(v, cst.Name):
                names.append(v.value)
    return names


def _first_arg_name(call: cst.Call) -> Optional[str]:
    if call.args:
        first = call.args[0]
        if isinstance(first.value, cst.Name):
            return first.value.value
    return None


def _eq_rhs_string_literal(test: cst.BaseExpression) -> Optional[str]:
    # Match: <expr> == <literal> with string/boolean/number
    if isinstance(test, cst.Comparison) and len(test.comparisons) == 1:
        comp = test.comparisons[0]
        if isinstance(comp.operator, cst.Equal):
            rhs = comp.comparator
            # String literal
            s = _const_str(rhs)
            if s is not None:
                return s
            # Boolean name True/False
            if isinstance(rhs, cst.Name) and rhs.value in {"True", "False"}:
                return rhs.value.lower()
            # Numeric literals
            if isinstance(rhs, (cst.Integer, cst.Float)):
                return rhs.value
    return None


def _find_first_runner_run_in_body(body: cst.BaseSuite) -> Optional[str]:
    # Walk the block and return first agent var used in await Runner.run(...)
    class _Find(cst.CSTVisitor):
        def __init__(self) -> None:
            self.agent_name: Optional[str] = None

        def visit_Await(
            self, node: cst.Await
        ) -> Optional[bool]:  # pragma: no cover - simple collection
            call = node.expression
            if isinstance(call, cst.Call):
                func_name = _attr_or_name(call.func)
                if func_name == "Runner.run":
                    self.agent_name = _first_arg_name(call)
            return None

    finder = _Find()
    body.visit(finder)
    return finder.agent_name


def _yaml_quote_block(s: str | None) -> str:
    if not s:
        return '""'
    # Use block literal style for readability; indent by two spaces
    lines = s.splitlines()
    if len(lines) <= 1:
        # single line; quote safely
        return _yaml_quote_scalar(s)
    indented = "\n".join(["  " + ln for ln in lines])
    return f"|\n{indented}"


def _yaml_quote_scalar(s: str) -> str:
    # Use double quotes and escape embedded quotes
    return '"' + s.replace('"', '\\"') + '"'


def _build_agent_yaml(
    name: str,
    model_id: Optional[str],
    instructions: Optional[str],
    gen: Optional[dict],  # type: ignore
    *,
    tool_defs_by_name: Optional[Dict[str, Dict[str, Any]]] = None,
    tool_names: Optional[List[str]] = None,
    outputs_schema: Optional[Dict[str, Any]] = None,
    allow_unknown_tools: bool = False,
) -> str:
    # Minimal Agent YAML sufficient for AgentSpecDeserializer
    model = model_id or "gpt-4o-mini"
    human_name = name or model
    prompt_yaml = _yaml_quote_block(instructions)
    yaml = (
        "component_type: Agent\n"
        'agentspec_version: "25.4.1"\n'
        f"name: {_yaml_quote_scalar(human_name)}\n"
        "llm_config:\n"
        "  component_type: OpenAiConfig\n"
        '  agentspec_version: "25.4.1"\n'
        f"  name: {_yaml_quote_scalar(model)}\n"
        f"  model_id: {_yaml_quote_scalar(model)}\n"
        f"system_prompt: {prompt_yaml}\n"
        "tools:\n"
    )
    # Tools
    tools_yaml_lines: List[str] = []
    if tool_names:
        for tname in tool_names or []:
            if not tool_defs_by_name or tname not in tool_defs_by_name:
                if allow_unknown_tools:
                    # skip unknown/prebuilt tools in non-strict mode
                    continue
                raise UnsupportedPatternError(
                    code="UNSUPPORTED_TOOL",
                    message="Agent references an unsupported or unknown tool",
                    details={"tool": tname},
                )
            tdef = tool_defs_by_name[tname]
            tools_yaml_lines.append("  - component_type: ServerTool")
            tools_yaml_lines.append('    agentspec_version: "25.4.1"')
            tools_yaml_lines.append(f"    name: {_yaml_quote_scalar(tdef.get('name', tname))}")
            ins = tdef.get("inputs") or []
            outs = tdef.get("outputs") or []
            if ins:
                tools_yaml_lines.append("    inputs:")
                for p in ins:
                    tools_yaml_lines.append(
                        f"      - title: {_yaml_quote_scalar(p.get('title','input'))}"
                    )
                    tools_yaml_lines.append(f"        type: {p.get('type','string')}")
            else:
                tools_yaml_lines.append("    inputs: []")
            if outs:
                tools_yaml_lines.append("    outputs:")
                for p in outs:
                    tools_yaml_lines.append(
                        f"      - title: {_yaml_quote_scalar(p.get('title','result'))}"
                    )
                    tools_yaml_lines.append(f"        type: {p.get('type','string')}")
            else:
                tools_yaml_lines.append("    outputs: []")
    # If no tools collected (either because none were provided or all were skipped), emit an empty list
    if not tools_yaml_lines:
        tools_yaml_lines.append("  []")
    yaml += "\n".join(tools_yaml_lines) + "\n"
    # Outputs from output_type (if available)
    if outputs_schema:
        yaml += "outputs:\n"
        for k, t in outputs_schema.items():
            yaml += f"  - title: {_yaml_quote_scalar(k)}\n"
            # t may be a simple type string or a JSON-schema-like dict
            if isinstance(t, dict):
                t_type = t.get("type", "string")
                yaml += f"    type: {t_type}\n"
                # Include enum if present to preserve Literal[...] information
                if "enum" in t and isinstance(t["enum"], list):
                    yaml += f"    json_schema:\n"
                    yaml += f"      type: {t_type}\n"
                    yaml += f"      enum:\n"
                    for v in t["enum"]:
                        if isinstance(v, str):
                            yaml += f"        - {_yaml_quote_scalar(v)}\n"
                        else:
                            yaml += f"        - {v}\n"
            else:
                yaml += f"    type: {t}\n"
    if gen:
        # Add default_generation_parameters
        parts = [
            "llm_config:",
            "  default_generation_parameters:",
        ]
        if "temperature" in gen and gen["temperature"] is not None:
            parts.append(f"    temperature: {gen['temperature']}")
        if "top_p" in gen and gen["top_p"] is not None:
            parts.append(f"    top_p: {gen['top_p']}")
        if "max_tokens" in gen and gen["max_tokens"] is not None:
            parts.append(f"    max_tokens: {int(gen['max_tokens'])}")
        # Inject after llm_config header
        inject = "\n".join(parts) + "\n"
        yaml = yaml.replace("llm_config:\n", inject)
    return yaml


class FlowASTParser:
    """Reverse parser: OpenAI Agents Python -> IRFlow (v0.3.3 rulepack).

    Scope: supports common patterns in provided examples.
    - Collects module-level Agent(...) definitions.
    - Extracts sequential Runner.run calls before the first if/elif chain.
    - Recognizes if/elif chains comparing against string literals; maps to a Branch node with mapping.
    - Wires control flow edges across Start -> pre-branch agents -> Branch -> per-branch first agent (if present) -> End.

    Limitations:
    - Tools are not materialized; Agent YAML will contain an empty tools list.
    - Data edges and Start/End IO schemas are not reconstructed.
    """

    def __init__(self, *, strict: bool = True) -> None:
        self.strict = strict

    def parse(self, src: str, *, flow_name: str = "workflow") -> IRFlow:
        try:
            mod = cst.parse_module(src)
        except Exception as e:  # pragma: no cover - parser errors are environment dependent
            raise FlowConversionError(
                code="PARSE_ERROR",
                message="Failed to parse source as Python",
                details={"error": str(e)},
            )

        # Pass 1: collect agents and function tools
        scan = _ModuleScan(strict=self.strict)
        mod.visit(scan)

        # Find run_workflow function body
        run_fn: Optional[cst.FunctionDef] = None

        class _FindRun(cst.CSTVisitor):
            def __init__(self) -> None:
                self.node: Optional[cst.FunctionDef] = None

            def visit_FunctionDef(self, n: cst.FunctionDef) -> Optional[bool]:
                if n.name.value == "run_workflow":
                    self.node = n
                return None

        fr = _FindRun()
        mod.visit(fr)
        run_fn = fr.node
        if not run_fn:
            raise UnsupportedPatternError(
                code="NO_RUN_WORKFLOW", message="Missing run_workflow entrypoint"
            )

        # Construct IR graph
        nid = _IdGen()
        nodes: list[IRNode] = []
        cedges: list[IRControlEdge] = []
        dedges: list[IRDataEdge] = []

        start_id = nid.new()
        # Populate Start IO from WorkflowInput
        start_meta: dict[str, Any] = {}
        if scan.workflow_input:
            io_list = [{"title": k, "type": v} for k, v in scan.workflow_input.items()]
            start_meta = {"inputs": io_list, "outputs": io_list}
        start = IRNode(id=start_id, name="Start", kind="start", meta=start_meta)
        nodes.append(start)
        tails = [Tail(node_id=start_id, last_agent_id=None, pending_branch_label=None)]

        # Descend into top-level or first with-trace body
        stmts: List[cst.BaseStatement] = []
        for s in list(run_fn.body.body):
            if isinstance(s, cst.With):
                if isinstance(s.body, cst.IndentedBlock):
                    stmts.extend(list(s.body.body))
                else:
                    stmts.append(s)
            else:
                stmts.append(s)  # type: ignore[arg-type]

        nodes, cedges, dedges, tails = self._build_block(
            stmts, scan, nid, nodes, cedges, dedges, tails
        )

        # If no End node was created, add a terminal End and connect remaining tails
        if not any(n.kind == "end" for n in nodes):
            eid = nid.new()
            enode = IRNode(id=eid, name="End", kind="end", meta={})
            nodes.append(enode)
            for t in tails:
                cedges.append(IRControlEdge(from_id=t.node_id, to_id=eid))

        flow = IRFlow(
            name=flow_name, start_id=start_id, nodes=nodes, edges_control=cedges, edges_data=dedges
        )
        return flow

    # ---- CFG builder ----
    def _build_block(
        self,
        body_stmts: List[cst.BaseStatement],
        scan: _ModuleScan,
        nid: "_IdGen",
        nodes: List[IRNode],
        cedges: List[IRControlEdge],
        dedges: List[IRDataEdge],
        tails: List["Tail"],
    ) -> Tuple[List[IRNode], List[IRControlEdge], List[IRDataEdge], List["Tail"]]:
        cur_tails = tails
        for stmt in body_stmts:
            if isinstance(stmt, cst.SimpleStatementLine):
                # Return
                for small in stmt.body:
                    if isinstance(small, cst.Return):
                        out = _infer_return_schema(small.value)
                        eid = nid.new()
                        enode = IRNode(id=eid, name="End", kind="end", meta={"outputs": out})
                        nodes.append(enode)
                        for t in cur_tails:
                            cedges.append(IRControlEdge(from_id=t.node_id, to_id=eid))
                        cur_tails = []
                        break
                    # Detect assignment of *_result_temp or *_result and infer final_output_as(str) usage
                    if isinstance(small, cst.Assign):
                        # Heuristic: when variable named like *_result_temp is assigned from await Runner.run(...)
                        val = small.value
                        if (
                            isinstance(val, cst.Await)
                            and isinstance(val.expression, cst.Call)
                            and _attr_or_name(val.expression.func) == "Runner.run"
                        ):
                            agent_name = _first_arg_name(val.expression)
                            if not agent_name:
                                raise UnsupportedPatternError(
                                    code="RUNNER_RUN_NO_AGENT",
                                    message="Runner.run missing agent variable",
                                )
                            # Validate the run consumes conversation_history
                            if not _call_uses_conversation_history(val.expression):
                                if self.strict:
                                    raise UnsupportedPatternError(
                                        code="CONVERSATION_INPUT_MISSING",
                                        message="Runner.run must include conversation_history in input for implicit propagation",
                                    )
                            # Validate subsequent append of new_items into conversation_history before next run
                            result_var = None
                            if len(small.targets) == 1 and isinstance(
                                small.targets[0].target, cst.Name
                            ):
                                result_var = small.targets[0].target.value
                            if result_var:
                                if not _validate_conversation_append(
                                    self, body_stmts, body_stmts.index(stmt) + 1, result_var
                                ):
                                    if self.strict:
                                        raise UnsupportedPatternError(
                                            code="CONVERSATION_PROPAGATION_REQUIRED",
                                            message="Conversation history propagation via '<result>.new_items' append is mandatory",
                                            details={"result_var": result_var},
                                        )
                            agent_def = scan.agents.get(agent_name)
                            display = agent_def.display_name if agent_def else agent_name
                            outputs_schema = None
                            if (
                                agent_def
                                and agent_def.output_model
                                and agent_def.output_model in scan.pyd_models
                            ):
                                outputs_schema = scan.pyd_models[agent_def.output_model]
                            yaml = _build_agent_yaml(
                                display,
                                agent_def.model_id if agent_def else None,
                                agent_def.instructions if agent_def else None,
                                agent_def.gen if agent_def else None,
                                tool_defs_by_name=scan.function_tools,
                                tool_names=(agent_def.tools if agent_def else []),
                                allow_unknown_tools=not self.strict,
                                outputs_schema=outputs_schema,
                            )
                            aid = nid.new()
                            anode = IRNode(
                                id=aid, name=display, kind="agent", meta={"agent_spec_yaml": yaml}
                            )
                            nodes.append(anode)
                            # Connect tails to the agent
                            ntails: List[Tail] = []
                            for t in cur_tails:
                                cedges.append(
                                    IRControlEdge(
                                        from_id=t.node_id, to_id=aid, branch=t.pending_branch_label
                                    )
                                )
                                ntails.append(
                                    Tail(node_id=aid, last_agent_id=aid, pending_branch_label=None)
                                )
                            cur_tails = ntails
                            # TODO: emit implicit conversation-history propagation in Agent Spec when available
                            continue
                    if isinstance(small, cst.Assign):
                        # Detect Await Runner.run on RHS
                        val = small.value
                        if (
                            isinstance(val, cst.Await)
                            and isinstance(val.expression, cst.Call)
                            and _attr_or_name(val.expression.func) == "Runner.run"
                        ):
                            agent_name = _first_arg_name(val.expression)
                            if not agent_name:
                                raise UnsupportedPatternError(
                                    code="RUNNER_RUN_NO_AGENT",
                                    message="Runner.run missing agent variable",
                                )
                            if not _call_uses_conversation_history(val.expression):
                                if self.strict:
                                    raise UnsupportedPatternError(
                                        code="CONVERSATION_INPUT_MISSING",
                                        message="Runner.run must include conversation_history in input for implicit propagation",
                                    )
                            result_var = None
                            if len(small.targets) == 1 and isinstance(
                                small.targets[0].target, cst.Name
                            ):
                                result_var = small.targets[0].target.value
                            if result_var:
                                if not _validate_conversation_append(
                                    self, body_stmts, body_stmts.index(stmt) + 1, result_var
                                ):
                                    if self.strict:
                                        raise UnsupportedPatternError(
                                            code="CONVERSATION_PROPAGATION_REQUIRED",
                                            message="Conversation history propagation via '<result>.new_items' append is mandatory",
                                            details={"result_var": result_var},
                                        )
                            agent_def = scan.agents.get(agent_name)
                            display = agent_def.display_name if agent_def else agent_name
                            outputs_schema = None
                            if (
                                agent_def
                                and agent_def.output_model
                                and agent_def.output_model in scan.pyd_models
                            ):
                                outputs_schema = scan.pyd_models[agent_def.output_model]
                            yaml = _build_agent_yaml(
                                display,
                                agent_def.model_id if agent_def else None,
                                agent_def.instructions if agent_def else None,
                                agent_def.gen if agent_def else None,
                                tool_defs_by_name=scan.function_tools,
                                tool_names=(agent_def.tools if agent_def else []),
                                allow_unknown_tools=not self.strict,
                                outputs_schema=outputs_schema,
                            )
                            # Attach tools via meta tools_def if present on the Agent call
                            # For now, try to re-scan the Agent(...) call site info is limited here; rely on pre-collected tools via agents map? Not available. Conservatively leave tools_def empty.
                            aid = nid.new()
                            anode = IRNode(
                                id=aid, name=display, kind="agent", meta={"agent_spec_yaml": yaml}
                            )
                            nodes.append(anode)
                            # Wire control + potential data edges from tails
                            ntails: List[Tail] = []  # type: ignore[no-redef]
                            for t in cur_tails:
                                cedges.append(
                                    IRControlEdge(
                                        from_id=t.node_id, to_id=aid, branch=t.pending_branch_label
                                    )
                                )
                                ntails.append(
                                    Tail(node_id=aid, last_agent_id=aid, pending_branch_label=None)
                                )
                            cur_tails = ntails
            elif isinstance(stmt, cst.If):
                # Resolve if/elif ladder
                branch_id = nid.new()
                mapping: Dict[str, str] = {}
                # Try to infer input_key from first condition LHS
                input_key = None
                if isinstance(stmt.test, cst.Comparison):
                    input_key = _lhs_key_from_equality(stmt.test)
                # If not directly detectable, try to infer from the last agent's structured output schema
                if input_key is None:
                    last_agent_tail = next(
                        (t for t in cur_tails if t.last_agent_id is not None), None
                    )
                    if last_agent_tail is not None:
                        # Find the last agent node and parse its AgentSpec to read outputs
                        last_node = next(
                            (n for n in nodes if n.id == last_agent_tail.last_agent_id), None
                        )
                        outs: list[dict] | None = None  # type: ignore
                        if last_node and (last_node.meta or {}).get("agent_spec_yaml"):
                            from pyagentspec.serialization.deserializer import (
                                AgentSpecDeserializer,
                            )
                            from pyagentspec.serialization.serializer import AgentSpecSerializer

                            comp = AgentSpecDeserializer().from_yaml(
                                (last_node.meta or {}).get("agent_spec_yaml")  # type: ignore[arg-type]
                            )
                            info = AgentSpecSerializer().to_dict(comp)
                            outs = info.get("outputs") or []
                        if outs:
                            # If exactly one field, use it; otherwise, leave None for strict handling below
                            if len(outs) == 1 and outs[0].get("title"):
                                input_key = str(outs[0].get("title"))
                if input_key is None and self.strict:
                    raise UnsupportedPatternError(
                        code="BRANCH_INPUT_KEY_UNDETECTABLE",
                        message="Unable to determine branch input key. Ensure comparisons target a structured output field (e.g., result['field'] == 'value').",
                    )
                bnode = IRNode(
                    id=branch_id,
                    name="Branch",
                    kind="branch",
                    meta={"mapping": mapping, "input_key": input_key},
                )
                nodes.append(bnode)
                # If we inferred an input_key and have a known last agent, add a data edge to reflect wiring
                if input_key is not None:
                    last_agent_tail = next(
                        (t for t in cur_tails if t.last_agent_id is not None), None
                    )
                    if last_agent_tail is not None:
                        dedges.append(
                            IRDataEdge(
                                source_id=last_agent_tail.last_agent_id,  # type: ignore[arg-type]
                                source_output=input_key,
                                dest_id=branch_id,
                                dest_input=input_key,
                            )
                        )
                # Connect incoming tails to branch node and wire data from last agent when possible
                for t in cur_tails:
                    cedges.append(IRControlEdge(from_id=t.node_id, to_id=branch_id))
                    if input_key and t.last_agent_id:
                        dedges.append(
                            IRDataEdge(
                                source_id=t.last_agent_id,
                                source_output=input_key,
                                dest_id=branch_id,
                                dest_input=input_key,
                            )
                        )
                # Unfold ladder
                arms: List[Tuple[str, List[cst.BaseStatement]]] = []
                else_body: Optional[List[cst.BaseStatement]] = None
                cur_if = stmt
                used_literals: set[str] = set()
                while True:
                    lit = _eq_rhs_string_literal(cur_if.test)
                    if lit is None:
                        # approval_request style: if someFunction(...): -> ClientTool
                        fn = _call_name(cur_if.test)
                        if fn:
                            # Insert tool node then a boolean branch
                            tool_id = nid.new()
                            tnode = IRNode(
                                id=tool_id,
                                name=fn,
                                kind="tool",
                                meta={
                                    "tool_def": {
                                        "name": fn,
                                        "kind": "client",
                                        "inputs": [{"title": "message", "type": "string"}],
                                        "outputs": [{"title": "result", "type": "boolean"}],
                                    }
                                },
                            )
                            nodes.append(tnode)
                            # Wire from previous tails to tool
                            ntails: List[Tail] = []  # type: ignore[no-redef]
                            for t in cur_tails:
                                cedges.append(IRControlEdge(from_id=t.node_id, to_id=tool_id))
                                ntails.append(
                                    Tail(
                                        node_id=tool_id,
                                        last_agent_id=t.last_agent_id,
                                        pending_branch_label=None,
                                    )
                                )
                            cur_tails = ntails
                            # Then convert this into a boolean branching with mapping true/false
                            branch_id = nid.new()
                            mapping = {"true": "true", "false": "false"}
                            bnode = IRNode(
                                id=branch_id,
                                name="Approval",
                                kind="branch",
                                meta={"mapping": mapping, "input_key": "approval"},
                            )
                            nodes.append(bnode)
                            for t in cur_tails:
                                cedges.append(IRControlEdge(from_id=t.node_id, to_id=branch_id))
                                # Wire tool boolean output to branch input
                                dedges.append(
                                    IRDataEdge(
                                        source_id=t.node_id,
                                        source_output="result",
                                        dest_id=branch_id,
                                        dest_input="approval",
                                    )
                                )
                            # Now set up a synthetic ladder as if comparisons existed
                            arms = [("true", _suite_body(cur_if.body))]
                            else_body = _else_body(cur_if.orelse)  # type: ignore[arg-type]
                            cur_tails = [
                                Tail(
                                    node_id=branch_id, last_agent_id=None, pending_branch_label=None
                                )
                            ]
                            # Process arms below as generic path
                            break
                        raise UnsupportedPatternError(
                            code="UNSUPPORTED_BRANCH_CONDITION",
                            message="If condition must be equality against a literal or a ClientTool call",
                        )
                    if lit in used_literals:
                        raise UnsupportedPatternError(
                            code="DUPLICATE_BRANCH_LITERAL",
                            message="Duplicate literal in if/elif ladder",
                            details={"literal": lit},
                        )
                    used_literals.add(lit)
                    arms.append((lit, _suite_body(cur_if.body)))
                    if isinstance(cur_if.orelse, cst.If):
                        cur_if = cur_if.orelse
                        continue
                    else:
                        else_body = _else_body(cur_if.orelse)  # type: ignore[arg-type]
                        break
                # For each arm, process with branch label
                all_new_tails: List[Tail] = []
                for lit, body in arms:
                    mapping[lit] = lit
                    # Seed tails from branch node but carry pending branch label for first edge
                    seed = [Tail(node_id=branch_id, last_agent_id=None, pending_branch_label=lit)]
                    nodes, cedges, dedges, arm_tails = self._build_block(
                        body, scan, nid, nodes, cedges, dedges, seed
                    )
                    all_new_tails.extend(arm_tails)
                if else_body is not None:
                    seed = [
                        Tail(node_id=branch_id, last_agent_id=None, pending_branch_label="default")
                    ]
                    nodes, cedges, dedges, arm_tails = self._build_block(
                        else_body, scan, nid, nodes, cedges, dedges, seed
                    )
                    all_new_tails.extend(arm_tails)
                cur_tails = all_new_tails
            # Ignore other statements that don't affect control flow
        return nodes, cedges, dedges, cur_tails


class _IdGen:
    def __init__(self) -> None:
        self._i = 0

    def new(self) -> str:
        self._i += 1
        return f"node_{self._i}"


@dataclass
class Tail:
    node_id: str
    last_agent_id: Optional[str]
    pending_branch_label: Optional[str]


def _suite_body(suite: cst.BaseSuite) -> List[cst.BaseStatement]:
    if isinstance(suite, cst.IndentedBlock):
        return list(suite.body)
    return []


def _else_body(orelse: Optional[cst.BaseStatement]) -> Optional[List[cst.BaseStatement]]:
    if isinstance(orelse, cst.Else):
        return _suite_body(orelse.body)
    return None


def _call_name(expr: cst.CSTNode) -> Optional[str]:
    # Returns function name if expr is a call expression
    if isinstance(expr, cst.Call):
        return _attr_or_name(expr.func)
    return None


def _call_uses_conversation_history(call: cst.Call) -> bool:
    # Verify input=[*conversation_history] is present
    for a in call.args:
        if isinstance(a.keyword, cst.Name) and a.keyword.value == "input":
            val = a.value
            if isinstance(val, cst.List):
                for el in val.elements:
                    # LibCST represents star elements as StarredElement directly in elements
                    if isinstance(el, cst.StarredElement):
                        inner = el.value
                        if isinstance(inner, cst.Name) and inner.value == "conversation_history":
                            return True
            # Simpler: input=conversation_history
            if isinstance(val, cst.Name) and val.value == "conversation_history":
                return True
    return False


def _is_conversation_extend(stmt: cst.BaseStatement, result_var: str) -> bool:
    # Matches: conversation_history.extend([item.to_input_item() for item in <result>.new_items])
    if not isinstance(stmt, cst.SimpleStatementLine):
        return False
    for small in stmt.body:
        expr = getattr(small, "value", None)
        if isinstance(expr, cst.Call):
            call = expr
            # conversation_history.extend(...)
            if (
                isinstance(call.func, cst.Attribute)
                and isinstance(call.func.value, cst.Name)
                and call.func.value.value == "conversation_history"
                and call.func.attr.value == "extend"
            ):
                if call.args:
                    arg0 = call.args[0].value
                    # check listcomp
                    if isinstance(arg0, cst.ListComp):
                        # [item.to_input_item() for item in X]
                        gen = arg0.for_in
                        if isinstance(gen, cst.CompFor) and isinstance(gen.iter, cst.Attribute):
                            # X should be <result_var>.new_items
                            it = gen.iter
                            if (
                                isinstance(it.value, cst.Name)
                                and it.value.value == result_var
                                and isinstance(it.attr, cst.Name)
                                and it.attr.value == "new_items"
                            ):
                                return True
    return False


def _next_effectful_index(stmts: List[cst.BaseStatement], start: int) -> int:
    # Skip non-effectful statements like simple variable assignments not to Runner.run
    i = start
    while i < len(stmts):
        s = stmts[i]
        # Stop at next Runner.run or control transfer (return/if)
        if isinstance(s, cst.SimpleStatementLine):
            for small in s.body:
                if isinstance(small, cst.Return):
                    return i
                if isinstance(small, cst.Assign):
                    val = small.value
                    if (
                        isinstance(val, cst.Await)
                        and isinstance(val.expression, cst.Call)
                        and _attr_or_name(val.expression.func) == "Runner.run"
                    ):
                        return i
        if isinstance(s, cst.If):
            return i
        i += 1
    return i


def _validate_conversation_append(  # type: ignore
    self, stmts: List[cst.BaseStatement], after_idx: int, result_var: str
) -> bool:
    # Look ahead to the next effectful statement and verify an extend call occurs before it
    end = _next_effectful_index(stmts, after_idx)
    i = after_idx
    while i < end:
        if _is_conversation_extend(stmts[i], result_var):
            return True
        i += 1
    return False


def _infer_return_schema(val: Optional[cst.BaseExpression]) -> List[Dict[str, Any]]:
    # Only handle dict literal with string keys mapping to scalars we can type
    out: List[Dict[str, Any]] = []
    if isinstance(val, cst.Dict):
        for el in val.elements:
            if isinstance(el, cst.DictElement) and isinstance(el.key, cst.SimpleString):
                key = ast.literal_eval(el.key.value)
                t = _schema_type_from_expr(el.value)
                if t:
                    out.append({"title": key, "type": t})
    return out


def _schema_type_from_expr(expr: cst.CSTNode) -> Optional[str]:
    if isinstance(expr, cst.SimpleString):
        return "string"
    if isinstance(expr, cst.Integer):
        return "integer"
    if isinstance(expr, cst.Float):
        return "number"
    if isinstance(expr, cst.Name) and expr.value in {"True", "False"}:
        return "boolean"
    return None


def _lhs_key_from_equality(test: cst.Comparison) -> Optional[str]:
    # Extract last string subscript key from the left side e.g., foo["bar"]["baz"] -> baz
    left = test.left
    cur = left
    last_key: Optional[str] = None
    while isinstance(cur, cst.Subscript):
        slc = cur.slice
        idx: Optional[cst.SubscriptElement] = None
        if isinstance(slc, cst.SubscriptElement):
            idx = slc
        elif isinstance(slc, cst.Index):
            idx = slc  # type: ignore[assignment]
        if idx and isinstance(idx.slice, cst.SimpleString):
            last_key = ast.literal_eval(idx.slice.value)
        cur = cur.value
    return last_key
