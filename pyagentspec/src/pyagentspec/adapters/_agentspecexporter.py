# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from abc import ABC, abstractmethod
from typing import (
    Any,
    Callable,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    TypeAlias,
    Union,
    cast,
    overload,
)

from pyagentspec.adapters._agentspecloader import (
    RuntimeToAgentSpecConverter,
    _RuntimeComponentT,
)
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.serialization import AgentSpecSerializer, ComponentSerializationPlugin
from pyagentspec.serialization.types import (
    DisaggregatedComponentsConfigT as AgentSpecDisaggregatedComponentsConfigT,
)
from pyagentspec.versioning import AgentSpecVersionEnum

FieldID: TypeAlias = str
_RuntimeDisaggregatedComponentsConfigT: TypeAlias = Sequence[
    Union[_RuntimeComponentT, Tuple[_RuntimeComponentT, FieldID]]
]


class AdapterAgnosticAgentSpecExporter(ABC):
    """Helper class to convert Runtime objects to Agent Spec configurations."""

    def __init__(
        self,
        plugins: Optional[List[ComponentSerializationPlugin]] = None,
    ):
        """
        Parameters
        ----------
        plugins:
            List of serialization plugins to use.

        """
        self.plugins = plugins or []

    @property
    @abstractmethod
    def runtime_to_agentspec_converter(self) -> RuntimeToAgentSpecConverter:
        """Instance of runtime converter used to convert runtime components."""

    @overload
    def to_json(
        self,
        runtime_component: _RuntimeComponentT,
    ) -> str: ...

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
        Transform the given runtime component into the respective Agent Spec JSON representation.

        Parameters
        ----------
        runtime_component:
            Runtime component to serialize to an Agent Spec configuration.
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
        return cast(
            str,
            self._export(
                exporter="json",
                runtime_component=runtime_component,
                agentspec_version=agentspec_version,
                disaggregated_components=disaggregated_components,
                export_disaggregated_components=export_disaggregated_components,
            ),
        )

    @overload
    def to_yaml(
        self,
        runtime_component: _RuntimeComponentT,
    ) -> str: ...

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
        Transform the given Runtime component into the respective Agent Spec YAML representation.

        Parameters
        ----------
        runtime_component:
            Runtime component to serialize to an Agent Spec configuration.
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
        return cast(
            str,
            self._export(
                exporter="yaml",
                runtime_component=runtime_component,
                agentspec_version=agentspec_version,
                disaggregated_components=disaggregated_components,
                export_disaggregated_components=export_disaggregated_components,
            ),
        )

    @overload
    def to_dict(
        self,
        runtime_component: _RuntimeComponentT,
    ) -> dict[str, Any]: ...

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
        Transform the given Runtime component into the respective Agent Spec dictionary.

        Parameters
        ----------
        runtime_component:
            Runtime component to serialize to an Agent Spec configuration.
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
        return cast(
            dict[str, Any],
            self._export(
                exporter="dict",
                runtime_component=runtime_component,
                agentspec_version=agentspec_version,
                disaggregated_components=disaggregated_components,
                export_disaggregated_components=export_disaggregated_components,
            ),
        )

    def _export(
        self,
        exporter: str,
        runtime_component: _RuntimeComponentT,
        agentspec_version: Optional[AgentSpecVersionEnum] = None,
        disaggregated_components: Optional[_RuntimeDisaggregatedComponentsConfigT] = None,
        export_disaggregated_components: bool = False,
    ) -> Any:
        """Common implementation of the export function. The returned type depends on the type of exporter."""
        serializer = AgentSpecSerializer(plugins=self.plugins)
        serializer_func: Callable[..., Any]
        if exporter == "yaml":
            serializer_func = serializer.to_yaml
        elif exporter == "json":
            serializer_func = serializer.to_json
        elif exporter == "dict":
            serializer_func = serializer.to_dict
        else:
            raise ValueError(
                f"Unsupported exporter type: `{exporter}`. Expected `dict`, `json`, or `yaml`."
            )

        converted_disag_config, referenced_components = (
            self._convert_disaggregated_config(disaggregated_components)
            if disaggregated_components is not None
            else (None, None)
        )
        agentspec_assistant = self.runtime_to_agentspec_converter.convert(
            runtime_component, referenced_components
        )
        return serializer_func(
            agentspec_assistant,
            agentspec_version=agentspec_version,
            disaggregated_components=converted_disag_config,
            export_disaggregated_components=export_disaggregated_components,
        )

    def _convert_disaggregated_config(
        self, runtime_disag_config: _RuntimeDisaggregatedComponentsConfigT
    ) -> Tuple[AgentSpecDisaggregatedComponentsConfigT, dict[str, Any]]:
        agentspec_disaggregated_components = []
        referenced_components: dict[str, Any] = {}
        for disag_config in runtime_disag_config:
            is_pair = isinstance(disag_config, tuple)
            if is_pair:
                runtime_component, custom_id = disag_config
            else:
                runtime_component, custom_id = disag_config, None
            agentspec_component = self.runtime_to_agentspec_converter.convert(
                runtime_component, referenced_components
            )
            agentspec_disaggregated_components.append(
                (agentspec_component, custom_id) if is_pair else agentspec_component
            )
        return agentspec_disaggregated_components, referenced_components  # type: ignore

    def to_component(self, runtime_component: _RuntimeComponentT) -> AgentSpecComponent:
        """
        Transform the given Runtime component into the respective PyAgentSpec Component.

        Parameters
        ----------

        runtime_component:
            Runtime Component to serialize to a corresponding PyAgentSpec Component.
        """
        return self.runtime_to_agentspec_converter.convert(runtime_component)
