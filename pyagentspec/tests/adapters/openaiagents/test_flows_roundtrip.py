# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


import asyncio
import types
from pathlib import Path
from typing import Literal, get_origin

import pytest
from pydantic import BaseModel
from retry_utils import retry_attempts

ROOT = Path(__file__).resolve().parent
REFERENCE_FLOW_PATH = ROOT / "flows" / "router_math_flow.py"


def _exec_module_from_code(code: str, module_name: str = "_flow_module") -> types.ModuleType:
    mod = types.ModuleType(module_name)
    exec(compile(code, module_name, "exec"), mod.__dict__)  # nosec
    return mod


def _run_flow_sync(mod: types.ModuleType, message: str, *, tools: dict | None = None) -> str:
    # Instantiate the module's WorkflowInput and call run_workflow
    WorkflowInput = getattr(mod, "WorkflowInput")
    run_workflow = getattr(mod, "run_workflow")

    wi = WorkflowInput(input_as_text=message)

    # Support both signatures: run_workflow(workflow_input) and run_workflow(workflow_input, tools=...)
    async def _runner():
        try:
            if tools is None:
                return await run_workflow(wi)
            # Some generated code accepts tools registry; pass when provided
            return await run_workflow(wi, tools=tools)
        except TypeError:
            # Fallback to single-arg if tools not supported by the function
            return await run_workflow(wi)

    # Run with retries to mitigate flakiness in agent execution
    with retry_attempts() as attempt:
        result = attempt(lambda: asyncio.run(_runner()))
    # Normalize output as string for assertions
    if isinstance(result, dict) and "output_text" in result:
        return str(result["output_text"]) if result["output_text"] is not None else ""
    return str(result)


def _override_module_models(mod: types.ModuleType) -> None:
    """Override Agent model in a compiled flow module to a target hosted model."""
    from agents.agent import Agent
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI

    from ..conftest import oss_api_url, should_skip_llm_test

    if should_skip_llm_test():
        pytest.skip("LLM called, skipping test")

    base_url = oss_api_url
    if not base_url.startswith("http"):
        base_url = "http://" + base_url
    if not base_url.endswith("v1"):
        base_url += "/v1"

    client = AsyncOpenAI(api_key="", base_url=base_url)
    model = OpenAIChatCompletionsModel("openai/gpt-oss-120b", client)
    for v in list(mod.__dict__.values()):
        if isinstance(v, Agent):
            v.model = model


