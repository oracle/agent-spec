# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Validate an Agent Spec JSON/YAML config with PyAgentSpec."""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import Any

from pyagentspec.serialization import AgentSpecDeserializer


def component_label(component: Any) -> str:
    component_type = type(component).__name__
    component_name = getattr(component, "name", None)
    if component_name:
        return f"{component_type} {component_name!r}"
    return component_type


def validate_with_pyagentspec(path: Path) -> tuple[str, list[str]]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    deserializer = AgentSpecDeserializer()

    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        if suffix in {".yaml", ".yml"}:
            component = deserializer.from_yaml(text)
        elif suffix == ".json":
            component = deserializer.from_json(text)
        else:
            try:
                component = deserializer.from_json(text)
            except json.JSONDecodeError:
                component = deserializer.from_yaml(text)

    return component_label(component), [str(warning.message) for warning in caught_warnings]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="Agent Spec JSON/YAML config to validate")
    args = parser.parse_args()

    label, validation_warnings = validate_with_pyagentspec(args.config)

    for warning in validation_warnings:
        print(f"WARN {warning}")

    print(f"PASS PyAgentSpec validation completed for {label}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
