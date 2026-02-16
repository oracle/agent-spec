# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


"""
Define the AgentSpecDeserializer class.

The class provides entry points to read Agent Spec from a serialized form.
"""

import json
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, Union, overload

import yaml

from pyagentspec.component import Component
from pyagentspec.serialization.deserializationcontext import _DeserializationContextImpl
from pyagentspec.serialization.deserializationplugin import ComponentDeserializationPlugin
from pyagentspec.serialization.types import ComponentAsDictT, ComponentsRegistryT
from pyagentspec.validation_helpers import PyAgentSpecErrorDetails


class AgentSpecDeserializer:
    """Provides methods to deserialize Agent Spec Components."""

    def __init__(self, plugins: Optional[List[ComponentDeserializationPlugin]] = None) -> None:
        """
        Instantiate an Agent Spec Deserializer.

        plugins:
            List of plugins to serialize additional components.
        """
        _DeserializationContextImpl(
            plugins=plugins
        )  # for early failure when using incorrect plugins
        self.plugins = plugins

    @overload
    def from_yaml(self, yaml_content: str) -> Component:
        """Load a component and its sub-components from YAML."""

    @overload
    def from_yaml(
        self,
        yaml_content: str,
        components_registry: Optional[ComponentsRegistryT],
    ) -> Component: ...

    @overload
    def from_yaml(
        self,
        yaml_content: str,
        *,
        import_only_referenced_components: Literal[False],
    ) -> Component: ...

    @overload
    def from_yaml(
        self,
        yaml_content: str,
        *,
        import_only_referenced_components: Literal[True],
    ) -> Dict[str, Component]: ...

    @overload
    def from_yaml(
        self,
        yaml_content: str,
        *,
        import_only_referenced_components: bool,
    ) -> Union[Component, Dict[str, Component]]: ...

    @overload
    def from_yaml(
        self,
        yaml_content: str,
        components_registry: Optional[ComponentsRegistryT],
        import_only_referenced_components: Literal[False],
    ) -> Component: ...

    @overload
    def from_yaml(
        self,
        yaml_content: str,
        components_registry: Optional[ComponentsRegistryT],
        import_only_referenced_components: Literal[True],
    ) -> Dict[str, Component]: ...

    @overload
    def from_yaml(
        self,
        yaml_content: str,
        components_registry: Optional[ComponentsRegistryT],
        import_only_referenced_components: bool,
    ) -> Union[Component, Dict[str, Component]]: ...

    def from_yaml(
        self,
        yaml_content: str,
        components_registry: Optional[ComponentsRegistryT] = None,
        import_only_referenced_components: bool = False,
    ) -> Union[Component, Dict[str, Component]]:
        """
        Load a component and its sub-components from YAML.

        Parameters
        ----------
        yaml_content:
            The YAML content to use to deserialize the component.
        components_registry:
            A dictionary of loaded components to use when deserializing the
            main component.
        import_only_referenced_components:
            When ``True``, loads the referenced/disaggregated components
            into a dictionary to be used as the ``components_registry``
            when deserializing the main component. Otherwise, loads the
            main component. Defaults to ``False``

        Returns
        -------
        If ``import_only_referenced_components`` is ``False``

        Component
            The deserialized component.

        If ``import_only_referenced_components`` is ``False``

        Dict[str, Component]
            A dictionary containing the loaded referenced components.

        Examples
        --------

        See examples in the ``.from_dict`` method docstring.
        """
        return self.from_dict(
            yaml.safe_load(yaml_content),
            components_registry=components_registry,
            import_only_referenced_components=import_only_referenced_components,
        )

    @overload
    def from_json(self, json_content: str) -> Component:
        """Load a component and its sub-components from JSON."""

    @overload
    def from_json(
        self,
        json_content: str,
        components_registry: Optional[ComponentsRegistryT],
    ) -> Component: ...

    @overload
    def from_json(
        self,
        json_content: str,
        *,
        import_only_referenced_components: Literal[False],
    ) -> Component: ...

    @overload
    def from_json(
        self,
        json_content: str,
        *,
        import_only_referenced_components: Literal[True],
    ) -> Dict[str, Component]: ...

    @overload
    def from_json(
        self,
        json_content: str,
        *,
        import_only_referenced_components: bool,
    ) -> Union[Component, Dict[str, Component]]: ...

    @overload
    def from_json(
        self,
        json_content: str,
        components_registry: Optional[ComponentsRegistryT],
        import_only_referenced_components: Literal[False],
    ) -> Component: ...

    @overload
    def from_json(
        self,
        json_content: str,
        components_registry: Optional[ComponentsRegistryT],
        import_only_referenced_components: Literal[True],
    ) -> Dict[str, Component]: ...

    @overload
    def from_json(
        self,
        json_content: str,
        components_registry: Optional[ComponentsRegistryT],
        import_only_referenced_components: bool,
    ) -> Union[Component, Dict[str, Component]]: ...

    def from_json(
        self,
        json_content: str,
        components_registry: Optional[ComponentsRegistryT] = None,
        import_only_referenced_components: bool = False,
    ) -> Union[Component, Dict[str, Component]]:
        """
        Load a component and its sub-components from JSON.

        Parameters
        ----------
        json_content:
            The JSON content to use to deserialize the component.
        components_registry:
            A dictionary of loaded components to use when deserializing the
            main component.
        import_only_referenced_components:
            When ``True``, loads the referenced/disaggregated components
            into a dictionary to be used as the ``components_registry``
            when deserializing the main component. Otherwise, loads the
            main component. Defaults to ``False``

        Returns
        -------
        If ``import_only_referenced_components`` is ``False``

        Component
            The deserialized component.

        If ``import_only_referenced_components`` is ``False``

        Dict[str, Component]
            A dictionary containing the loaded referenced components.

        Examples
        --------

        See examples in the ``.from_dict`` method docstring.
        """
        return self.from_dict(
            json.loads(json_content),
            components_registry=components_registry,
            import_only_referenced_components=import_only_referenced_components,
        )

    @overload
    def from_dict(self, dict_content: ComponentAsDictT) -> Component: ...

    @overload
    def from_dict(
        self,
        dict_content: ComponentAsDictT,
        components_registry: ComponentsRegistryT | None,
    ) -> Component: ...

    @overload
    def from_dict(
        self,
        dict_content: ComponentAsDictT,
        *,
        import_only_referenced_components: Literal[False],
    ) -> Component: ...

    @overload
    def from_dict(
        self,
        dict_content: ComponentAsDictT,
        *,
        import_only_referenced_components: Literal[True],
    ) -> dict[str, Component]: ...

    @overload
    def from_dict(
        self,
        dict_content: ComponentAsDictT,
        *,
        import_only_referenced_components: bool,
    ) -> Component | dict[str, Component]: ...

    @overload
    def from_dict(
        self,
        dict_content: ComponentAsDictT,
        components_registry: ComponentsRegistryT | None,
        import_only_referenced_components: Literal[False],
    ) -> Component: ...

    @overload
    def from_dict(
        self,
        dict_content: ComponentAsDictT,
        components_registry: ComponentsRegistryT | None,
        import_only_referenced_components: Literal[True],
    ) -> dict[str, Component]: ...

    @overload
    def from_dict(
        self,
        dict_content: ComponentAsDictT,
        components_registry: Optional[ComponentsRegistryT],
        import_only_referenced_components: bool,
    ) -> Component | dict[str, Component]: ...

    def from_dict(
        self,
        dict_content: ComponentAsDictT,
        components_registry: ComponentsRegistryT | None = None,
        import_only_referenced_components: bool = False,
    ) -> Component | dict[str, Component]:
        """
        Load a component and its sub-components from dictionary.

        Parameters
        ----------
        dict_content:
            The loaded serialized component representation as a dictionary.
        components_registry:
            A dictionary of loaded components to use when deserializing the
            main component.
        import_only_referenced_components:
            When ``True``, loads the referenced/disaggregated components
            into a dictionary to be used as the ``components_registry``
            when deserializing the main component. Otherwise, loads the
            main component. Defaults to ``False``

        Returns
        -------
        If ``import_only_referenced_components`` is ``False``

        Component
            The deserialized component.

        If ``import_only_referenced_components`` is ``False``

        Dict[str, Component]
            A dictionary containing the loaded referenced components.

        Examples
        --------
        Basic deserialization is done as follows. First, serialize a component (here an ``Agent``).

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

        Then deserialize using the ``AgentSpecDeserializer``.

        >>> from pyagentspec.serialization import AgentSpecDeserializer
        >>> deser_agent = AgentSpecDeserializer().from_dict(agent_config)

        When using disaggregated components, the deserialization must be done
        in several phases, as follows.

        >>> agent_config, disag_config = AgentSpecSerializer().to_dict(
        ...     component=agent,
        ...     disaggregated_components=[(llm, "custom_llm_id")],
        ...     export_disaggregated_components=True,
        ... )
        >>> disag_components = AgentSpecDeserializer().from_dict(
        ...     disag_config,
        ...     import_only_referenced_components=True
        ... )
        >>> deser_agent = AgentSpecDeserializer().from_dict(
        ...     agent_config,
        ...     components_registry=disag_components
        ... )

        """
        self._check_missing_component_references(dict_content, components_registry)
        all_keys = set(dict_content.keys())
        if not import_only_referenced_components:
            # Loading as a Main Component
            if all_keys == {"$referenced_components"}:
                raise ValueError(
                    "Cannot deserialize the given content, it doesn't seem to be a "
                    "valid Agent Spec Component. To load a disaggregated configuration, "
                    "make sure that `import_only_referenced_components` is `True`"
                )
            main_deserialization_context = _DeserializationContextImpl(
                plugins=self.plugins, partial_model_build=False
            )
            return main_deserialization_context.load_config_dict(
                dict_content, components_registry=components_registry
            )[0]

        # Else, loading the disaggregated components
        if "$referenced_components" not in all_keys:
            raise ValueError(
                "Disaggregated component config should have the "
                "'$referenced_components' field, but it is missing. "
                "Make sure that you are passing the disaggregated config."
            )
        if all_keys != {"$referenced_components"}:
            raise ValueError(
                "Found extra fields on disaggregated components configuration: "
                "Disaggregated components configuration should "
                "only have the '$referenced_components' field, but "
                f"got fields: {all_keys}"
            )
        referenced_components: Dict[str, Component] = {}
        for component_id, component_as_dict in dict_content["$referenced_components"].items():
            disag_deserialization_context = _DeserializationContextImpl(
                plugins=self.plugins, partial_model_build=False
            )
            referenced_components[component_id] = disag_deserialization_context.load_config_dict(
                component_as_dict, components_registry=components_registry
            )[0]

        return referenced_components

    @overload
    def from_partial_dict(
        self,
        dict_content: ComponentAsDictT,
    ) -> tuple[Component, list[PyAgentSpecErrorDetails]]: ...

    @overload
    def from_partial_dict(
        self,
        dict_content: ComponentAsDictT,
        components_registry: ComponentsRegistryT | None,
    ) -> tuple[Component, list[PyAgentSpecErrorDetails]]: ...

    @overload
    def from_partial_dict(
        self,
        dict_content: ComponentAsDictT,
        *,
        import_only_referenced_components: Literal[False],
    ) -> tuple[Component, list[PyAgentSpecErrorDetails]]: ...

    @overload
    def from_partial_dict(
        self,
        dict_content: ComponentAsDictT,
        *,
        import_only_referenced_components: Literal[True],
    ) -> tuple[dict[str, Component], list[PyAgentSpecErrorDetails]]: ...

    @overload
    def from_partial_dict(
        self,
        dict_content: ComponentAsDictT,
        *,
        import_only_referenced_components: bool,
    ) -> tuple[Component | dict[str, Component], list[PyAgentSpecErrorDetails]]: ...

    @overload
    def from_partial_dict(
        self,
        dict_content: ComponentAsDictT,
        components_registry: ComponentsRegistryT | None,
        import_only_referenced_components: Literal[False],
    ) -> tuple[Component, list[PyAgentSpecErrorDetails]]: ...

    @overload
    def from_partial_dict(
        self,
        dict_content: ComponentAsDictT,
        components_registry: ComponentsRegistryT | None,
        import_only_referenced_components: Literal[True],
    ) -> tuple[dict[str, Component], list[PyAgentSpecErrorDetails]]: ...

    @overload
    def from_partial_dict(
        self,
        dict_content: ComponentAsDictT,
        components_registry: ComponentsRegistryT | None = None,
        import_only_referenced_components: bool = False,
    ) -> tuple[Component | dict[str, Component], list[PyAgentSpecErrorDetails]]: ...

    def from_partial_dict(
        self,
        dict_content: ComponentAsDictT,
        components_registry: Optional[ComponentsRegistryT] = None,
        import_only_referenced_components: bool = False,
    ) -> Tuple[Union[Component, Dict[str, Component]], List[PyAgentSpecErrorDetails]]:
        all_keys = set(dict_content.keys())
        if not import_only_referenced_components:
            # Loading as a Main Component
            if all_keys == {"$referenced_components"}:
                raise ValueError(
                    "Cannot deserialize the given content, it doesn't seem to be a "
                    "valid Agent Spec Component. To load a disaggregated configuration, "
                    "make sure that `import_only_referenced_components` is `True`"
                )
            main_deserialization_context = _DeserializationContextImpl(
                plugins=self.plugins, partial_model_build=True
            )
            return main_deserialization_context.load_config_dict(
                dict_content, components_registry=components_registry
            )

        # Else, loading the disaggregated components
        if "$referenced_components" not in all_keys:
            raise ValueError(
                "Disaggregated component config should have the "
                "'$referenced_components' field, but it is missing. "
                "Make sure that you are passing the disaggregated config."
            )
        if all_keys != {"$referenced_components"}:
            raise ValueError(
                "Found extra fields on disaggregated components configuration: "
                "Disaggregated components configuration should "
                "only have the '$referenced_components' field, but "
                f"got fields: {all_keys}"
            )
        referenced_components: Dict[str, Component] = {}
        all_validation_errors: List[PyAgentSpecErrorDetails] = []
        for component_id, component_as_dict in dict_content["$referenced_components"].items():
            disag_deserialization_context = _DeserializationContextImpl(
                plugins=self.plugins, partial_model_build=True
            )
            referenced_components[component_id], validation_errors = (
                disag_deserialization_context.load_config_dict(
                    component_as_dict, components_registry=components_registry
                )
            )
            all_validation_errors.extend(validation_errors)

        return referenced_components, all_validation_errors

    @staticmethod
    def _check_missing_component_references(
        dict_content: ComponentAsDictT, components_registry: Optional[ComponentsRegistryT] = None
    ) -> None:
        """
        Check that all references that are part of the dict_content are either defined in
        dict_content["$referenced_components"] or are present in the components_registry.
        If any references is not defined an error is raised.
        """
        all_used_references, all_defined_references = (
            AgentSpecDeserializer._recursively_get_all_references(dict_content)
        )
        all_defined_references.update(set((components_registry or {}).keys()))
        missing_references = [
            ref for ref in all_used_references if ref not in all_defined_references
        ]
        if missing_references:
            raise ValueError(
                "The following references to fields or components are missing and should be passed"
                " as part of the component registry when deserializing: "
                f"{sorted(list(missing_references))}"
            )

    @staticmethod
    def _recursively_get_all_references(value: Dict[str, Any]) -> Tuple[Set[str], Set[str]]:
        """
        This method recursively traverses the content of `value` and collects all the references
        used that appear as `{"$component_ref": "some_component_id"}` and all the references that
        are defined in the content as part of the nested `"$referenced_components"`.
        """
        used_references, defined_references = set(), set()
        visited = {id(value)}
        exploration_stack: List[Dict[str, Any] | List[Any]] = [value]
        while exploration_stack:
            current_value = exploration_stack.pop()
            if isinstance(current_value, dict) and "$component_ref" in current_value:
                used_references.add(current_value["$component_ref"])
            if isinstance(current_value, dict) and "$referenced_components" in current_value:
                defined_references.update(set(current_value["$referenced_components"]))

            nested_values = (
                current_value.values() if isinstance(current_value, dict) else current_value
            )
            for nested_value in nested_values:
                if isinstance(nested_value, (dict, list)) and id(nested_value) not in visited:
                    visited.add(id(nested_value))
                    exploration_stack.append(nested_value)

        return used_references, defined_references