@pytest.mark.parametrize(
    "flow_file",
    [
        ROOT / "flows" / "router_math_flow.py",
        ROOT / "flows" / "simple_agent_no_tools.py",
        ROOT / "flows" / "single_agent_three_tools_math.py",
        ROOT / "flows" / "linear_chain_three_agents.py",
        ROOT / "flows" / "structured_schemas_variety.py",
    ],
)
def test_flow_roundtrip_converts_and_generates_code(
    capsys: pytest.CaptureFixture[str], flow_file: Path
) -> None:

    from pyagentspec.adapters.openaiagents import AgentSpecExporter, AgentSpecLoader

    # Load the flow source, export to Agent Spec YAML, then regenerate Python code
    src = flow_file.read_text(encoding="utf-8")

    exporter = AgentSpecExporter()
    # Use non-strict to tolerate minor differences and missing annotations in tools
    yaml_str = exporter.to_flow_yaml(src, strict=False)

    loader = AgentSpecLoader()
    regenerated_code = loader.load_yaml(yaml_str)

    # Print the regenerated code for manual inspection when needed
    print(f"===== Regenerated Flow Code ({flow_file.stem}) BEGIN =====")
    print(regenerated_code)
    print(f"===== Regenerated Flow Code ({flow_file.stem}) END =====")

    # Ensure code is syntactically valid and defines expected symbols
    regenerated_mod = _exec_module_from_code(
        regenerated_code, module_name=f"regenerated_{flow_file.stem}"
    )
    assert hasattr(regenerated_mod, "WorkflowInput")
    assert hasattr(regenerated_mod, "run_workflow")

    # Also ensure original reference compiles cleanly
    reference_mod = _exec_module_from_code(src, module_name=f"reference_{flow_file.stem}")
    assert hasattr(reference_mod, "WorkflowInput")
    assert hasattr(reference_mod, "run_workflow")

    # Common assertions that should hold across all flows
    # - A trace context is present to bracket the workflow
    assert "with trace(" in regenerated_code

    # - LLM model identifiers should be present. We verify that any model strings appearing
    #   in the original source are also present in the regenerated code.
    for model_str in ("gpt-5-mini", "gpt-4o-mini"):
        if model_str in src:
            assert model_str in regenerated_code

    # Flow-specific structural assertions for stronger confidence
    stem = flow_file.stem
    code = regenerated_code

    if stem == "router_math_flow":
        # Expect router + 3 math tool agents + fail
        for agent_name in ("Router", "Zwik", "Zwak", "Zwok", "Fail"):
            assert f'name="{agent_name}"' in code or f"name='{agent_name}'" in code

        # Expect exactly three function tools defined
        assert code.count("@function_tool") >= 3

        # Expect branch on router result to three paths and an else/fail path
        for branch_label in ("zwik", "zwak", "zwok"):
            assert f"'{branch_label}'" in code or f'"{branch_label}"' in code
        assert "router" in code  # router agent invoked
        assert "fail" in code  # fail agent reachable

    elif stem == "simple_agent_no_tools":
        # One agent, no tools, and a simple run
        assert ('name="SimpleEcho"' in code) or ("name='SimpleEcho'" in code)
        assert "Runner.run" in code
        # No function tool decorator usages in this flow (ignore mention in header comments)
        assert "\n@function_tool" not in code

    elif stem == "single_agent_three_tools_math":
        # Single agent with three tools. Expect three function tools and the agent to list them.
        for tool in ("compute_glip", "compute_glap", "compute_glop"):
            assert tool in code
        assert code.count("@function_tool") >= 3
        # The tricoder agent should exist and have a tools list in code
        assert (
            ('name="TriCoder"' in code)
            or ("name='TriCoder'" in code)
            or ('name="Tricoder"' in code)
            or ("name='Tricoder'" in code)
            or ("TriCoder" in code)
            or ("Tricoder" in code)
        )
        assert "tools=[" in code

    elif stem == "linear_chain_three_agents":
        # Three agents, no tools, executed in order normalizer -> classifier -> responder
        assert "\n@function_tool" not in code
        # Ensure order of agent execution is preserved in the code string using call argument tokens
        idx_n = code.find("normalizer,")
        idx_c = code.find("classifier,")
        idx_r = code.find("responder,")
        assert idx_n != -1 and idx_c != -1 and idx_r != -1
        assert idx_n < idx_c < idx_r

    elif stem == "structured_schemas_variety":
        # Expect three agents with structured outputs including Literals and multiple fields
        assert ('name="Extractor"' in code) or ("name='Extractor'" in code)
        assert ('name="Sentiment"' in code) or ("name='Sentiment'" in code)
        assert ('name="Summarizer"' in code) or ("name='Summarizer'" in code)

        # Introspect regenerated module for BaseModel schemas and their fields
        model_classes = [
            v
            for v in regenerated_mod.__dict__.values()
            if isinstance(v, type) and issubclass(v, BaseModel)
        ]

        def fields_of(m: type[BaseModel]) -> set[str]:
            fld_map = getattr(m, "model_fields", getattr(m, "__fields__", {}))
            return set(fld_map.keys())

        field_sets = [fields_of(m) for m in model_classes]

        # Multi-field model should include exactly these fields
        assert any(
            fs == {"title", "priority", "urgent"} for fs in field_sets
        ), f"Expected Extraction schema fields missing; saw {field_sets}"
        # Summary schema must include both 'summary' and 'quality'
        assert any(
            fs == {"summary", "quality"} for fs in field_sets
        ), f"Expected SummaryQuality schema with fields summary+quality; saw {field_sets}"
        # There should be a schema with a single 'label' field (for sentiment)
        assert any(
            fs == {"label"} for fs in field_sets
        ), f"Expected SentimentLabel schema with field 'label'; saw {field_sets}"

        # Verify that 'label' and 'quality' fields are Literal[...] not plain strings
        def get_model_by_fields(target: set[str]) -> type[BaseModel] | None:
            for m in model_classes:
                if fields_of(m) == target:
                    return m
            return None

        label_model = get_model_by_fields({"label"})
        assert label_model is not None, "Missing model for sentiment label"
        label_ann = getattr(label_model, "__annotations__", {}).get("label")
        assert get_origin(label_ann) is Literal, "Sentiment 'label' must be a Literal[...]"

        summary_model = get_model_by_fields({"summary", "quality"})
        assert summary_model is not None, "Missing summary+quality model"
        qual_ann = getattr(summary_model, "__annotations__", {}).get("quality")
        assert get_origin(qual_ann) is Literal, "Summary 'quality' must be a Literal[...]"

    # Emit to captured stdout
    capsys.readouterr()


