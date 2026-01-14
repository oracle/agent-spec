# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# mypy: ignore-errors

"""Helper to run a flow module safely by importing the file as a module.

Usage:
  python examples/run_flow.py examples/two_agent_review_flow.py "Your prompt here"
  python examples/run_flow.py examples/two_agent_review_flow_regenerated.py "Your prompt here"

This avoids dynamic exec of arbitrary strings and relies on Python's
import machinery to load a file as a module.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def import_from_path(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python examples/run_flow.py <flow_file.py> <prompt>")
        sys.exit(2)

    flow_path = Path(sys.argv[1]).resolve()
    prompt = sys.argv[2]

    mod = import_from_path(flow_path)
    WorkflowInput = getattr(mod, "WorkflowInput", None)
    run_workflow = getattr(mod, "run_workflow", None)
    if WorkflowInput is None or run_workflow is None:
        raise RuntimeError("Flow file must define WorkflowInput and run_workflow")

    import asyncio

    async def _run():
        inp = WorkflowInput(input_as_text=prompt)
        out = await run_workflow(inp)
        print("Result:", out)

    asyncio.run(_run())


if __name__ == "__main__":
    main()
