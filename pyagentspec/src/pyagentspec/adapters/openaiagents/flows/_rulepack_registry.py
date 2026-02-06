# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol

from pyagentspec.adapters.openaiagents.flows.errors import RulePackNotFoundError


class RulePack(Protocol):
    version: str

    def python_flow_to_ir(self, mod, *, strict: bool = True) -> Any: ...  # type: ignore
    def ir_to_agentspec(self, ir, *, strict: bool = True) -> Any: ...  # type: ignore
    def agentspec_to_ir(self, flow, *, strict: bool = True) -> Any: ...  # type: ignore
    def codegen(self, ir, module_name: str | None = None) -> Any: ...  # type: ignore


@dataclass
class _Registry:
    packs: dict[str, RulePack]


_registry: _Registry = _Registry(packs={})


def register_rulepack(pack: RulePack) -> None:
    _registry.packs[pack.version] = pack


def get_rulepack(version: str) -> RulePack:
    try:
        return _registry.packs[version]
    except KeyError as e:
        raise RulePackNotFoundError(
            code="RULEPACK_NOT_FOUND",
            message=f"No RulePack registered for version {version}",
            details={"known_versions": sorted(_registry.packs)},
        ) from e


def resolve_rulepack(version_hint: Optional[str] = None) -> RulePack:
    """Resolve a RulePack by explicit version or SDK version.

    If version_hint is None, attempts to read agents.version.__version__ from vendored SDK.
    """
    # Lazy-register rulepacks on first use so callers don't need to import flows package.
    if not _registry.packs:
        from . import rulepacks as _rulepacks  # noqa: F401

    if version_hint is not None:
        return get_rulepack(version_hint)

    try:
        from agents.version import __version__ as sdk_version
    except Exception as e:  # pragma: no cover - environment dependent
        raise RulePackNotFoundError(
            code="SDK_VERSION_UNAVAILABLE",
            message="Unable to resolve SDK version from agents.version.__version__",
            details={"error": str(e)},
        ) from e

    return get_rulepack(sdk_version)
