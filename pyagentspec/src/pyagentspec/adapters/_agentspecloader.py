# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Provide a framework-agnostic loader for Agent Spec configurations."""

import logging
from abc import ABC, abstractmethod
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    TypeAlias,
    Union,
    cast,
    overload,
)

from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.mcp import StdioTransport
from pyagentspec.serialization import AgentSpecDeserializer, ComponentDeserializationPlugin
from pyagentspec.serialization.componentpolicy import ComponentLoadPolicy, ComponentPolicyInput

_RuntimeComponentT: TypeAlias = Any
_RuntimeRegistryT: TypeAlias = Dict[str, Any]
_DEFAULT_BLOCKED_COMPONENTS: tuple[type[AgentSpecComponent], ...] = (StdioTransport,)


logger = logging.getLogger(__name__)


class AgentSpecToRuntimeConverter(Protocol):
    """Protocol for adapter-specific Agent Spec -> Runtime converters used by loaders."""

    def convert(
        self,
        agentspec_component: AgentSpecComponent,
        tool_registry: Dict[str, Any],
        **kwargs: Any,
    ) -> _RuntimeComponentT:
        """Convert an Agent Spec component into a runtime component."""


class RuntimeToAgentSpecConverter(Protocol):
    """Protocol for adapter-specific Runtime -> Agent Spec converters used by loaders."""

    def convert(
        self,
        runtime_component: _RuntimeComponentT,
        referenced_objects: Optional[Dict[str, AgentSpecComponent]] = None,
        **kwargs: Any,
    ) -> AgentSpecComponent:
        """Convert a runtime component into an Agent Spec component."""


