# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from types import FunctionType
from typing import Any, Literal, Optional, Tuple, Union, overload

from libcst._nodes.module import Module

from pyagentspec.adapters._agentspecexporter import (
    AdapterAgnosticAgentSpecExporter,
    _RuntimeDisaggregatedComponentsConfigT,
)
from pyagentspec.adapters._agentspecloader import RuntimeToAgentSpecConverter, _RuntimeComponentT
from pyagentspec.adapters.openaiagents._agentspecconverter import OpenAIToAgentSpecConverter
from pyagentspec.adapters.openaiagents.flows._rulepack_registry import resolve_rulepack
from pyagentspec.adapters.openaiagents.flows.errors import FlowConversionError
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.versioning import AgentSpecVersionEnum


class AgentSpecExporter(AdapterAgnosticAgentSpecExporter):
    """Helper class to convert OpenAI Agents SDK objects to Agent Spec configurations."""

    @property
    def runtime_to_agentspec_converter(self) -> RuntimeToAgentSpecConverter:
        return OpenAIToAgentSpecConverter()

    # ---- Flows: Python (OpenAI Agents) -> Agent Spec Flow ----
    def _flow_src_to_module(self, py_src: str | FunctionType) -> Module:
        """Parse a Python source string or function object into a LibCST module."""
        import inspect

        import libcst as cst

        if isinstance(py_src, str):
            src = py_src
        elif isinstance(py_src, FunctionType):
            try:
                src = inspect.getsource(py_src)
            except OSError as e:  # pragma: no cover - environment dependent
                raise FlowConversionError(
                    code="SOURCE_UNAVAILABLE",
                    message="Unable to retrieve source from function",
                    details={"error": str(e), "func": getattr(py_src, "__name__", None)},
                )
        else:
            raise TypeError("py_src must be a Python source string or function")

        return cst.parse_module(src)

    def to_flow_component(
        self,
        py_src: str | FunctionType,
        strict: bool = True,
        rulepack_version: str | None = None,
    ) -> AgentSpecComponent:
        """Export an OpenAI Agents Python workflow to an Agent Spec Flow component.

        Parameters:
        - py_src: Python source text or a callable defining the workflow (e.g., run_workflow).
        - strict: When True, raises on unsupported patterns. When False, attempts best-effort export.
        - rulepack_version: Optional explicit RulePack version; otherwise attempst to infer from SDK version.
        """
        mod = self._flow_src_to_module(py_src)
        pack = resolve_rulepack(rulepack_version)
        ir = pack.python_flow_to_ir(mod, strict=strict)
        return pack.ir_to_agentspec(ir, strict=strict)  # type: ignore

    def to_flow_yaml(
        self,
        py_src: str | FunctionType,
        strict: bool = True,
        rulepack_version: str | None = None,
    ) -> str:
        """Export an OpenAI Agents Python workflow to Agent Spec Flow YAML."""
        # Defer to PyAgentSpec serializer to keep adapter lean
        from pyagentspec.serialization import AgentSpecSerializer  # local import

        flow_comp = self.to_flow_component(py_src, strict=strict, rulepack_version=rulepack_version)
        return AgentSpecSerializer().to_yaml(flow_comp)

    @overload
    def to_json(self, runtime_component: _RuntimeComponentT) -> str: ...

    @overload
    def to_json(
        self,
        runtime_component: _RuntimeComponentT,
        agentspec_version: Optional[AgentSpecVersionEnum],
    ) -> str: ...

    @overload
    def to_json(
        self,
        runtime_component: _RuntimeComponentT,
        *,
        disaggregated_components: _RuntimeDisaggregatedComponentsConfigT,
        export_disaggregated_components: Literal[True],
    ) -> Tuple[str, str]: ...

    @overload
    def to_json(
        self,
        runtime_component: _RuntimeComponentT,
        *,
        disaggregated_components: Optional[_RuntimeDisaggregatedComponentsConfigT],
        export_disaggregated_components: Literal[False],
    ) -> str: ...

    @overload
    def to_json(
        self,
        runtime_component: _RuntimeComponentT,
        *,
        disaggregated_components: Optional[_RuntimeDisaggregatedComponentsConfigT],
        export_disaggregated_components: bool,
    ) -> Union[str, Tuple[str, str]]: ...

    @overload
    def to_json(
        self,
        runtime_component: _RuntimeComponentT,
        agentspec_version: Optional[AgentSpecVersionEnum],
        disaggregated_components: Optional[_RuntimeDisaggregatedComponentsConfigT],
        export_disaggregated_components: bool,
    ) -> Union[str, Tuple[str, str]]: ...

    def to_json(
        self,
        runtime_component: _RuntimeComponentT,
        agentspec_version: Optional[AgentSpecVersionEnum] = None,
        disaggregated_components: Optional[_RuntimeDisaggregatedComponentsConfigT] = None,
        export_disaggregated_components: bool = False,
    ) -> Union[str, Tuple[str, str]]:
        """
        Transform the given OpenAI Agents component into the respective Agent Spec JSON representation.

        Parameters
        ----------
        runtime_component:
            OpenAI Agents component to serialize to an Agent Spec configuration.
        agentspec_version:
            The Agent Spec version of the component.
        disaggregated_components:
            Configuration specifying the components/fields to disaggregate upon serialization.
            Each item can be:

            - A ``Component``: to disaggregate the component using its id
            - A tuple ``(Component, str)``: to disaggregate the component using
              a custom id.

            .. note::

                Components in ``disaggregated_components`` are disaggregated
                even if ``export_disaggregated_components`` is ``False``.
        export_disaggregated_components:
            Whether to export the disaggregated components or not. Defaults to ``False``.

        Returns
        -------
        If ``export_disaggregated_components`` is ``True``:

        str
            The JSON serialization of the root component.
        str
            The JSON serialization of the disaggregated components.

        If ``export_disaggregated_components`` is ``False``:

        str
            The JSON serialization of the root component.
        """
        return super().to_json(
            runtime_component,
            agentspec_version=agentspec_version,
            disaggregated_components=disaggregated_components,
            export_disaggregated_components=export_disaggregated_components,
        )

    @overload
    def to_yaml(self, runtime_component: _RuntimeComponentT) -> str: ...

    @overload
    def to_yaml(
        self,
        runtime_component: _RuntimeComponentT,
        agentspec_version: Optional[AgentSpecVersionEnum],
    ) -> str: ...

    @overload
    def to_yaml(
        self,
        runtime_component: _RuntimeComponentT,
        *,
        disaggregated_components: _RuntimeDisaggregatedComponentsConfigT,
        export_disaggregated_components: Literal[True],
    ) -> Tuple[str, str]: ...

    @overload
    def to_yaml(
        self,
        runtime_component: _RuntimeComponentT,
        *,
        disaggregated_components: Optional[_RuntimeDisaggregatedComponentsConfigT],
        export_disaggregated_components: Literal[False],
    ) -> str: ...

    @overload
    def to_yaml(
        self,
        runtime_component: _RuntimeComponentT,
        *,
        disaggregated_components: Optional[_RuntimeDisaggregatedComponentsConfigT],
        export_disaggregated_components: bool,
    ) -> Union[str, Tuple[str, str]]: ...

    @overload
    def to_yaml(
        self,
        runtime_component: _RuntimeComponentT,
        agentspec_version: Optional[AgentSpecVersionEnum],
        disaggregated_components: Optional[_RuntimeDisaggregatedComponentsConfigT],
        export_disaggregated_components: bool,
    ) -> Union[str, Tuple[str, str]]: ...

    def to_yaml(
        self,
        runtime_component: _RuntimeComponentT,
        agentspec_version: Optional[AgentSpecVersionEnum] = None,
        disaggregated_components: Optional[_RuntimeDisaggregatedComponentsConfigT] = None,
        export_disaggregated_components: bool = False,
    ) -> Union[str, Tuple[str, str]]:
        """
        Transform the given OpenAI Agents component into the respective Agent Spec YAML representation.

        Parameters
        ----------
        runtime_component:
            OpenAI Agents component to serialize to an Agent Spec configuration.
        agentspec_version:
            The Agent Spec version of the component.
        disaggregated_components:
            Configuration specifying the components/fields to disaggregate upon serialization.
            Each item can be:

            - A ``Component``: to disaggregate the component using its id
            - A tuple ``(Component, str)``: to disaggregate the component using
              a custom id.

            .. note::

                Components in ``disaggregated_components`` are disaggregated
                even if ``export_disaggregated_components`` is ``False``.
        export_disaggregated_components:
            Whether to export the disaggregated components or not. Defaults to ``False``.

        Returns
        -------
        If ``export_disaggregated_components`` is ``True``:

        str
            The YAML serialization of the root component.
        str
            The YAML serialization of the disaggregated components.

        If ``export_disaggregated_components`` is ``False``:

        str
            The YAML serialization of the root component.
        """
        return super().to_yaml(
            runtime_component,
            agentspec_version=agentspec_version,
            disaggregated_components=disaggregated_components,
            export_disaggregated_components=export_disaggregated_components,
        )

    @overload
    def to_dict(self, runtime_component: _RuntimeComponentT) -> dict[str, Any]: ...

    @overload
    def to_dict(
        self,
        runtime_component: _RuntimeComponentT,
        agentspec_version: Optional[AgentSpecVersionEnum],
    ) -> dict[str, Any]: ...

    @overload
    def to_dict(
        self,
        runtime_component: _RuntimeComponentT,
        *,
        disaggregated_components: _RuntimeDisaggregatedComponentsConfigT,
        export_disaggregated_components: Literal[True],
    ) -> Tuple[str, dict[str, Any]]: ...

    @overload
    def to_dict(
        self,
        runtime_component: _RuntimeComponentT,
        *,
        disaggregated_components: Optional[_RuntimeDisaggregatedComponentsConfigT],
        export_disaggregated_components: Literal[False],
    ) -> dict[str, Any]: ...

    @overload
    def to_dict(
        self,
        runtime_component: _RuntimeComponentT,
        *,
        disaggregated_components: Optional[_RuntimeDisaggregatedComponentsConfigT],
        export_disaggregated_components: bool,
    ) -> Union[dict[str, Any], Tuple[str, dict[str, Any]]]: ...

    @overload
    def to_dict(
        self,
        runtime_component: _RuntimeComponentT,
        agentspec_version: Optional[AgentSpecVersionEnum],
        disaggregated_components: Optional[_RuntimeDisaggregatedComponentsConfigT],
        export_disaggregated_components: bool,
    ) -> Union[dict[str, Any], Tuple[str, dict[str, Any]]]: ...

    def to_dict(
        self,
        runtime_component: _RuntimeComponentT,
        agentspec_version: Optional[AgentSpecVersionEnum] = None,
        disaggregated_components: Optional[_RuntimeDisaggregatedComponentsConfigT] = None,
        export_disaggregated_components: bool = False,
    ) -> Union[dict[str, Any], Tuple[str, dict[str, Any]]]:
        """
        Transform the given OpenAI Agents component into the respective Agent Spec dictionary.

        Parameters
        ----------
        runtime_component:
            OpenAI Agents component to serialize to an Agent Spec configuration.
        agentspec_version:
            The Agent Spec version of the component.
        disaggregated_components:
            Configuration specifying the components/fields to disaggregate upon serialization.
            Each item can be:

            - A ``Component``: to disaggregate the component using its id
            - A tuple ``(Component, str)``: to disaggregate the component using
              a custom id.

            .. note::

                Components in ``disaggregated_components`` are disaggregated
                even if ``export_disaggregated_components`` is ``False``.
        export_disaggregated_components:
            Whether to export the disaggregated components or not. Defaults to ``False``.

        Returns
        -------
        If ``export_disaggregated_components`` is ``True``:

        str
            The dictionary serialization of the root component.
        str
            The dictionary serialization of the disaggregated components.

        If ``export_disaggregated_components`` is ``False``:

        str
            The dictionary serialization of the root component.
        """
        return super().to_dict(
            runtime_component,
            agentspec_version=agentspec_version,
            disaggregated_components=disaggregated_components,
            export_disaggregated_components=export_disaggregated_components,
        )
