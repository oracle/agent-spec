#!/usr/bin/env python3
# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Validate an Agent Spec JSON/YAML config with PyAgentSpec."""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import Any

LOCAL_PYAGENTSPEC_RELATIVE_PATH = Path("pyagentspec/src/pyagentspec/__init__.py")


def iter_search_roots(path: Path) -> list[Path]:
    start = path.resolve()
    if start.is_file():
        start = start.parent
    return [start, *start.parents]


def find_repo_file(relative_path: Path, config_path: Path) -> Path | None:
    seen: set[Path] = set()
    for start in (config_path, Path.cwd(), Path(__file__)):
        for root in iter_search_roots(start):
            if root in seen:
                continue
            seen.add(root)
            candidate = root / relative_path
            if candidate.is_file():
                return candidate
    return None


def add_local_pyagentspec_to_path(config_path: Path) -> None:
    local_init = find_repo_file(LOCAL_PYAGENTSPEC_RELATIVE_PATH, config_path)
    if local_init is None:
        return
    src_path = str(local_init.parents[1])
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


def import_deserializer(config_path: Path) -> Any:
    add_local_pyagentspec_to_path(config_path)
    try:
        from pyagentspec.serialization import AgentSpecDeserializer
    except ImportError as exc:
        raise RuntimeError(
            "PyAgentSpec and its dependencies are required for validation. "
            "Inside an Agent Spec checkout, install with `uv pip install -p "
            ".venv-agentspec/bin/python -e ./pyagentspec`; outside the repo, "
            "install `pyagentspec` from PyPI or a source checkout."
        ) from exc
    return AgentSpecDeserializer


def component_label(component: Any) -> str:
    component_type = type(component).__name__
    component_name = getattr(component, "name", None)
    if component_name:
        return f"{component_type} {component_name!r}"
    return component_type


def validate_with_pyagentspec(path: Path) -> tuple[str, list[str]]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    deserializer = import_deserializer(path)()

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

    try:
        label, validation_warnings = validate_with_pyagentspec(args.config)
    except Exception as exc:  # noqa: BLE001 - CLI should print concise failure.
        print(f"FAIL PyAgentSpec validation failed: {exc}", file=sys.stderr)
        return 1

    for warning in validation_warnings:
        print(f"WARN {warning}")

    print(f"PASS PyAgentSpec validation completed for {label}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