class AdapterAgnosticAgentSpecLoader(ABC):
    """Convert serialized Agent Spec into adapter runtime components.

    This base class centralizes plugin-aware deserialization and support for
    disaggregated components (``import_only_referenced_components``).

    Subclasses supply a converter (typically an ``AgentSpecTo*Converter``) and may
    optionally provide a ``component_registry_converter`` to translate adapter
    runtime registries back to Agent Spec registries for reference resolution.

    Parameters
    ----------
    converter_factory:
        Callable that returns the adapter-specific converter used to convert Agent
        Spec components into runtime components.
    plugins:
        Optional list of Agent Spec deserialization plugins. If omitted, builtin
        plugins compatible with the latest supported Agent Spec version are used.
    component_registry_converter:
        Optional callable to convert a runtime components registry into an Agent
        Spec registry (mapping ids to Agent Spec components/values) so that
        references can be resolved during deserialization.
    allowed_components:
        Optional iterable of Agent Spec component type names or Component classes allowed
        to be loaded. If omitted, all component types are allowed unless blocked.
    blocked_components:
        Optional iterable of Agent Spec component type names or Component classes blocked
        from loading. If omitted, ``StdioTransport`` and its subclasses are blocked by default.
        Resolvable type names and Component classes also match subclasses; unresolved
        type names match only the exact serialized component type. When allow and
        block entries both match, the closest match in the component class hierarchy
        wins; block entries win same-distance ties.
    """

    def __init__(
        self,
        tool_registry: Optional[Dict[str, Any]] = None,
        plugins: Optional[List[ComponentDeserializationPlugin]] = None,
        *,
        allowed_components: Optional[ComponentPolicyInput] = None,
        blocked_components: Optional[ComponentPolicyInput] = None,
    ) -> None:
        self.plugins = plugins
        self.tool_registry = tool_registry or {}
        blocked_components = (
            _DEFAULT_BLOCKED_COMPONENTS if blocked_components is None else blocked_components
        )
        self.component_load_policy = ComponentLoadPolicy(
            allowed_components=allowed_components,
            blocked_components=blocked_components,
        )
        self.allowed_components = self.component_load_policy.allowed_components
        self.blocked_components = self.component_load_policy.blocked_components

    @property
    @abstractmethod
    def agentspec_to_runtime_converter(self) -> AgentSpecToRuntimeConverter:
        """Instance of runtime converter used to convert runtime components."""

    @property
    @abstractmethod
    def runtime_to_agentspec_converter(self) -> RuntimeToAgentSpecConverter:
        """Instance of runtime converter used to convert runtime components."""

    @overload
    def load_yaml(self, serialized_assistant: str) -> _RuntimeComponentT: ...

    @overload
    def load_yaml(
        self,
        serialized_assistant: str,
        components_registry: Optional[_RuntimeRegistryT],
    ) -> _RuntimeComponentT: ...

    @overload
    def load_yaml(
        self,
        serialized_assistant: str,
        *,
        import_only_referenced_components: bool,
    ) -> Union[_RuntimeComponentT, Dict[str, _RuntimeComponentT]]: ...

    @overload
    def load_yaml(
        self,
        serialized_assistant: str,
        components_registry: Optional[_RuntimeRegistryT],
        import_only_referenced_components: bool,
    ) -> Union[_RuntimeComponentT, Dict[str, _RuntimeComponentT]]: ...

    def load_yaml(
        self,
        serialized_assistant: str,
        components_registry: Optional[_RuntimeRegistryT] = None,
        import_only_referenced_components: bool = False,
    ) -> Union[_RuntimeComponentT, Dict[str, _RuntimeComponentT]]:
        """
        Transform the given Agent Spec YAML into runtime components, with support for disaggregated configurations.

        Parameters
        ----------
        serialized_assistant:
            Serialized Agent Spec configuration.
        components_registry:
            Optional registry mapping ids to runtime components/values. The loader will
            convert these back to Agent Spec components/values internally to resolve references during deserialization.
            If the conversion fails, the given value will be used without conversion.
        import_only_referenced_components:
            When ``True``, loads only the referenced/disaggregated components and returns a
            dictionary mapping component id to runtime components/values.
            These can be used as the ``components_registry`` when loading the main configuration.
            When ``False``, loads the main component and returns the runtime component.

        Returns
        -------
        If ``import_only_referenced_components`` is ``False``

        _RuntimeComponentT
            The runtime component.

        If ``import_only_referenced_components`` is ``True``

        Dict[str, _RuntimeComponentT]
            A dictionary containing the converted referenced components.
        """
        return self._load(
            loader="yaml",
            serialized_assistant=serialized_assistant,
            components_registry=components_registry,
            import_only_referenced_components=import_only_referenced_components,
        )

    @overload
    def load_json(self, serialized_assistant: str) -> _RuntimeComponentT: ...

    @overload
    def load_json(
        self,
        serialized_assistant: str,
        components_registry: Optional[_RuntimeRegistryT],
    ) -> _RuntimeComponentT: ...

    @overload
    def load_json(
        self,
        serialized_assistant: str,
        *,
        import_only_referenced_components: bool,
    ) -> Union[_RuntimeComponentT, Dict[str, _RuntimeComponentT]]: ...

    @overload
    def load_json(
        self,
        serialized_assistant: str,
        components_registry: Optional[_RuntimeRegistryT],
        import_only_referenced_components: bool,
    ) -> Union[_RuntimeComponentT, Dict[str, _RuntimeComponentT]]: ...

    def load_json(
        self,
        serialized_assistant: str,
        components_registry: Optional[_RuntimeRegistryT] = None,
        import_only_referenced_components: bool = False,
    ) -> Union[_RuntimeComponentT, Dict[str, _RuntimeComponentT]]:
        """
        Transform the given Agent Spec JSON into runtime components, with support for disaggregated configurations.

        Parameters
        ----------
        serialized_assistant:
            Serialized Agent Spec configuration.
        components_registry:
            Optional registry mapping ids to values, runtime components, and Agent Spec components.
            The loader will convert the latter to the respective runtime components during loading.
            If the conversion fails, the given value will be used without conversion.
        import_only_referenced_components:
            When ``True``, loads only the referenced/disaggregated components and returns a
            dictionary mapping component id to runtime components and values.
            These can be used as the ``components_registry`` when loading the main configuration.
            When ``False``, loads the main component and returns the runtime component.

        Returns
        -------
        If ``import_only_referenced_components`` is ``False``

        _RuntimeComponentT
            The runtime component.

        If ``import_only_referenced_components`` is ``True``

        Dict[str, _RuntimeComponentT]
            A dictionary containing the converted referenced components.
        """
        return self._load(
            loader="json",
            serialized_assistant=serialized_assistant,
            components_registry=components_registry,
            import_only_referenced_components=import_only_referenced_components,
        )

    @overload
    def load_dict(self, serialized_assistant: Dict[str, Any]) -> _RuntimeComponentT: ...

    @overload
    def load_dict(
        self,
        serialized_assistant: Dict[str, Any],
        components_registry: Optional[_RuntimeRegistryT],
    ) -> _RuntimeComponentT: ...

    @overload
    def load_dict(
        self,
        serialized_assistant: Dict[str, Any],
        *,
        import_only_referenced_components: bool,
    ) -> Union[_RuntimeComponentT, Dict[str, _RuntimeComponentT]]: ...

    @overload
    def load_dict(
        self,
        serialized_assistant: Dict[str, Any],
        components_registry: Optional[_RuntimeRegistryT],
        import_only_referenced_components: bool,
    ) -> Union[_RuntimeComponentT, Dict[str, _RuntimeComponentT]]: ...

    def load_dict(
        self,
        serialized_assistant: Dict[str, Any],
        components_registry: Optional[_RuntimeRegistryT] = None,
        import_only_referenced_components: bool = False,
    ) -> Union[_RuntimeComponentT, Dict[str, _RuntimeComponentT]]:
        """
        Transform the given Agent Spec dictionary into runtime components, with support for disaggregated configurations.

        Parameters
        ----------
        serialized_assistant:
            Serialized Agent Spec configuration as a dictionary.
        components_registry:
            Optional registry mapping ids to values, runtime components, and Agent Spec components.
            The loader will convert the latter to the respective runtime components during loading.
            If the conversion fails, the given value will be used without conversion.
        import_only_referenced_components:
            When ``True``, loads only the referenced/disaggregated components and returns a
            dictionary mapping component id to runtime components and values.
            These can be used as the ``components_registry`` when loading the main configuration.
            When ``False``, loads the main component and returns the runtime component.

        Returns
        -------
        If ``import_only_referenced_components`` is ``False``

        _RuntimeComponentT
            The runtime component.

        If ``import_only_referenced_components`` is ``True``

        Dict[str, _RuntimeComponentT]
            A dictionary containing the converted referenced components.
        """
        return self._load(
            loader="dict",
            serialized_assistant=serialized_assistant,
            components_registry=components_registry,
            import_only_referenced_components=import_only_referenced_components,
        )

    def load_component(self, agentspec_component: AgentSpecComponent) -> _RuntimeComponentT:
        """Convert a PyAgentSpec component into a runtime component.

        Subclasses may override this method to pass adapter-specific parameters
        into their converter (e.g., tool registries).
        """
        self.component_load_policy.validate_component_tree(agentspec_component)
        return self.agentspec_to_runtime_converter.convert(
            agentspec_component, tool_registry=self.tool_registry
        )

    def _convert_component_registry(
        self, runtime_component_registry: _RuntimeRegistryT
    ) -> Dict[str, Union[AgentSpecComponent, Any]]:
        # We try to convert the value we have, if it is not supported for conversion, we just keep the value as-is
        exporter = self.runtime_to_agentspec_converter
        converted_registry: Dict[str, Union[AgentSpecComponent, Any]] = {}
        for custom_id, runtime_component_or_value in runtime_component_registry.items():
            try:
                converted_registry[custom_id] = exporter.convert(runtime_component_or_value)
            except Exception as e:
                logger.warning(
                    "Failed to convert runtime component %s with exception `%s`. Fallback to given value.",
                    custom_id,
                    e,
                )
                converted_registry[custom_id] = runtime_component_or_value
        return converted_registry

    def _load(
        self,
        loader: str,
        serialized_assistant: Union[str, Dict[str, Any]],
        components_registry: Optional[_RuntimeRegistryT],
        import_only_referenced_components: bool,
    ) -> Union[_RuntimeComponentT, Dict[str, _RuntimeComponentT]]:

        deserializer = AgentSpecDeserializer(
            plugins=self.plugins,
            allowed_components=self.allowed_components,
            blocked_components=self.blocked_components,
        )
        deserializer_func: Callable[..., Any]
        if loader == "yaml":
            deserializer_func = deserializer.from_yaml
        elif loader == "json":
            deserializer_func = deserializer.from_json
        elif loader == "dict":
            deserializer_func = deserializer.from_dict
        else:
            raise ValueError(
                f"Unsupported loader type: `{loader}`. Expected `dict`, `json`, or `yaml`."
            )

        converted_registry = (
            self._convert_component_registry(components_registry)
            if components_registry is not None
            else None
        )
        if import_only_referenced_components:
            # Loading the disaggregated components
            agentspec_referenced_components = deserializer_func(
                serialized_assistant,
                components_registry=converted_registry,
                import_only_referenced_components=True,
            )
            referenced_components_dict = cast(
                Dict[str, AgentSpecComponent], agentspec_referenced_components
            )
            return {
                component_id: self.load_component(agentspec_component_)
                for component_id, agentspec_component_ in referenced_components_dict.items()
            }

        agentspec_component = cast(
            AgentSpecComponent,
            deserializer_func(
                serialized_assistant,
                components_registry=converted_registry,
                import_only_referenced_components=False,
            ),
        )
        return self.load_component(agentspec_component)
