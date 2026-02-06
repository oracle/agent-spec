# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# mypy: ignore-errors

from pathlib import Path

from pyagentspec.adapters.openaiagents import AgentSpecExporter, AgentSpecLoader

EX_DIR = Path(__file__).resolve().parent
FLOW_PATH = EX_DIR / "two_agent_review_flow.py"
YAML_PATH = EX_DIR / "two_agent_review_flow.yaml"
REGEN_PATH = EX_DIR / "two_agent_review_flow_regenerated.py"


def convert_roundtrip() -> None:
    """Convert the reference flow to YAML and regenerate Python.

    This script intentionally does not execute the reference or regenerated code.
    It only writes the YAML and regenerated Python to disk so you can inspect or
    run them manually.
    """
    src = FLOW_PATH.read_text(encoding="utf-8")
    exporter = AgentSpecExporter()
    yaml_str = exporter.to_flow_yaml(src, strict=True)
    YAML_PATH.write_text(yaml_str, encoding="utf-8")

    loader = AgentSpecLoader()
    loader.load_yaml(
        yaml_str,
        output_path=str(REGEN_PATH),
        module_name="two_agent_review_regen",
    )

    print(f"Wrote YAML to: {YAML_PATH}")
    print(f"Wrote regenerated Python to: {REGEN_PATH}")


if __name__ == "__main__":
    convert_roundtrip()
