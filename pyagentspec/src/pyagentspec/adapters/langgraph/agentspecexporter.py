# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Literal, Optional, Tuple, Union, overload

from pyagentspec.adapters._agentspecexporter import (
    AdapterAgnosticAgentSpecExporter,
    _RuntimeDisaggregatedComponentsConfigT,
)
from pyagentspec.adapters._agentspecloader import RuntimeToAgentSpecConverter, _RuntimeComponentT
from pyagentspec.adapters.langgraph._agentspecconverter import LangGraphToAgentSpecConverter
from pyagentspec.versioning import AgentSpecVersionEnum


class AgentSpecExporter(AdapterAgnosticAgentSpecExporter):
    """Helper class to convert LangGraph objects into Agent Spec configuration."""

    @property
    def runtime_to_agentspec_converter(self) -> RuntimeToAgentSpecConverter:
        return LangGraphToAgentSpecConverter()

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
        Transform the given LangGraph component into the respective Agent Spec JSON representation.

        Parameters
        ----------
        runtime_component:
            LangGraph component to serialize to an Agent Spec configuration.
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
        Transform the given LangGraph component into the respective Agent Spec YAML representation.

        Parameters
        ----------
        runtime_component:
            LangGraph component to serialize to an Agent Spec configuration.
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
        Transform the given LangGraph component into the respective Agent Spec dictionary.

        Parameters
        ----------
        runtime_component:
            LangGraph component to serialize to an Agent Spec configuration.
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