@pytest.mark.parametrize(
    "flow_file, cases, toolset",
    [
        (
            ROOT / "flows" / "router_math_flow.py",
            [
                ("what is the zwik function of 3 and 5?", "34"),
                ("what is the zwak function of 3 and 5?", "7"),
                ("what is the zwok function of 3 and 5?", "23"),
                (";lkajshdflkajhsdf", "error"),  # invalid -> fail branch
            ],
            "router",
        ),
        (
            ROOT / "flows" / "simple_agent_no_tools.py",
            [("Hello there", "Hello there")],
            None,
        ),
        (
            ROOT / "flows" / "single_agent_three_tools_math.py",
            [
                ("please do glip of 2 and 3", "25"),
                ("do glap of 2 and 3", "35"),
                ("glop 9 and 4", "5"),
            ],
            "math3",
        ),
        (
            ROOT / "flows" / "linear_chain_three_agents.py",
            [("What is this?", "Q"), ("do this now", "C")],
            None,
        ),
    ],
)
def test_flows_roundtrip_and_run_live(
    flow_file: Path, cases: list[tuple[str, str]], toolset: str | None
) -> None:

    from pyagentspec.adapters.openaiagents import AgentSpecExporter, AgentSpecLoader

    # Read and convert (code -> YAML -> code)
    src = flow_file.read_text(encoding="utf-8")
    exporter = AgentSpecExporter()
    yaml_str = exporter.to_flow_yaml(src, strict=True)
    loader = AgentSpecLoader()
    regenerated_code = loader.load_yaml(yaml_str)

    # Compile reference and regenerated modules
    reference_mod = _exec_module_from_code(src, module_name=f"reference_{flow_file.stem}")
    regenerated_mod = _exec_module_from_code(
        regenerated_code, module_name=f"regen_{flow_file.stem}"
    )

    _override_module_models(regenerated_mod)
    _override_module_models(reference_mod)

    # Optional tools registry for regenerated code
    tools_registry = None
    if toolset == "router":

        def _zwik(a: int, b: int):
            return a**2 + b**2

        def _zwak(a: int, b: int):
            return a * b - a - b

        def _zwok(a: int, b: int):
            return a * b + a + b

        tools_registry = {
            "calculate_zwik_function": _zwik,
            "calculate_zwak_function": _zwak,
            "calculate_zwok_function": _zwok,
        }
    elif toolset == "math3":

        def _glip(a: int, b: int):
            return a * a + 2 * a * b + b * b

        def _glap(a: int, b: int):
            return a * a * a + b * b * b

        def _glop(a: int, b: int):
            return a - b

        tools_registry = {
            "compute_glip": _glip,
            "compute_glap": _glap,
            "compute_glop": _glop,
        }

    for message, expected in cases:
        # Run reference flow
        with retry_attempts() as attempt:
            ref_output = attempt(
                lambda: _run_flow_sync(reference_mod, message),
                validate=lambda s: expected.lower() in s.lower(),
            )

        # Run regenerated flow
        with retry_attempts() as attempt:
            regen_output = attempt(
                lambda: _run_flow_sync(regenerated_mod, message, tools=tools_registry),
                validate=lambda s: expected.lower() in s.lower(),
            )

        assert expected.lower() in ref_output.lower()
        assert expected.lower() in regen_output.lower()
