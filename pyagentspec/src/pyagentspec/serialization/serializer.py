# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""
This module defines the AgentSpecSerializer class.

The class is used to write Agent Spec to a serialized form.
"""

import json
import warnings
from copy import copy
from typing import Dict, List, Literal, Optional, Tuple, Union, overload

import yaml

from pyagentspec.component import Component
from pyagentspec.serialization.serializationcontext import _SerializationContextImpl
from pyagentspec.serialization.serializationplugin import ComponentSerializationPlugin
from pyagentspec.versioning import AgentSpecVersionEnum

from .types import (
    ComponentAsDictT,
    DisaggregatedComponentsAsDictT,
    DisaggregatedComponentsConfigT,
    WatchingDict,
)


class AgentSpecSerializer:
    """Provides methods to serialize Agent Spec Components."""

    def __init__(
        self,
        plugins: Optional[List[ComponentSerializationPlugin]] = None,
        _allow_partial_model_serialization: bool = False,
    ) -> None:
        """
        Instantiate an Agent Spec Serializer.

        plugins:
            List of plugins to serialize additional components.
        _allow_partial_model_serialization:
            Whether to raise an exception during serialization if a BaseModel (including Components) is missing some fields
        """
        # for early failure when using incorrect plugins
        _SerializationContextImpl(
            plugins=plugins,
            _allow_partial_model_serialization=_allow_partial_model_serialization,
        )
        self.plugins = plugins
        self._allow_partial_model_serialization = _allow_partial_model_serialization

    @overload
    def to_yaml(
        self,
        component: Component,
    ) -> str: ...

    @overload
    def to_yaml(
        self,
        component: Component,
        agentspec_version: Optional[AgentSpecVersionEnum] = None,
    ) -> str: ...

    @overload
    def to_yaml(
        self,
        component: Component,
        *,
        disaggregated_components: Optional[DisaggregatedComponentsConfigT],
    ) -> str: ...

    @overload
    def to_yaml(
        self,
        component: Component,
        *,
        export_disaggregated_components: Literal[False],
    ) -> str: ...

    @overload
    def to_yaml(
        self,
        component: Component,
        *,
        export_disaggregated_components: bool,
    ) -> Union[str, Tuple[str, str]]: ...

    @overload
    def to_yaml(
        self,
        component: Component,
        *,
        disaggregated_components: Optional[DisaggregatedComponentsConfigT],
        export_disaggregated_components: Literal[False],
    ) -> str: ...

    @overload
    def to_yaml(
        self,
        component: Component,
        *,
        disaggregated_components: DisaggregatedComponentsConfigT,
        export_disaggregated_components: Literal[True],
    ) -> Tuple[str, str]: ...

    @overload
    def to_yaml(
        self,
        component: Component,
        *,
        disaggregated_components: Optional[DisaggregatedComponentsConfigT],
        export_disaggregated_components: bool,
    ) -> Union[str, Tuple[str, str]]: ...

    @overload
    def to_yaml(
        self,
        component: Component,
        agentspec_version: Optional[AgentSpecVersionEnum],
        disaggregated_components: Optional[DisaggregatedComponentsConfigT],
        export_disaggregated_components: bool,
    ) -> Union[str, Tuple[str, str]]: ...

    def to_yaml(
        self,
        component: Component,
        agentspec_version: Optional[AgentSpecVersionEnum] = None,
        disaggregated_components: Optional[DisaggregatedComponentsConfigT] = None,
        export_disaggregated_components: bool = False,
    ) -> Union[str, Tuple[str, str]]:
        """
        Serialize a component and its sub-components to YAML.

        Parameters
        ----------
        component:
            The component to serialize.
        agentspec_version:
            The Agent Spec version of the component
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

        Examples
        --------

        See examples in the ``.to_dict`` method docstring.

        """
        obj = self.to_dict(
            component=component,
            agentspec_version=agentspec_version,
            disaggregated_components=disaggregated_components,
            export_disaggregated_components=export_disaggregated_components,
        )
        return (
            tuple(yaml.safe_dump(x, sort_keys=False) for x in obj)  # type: ignore
            if isinstance(obj, tuple)
            else yaml.safe_dump(obj, sort_keys=False)
        )

    @overload
    def to_json(
        self,
        component: Component,
    ) -> str: ...

    @overload
    def to_json(
        self,
        component: Component,
        agentspec_version: Optional[AgentSpecVersionEnum],
    ) -> str: ...

    @overload
    def to_json(
        self,
        component: Component,
        *,
        disaggregated_components: Optional[DisaggregatedComponentsConfigT],
    ) -> str: ...

    @overload
    def to_json(
        self,
        component: Component,
        *,
        export_disaggregated_components: Literal[False],
    ) -> str: ...

    @overload
    def to_json(
        self,
        component: Component,
        *,
        export_disaggregated_components: bool,
    ) -> Union[str, Tuple[str, str]]: ...

    @overload
    def to_json(
        self,
        component: Component,
        *,
        disaggregated_components: Optional[DisaggregatedComponentsConfigT],
        export_disaggregated_components: Literal[False],
    ) -> str: ...

    @overload
    def to_json(
        self,
        component: Component,
        *,
        disaggregated_components: Optional[DisaggregatedComponentsConfigT],
        export_disaggregated_components: Literal[True],
    ) -> Tuple[str, str]: ...

    @overload
    def to_json(
        self,
        component: Component,
        *,
        disaggregated_components: Optional[DisaggregatedComponentsConfigT],
        export_disaggregated_components: bool,
    ) -> Union[str, Tuple[str, str]]: ...

    @overload
    def to_json(
        self,
        component: Component,
        agentspec_version: Optional[AgentSpecVersionEnum],
        disaggregated_components: Optional[DisaggregatedComponentsConfigT],
        export_disaggregated_components: bool,
    ) -> Union[str, Tuple[str, str]]: ...

    def to_json(
        self,
        component: Component,
        agentspec_version: Optional[AgentSpecVersionEnum] = None,
        disaggregated_components: Optional[DisaggregatedComponentsConfigT] = None,
        export_disaggregated_components: bool = False,
        indent: Optional[int] = None,
    ) -> Union[str, Tuple[str, str]]:
        """
        Serialize a component and its sub-components to JSON.

        Parameters
        ----------
        component:
            The component to serialize.
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
        indent:
            The number of spaces to use for the JSON indentation.

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

        Examples
        --------

        See examples in the ``.to_dict`` method docstring.
        """
        obj = self.to_dict(
            component=component,
            agentspec_version=agentspec_version,
            disaggregated_components=disaggregated_components,
            export_disaggregated_components=export_disaggregated_components,
        )
        return (
            tuple(json.dumps(x, indent=indent, sort_keys=False) for x in obj)  # type: ignore
            if isinstance(obj, tuple)
            else json.dumps(obj, indent=indent, sort_keys=False)
        )

    @overload
    def to_dict(
        self,
        component: Component,
    ) -> ComponentAsDictT: ...

    @overload
    def to_dict(
        self,
        component: Component,
        agentspec_version: Optional[AgentSpecVersionEnum],
    ) -> ComponentAsDictT: ...

    @overload
    def to_dict(
        self,
        component: Component,
        *,
        disaggregated_components: Optional[DisaggregatedComponentsConfigT],
    ) -> ComponentAsDictT: ...

    @overload
    def to_dict(
        self,
        component: Component,
        *,
        export_disaggregated_components: Literal[False],
    ) -> ComponentAsDictT: ...

    @overload
    def to_dict(
        self,
        component: Component,
        *,
        export_disaggregated_components: bool,
    ) -> Union[ComponentAsDictT, DisaggregatedComponentsAsDictT]: ...

    @overload
    def to_dict(
        self,
        component: Component,
        *,
        disaggregated_components: Optional[DisaggregatedComponentsConfigT],
        export_disaggregated_components: Literal[False],
    ) -> ComponentAsDictT: ...

    @overload
    def to_dict(
        self,
        component: Component,
        *,
        disaggregated_components: DisaggregatedComponentsConfigT,
        export_disaggregated_components: Literal[True],
    ) -> Tuple[ComponentAsDictT, DisaggregatedComponentsAsDictT]: ...

    @overload
    def to_dict(
        self,
        component: Component,
        *,
        disaggregated_components: Optional[DisaggregatedComponentsConfigT],
        export_disaggregated_components: bool,
    ) -> Union[ComponentAsDictT, Tuple[ComponentAsDictT, DisaggregatedComponentsAsDictT]]: ...

    @overload
    def to_dict(
        self,
        component: Component,
        agentspec_version: Optional[AgentSpecVersionEnum],
        disaggregated_components: Optional[DisaggregatedComponentsConfigT],
        export_disaggregated_components: bool,
    ) -> Union[ComponentAsDictT, Tuple[ComponentAsDictT, DisaggregatedComponentsAsDictT]]: ...

    def to_dict(
        self,
        component: Component,
        agentspec_version: Optional[AgentSpecVersionEnum] = None,
        disaggregated_components: Optional[DisaggregatedComponentsConfigT] = None,
        export_disaggregated_components: bool = False,
    ) -> Union[ComponentAsDictT, Tuple[ComponentAsDictT, DisaggregatedComponentsAsDictT]]:
        """
        Serialize a component and its sub-components to a dictionary.

        Parameters
        ----------
        component:
            The component to serialize.
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

        ComponentAsDictT
            A dictionary containing the serialization of the root component.
        DisaggregatedComponentsAsDictT
            A dictionary containing the serialization of the disaggregated components.

        If ``export_disaggregated_components`` is ``False``:

        ComponentAsDictT
            A dictionary containing the serialization of the root component.

        Examples
        --------
        Basic serialization is done as follows.

        >>> from pyagentspec.agent import Agent
        >>> from pyagentspec.llms import VllmConfig
        >>> from pyagentspec.serialization import AgentSpecSerializer
        >>> llm = VllmConfig(
        ...     name="vllm",
        ...     model_id="model1",
        ...     url="http://dev.llm.url"
        ... )
        >>> agent = Agent(
        ...     name="Simple Agent",
        ...     llm_config=llm,
        ...     system_prompt="Be helpful"
        ... )
        >>> agent_config = AgentSpecSerializer().to_dict(agent)

        To use component disaggregation, specify the component(s) to disaggregate
        in the ``disaggregated_components`` parameter, and ensure that
        ``export_disaggregated_components`` is set to ``True``.

        >>> llm = VllmConfig(
        ...     id="llm_id",
        ...     name="vllm",
        ...     model_id="model1",
        ...     url="http://dev.llm.url"
        ... )
        >>> agent = Agent(name="Simple Agent", llm_config=llm, system_prompt="Be helpful")
        >>> agent_config, disag_config = AgentSpecSerializer().to_dict(
        ...     component=agent,
        ...     disaggregated_components=[llm],
        ...     export_disaggregated_components=True,
        ... )
        >>> list(disag_config["$referenced_components"].keys())
        ['llm_id']

        Finally, you can specify custom ids for the disaggregated components.

        >>> agent_config, disag_config = AgentSpecSerializer().to_dict(
        ...     component=agent,
        ...     disaggregated_components=[(llm, "custom_llm_id")],
        ...     export_disaggregated_components=True,
        ... )
        >>> list(disag_config["$referenced_components"].keys())
        ['custom_llm_id']

        """
        # 1. we serialize the disaggregated components
        converted_config: List[Tuple[Component, str]] = []
        components_id_mapping: Dict[str, str] = {}
        for config_ in disaggregated_components or []:
            if isinstance(config_, Component):
                mapped_component_id = config_.id
                converted_config.append((config_, mapped_component_id))
                components_id_mapping[mapped_component_id] = mapped_component_id
            elif isinstance(config_, tuple) and len(config_) == 2:
                disag_component, mapped_id = config_
                converted_config.append(config_)
                components_id_mapping[disag_component.id] = mapped_id
            elif isinstance(config_, tuple) and len(config_) == 3:
                raise NotImplementedError("Component field disaggregation is not supported yet")
            else:
                raise ValueError(f"Invalid disaggregated_components entry: {config_}")

        disaggregated_components_as_dict: Dict[str, ComponentAsDictT] = {}
        for disag_component, mapped_component_id in converted_config:
            if disag_component is component:
                raise ValueError(f"Disaggregating the root component is not allowed")
            disag_serialization_context = _SerializationContextImpl(
                plugins=self.plugins,
                _allow_partial_model_serialization=self._allow_partial_model_serialization,
            )
            model_dump = disag_serialization_context._save_to_dict(
                disag_component, agentspec_version=agentspec_version
            )
            disaggregated_components_as_dict[mapped_component_id] = model_dump

        serialized_disaggregated_components = {
            "$referenced_components": disaggregated_components_as_dict
        }

        # 2. We export the main config
        watched_components_id_mapping = WatchingDict(copy(components_id_mapping))
        main_serialization_context = _SerializationContextImpl(
            plugins=self.plugins,
            resolved_components=copy(disaggregated_components_as_dict),
            components_id_mapping=watched_components_id_mapping,
            _allow_partial_model_serialization=self._allow_partial_model_serialization,
        )

        main_model_dump = main_serialization_context._save_to_dict(
            component, agentspec_version=agentspec_version
        )
        if unvisited_keys := watched_components_id_mapping.get_unvisited_keys():
            warnings.warn(
                (
                    "The following specified disaggregated components are not part "
                    f"of the main component: {unvisited_keys}. Make sure that those "
                    "components are used in the main component."
                ),
                UserWarning,
            )
        if not export_disaggregated_components:
            return main_model_dump
        return main_model_dump, serialized_disaggregated_components
