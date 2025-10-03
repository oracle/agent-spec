# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.


"""
Define the AgentSpecDeserializer class.

The class provides entry points to read Agent Spec from a serialized form.
"""

import json
from typing import Dict, List, Literal, Optional, Union, overload

import yaml

from pyagentspec.component import Component
from pyagentspec.serialization.deserializationcontext import _DeserializationContextImpl
from pyagentspec.serialization.deserializationplugin import ComponentDeserializationPlugin
from pyagentspec.serialization.types import ComponentAsDictT, ComponentsRegistryT


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
        components_registry: Optional[ComponentsRegistryT],
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
    ) -> Dict[str, Component]: ...

    @overload
    def from_dict(
        self,
        dict_content: ComponentAsDictT,
        *,
        import_only_referenced_components: bool,
    ) -> Union[Component, Dict[str, Component]]: ...

    @overload
    def from_dict(
        self,
        dict_content: ComponentAsDictT,
        components_registry: Optional[ComponentsRegistryT],
        import_only_referenced_components: Literal[False],
    ) -> Component: ...

    @overload
    def from_dict(
        self,
        dict_content: ComponentAsDictT,
        components_registry: Optional[ComponentsRegistryT],
        import_only_referenced_components: Literal[True],
    ) -> Dict[str, Component]: ...

    @overload
    def from_dict(
        self,
        dict_content: ComponentAsDictT,
        components_registry: Optional[ComponentsRegistryT],
        import_only_referenced_components: bool,
    ) -> Union[Component, Dict[str, Component]]: ...

    def from_dict(
        self,
        dict_content: ComponentAsDictT,
        components_registry: Optional[ComponentsRegistryT] = None,
        import_only_referenced_components: bool = False,
    ) -> Union[Component, Dict[str, Component]]:
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
        all_keys = set(dict_content.keys())
        if not import_only_referenced_components:
            # Loading as a Main Component
            if all_keys == {"$referenced_components"}:
                raise ValueError(
                    "Cannot deserialize the given content, it doesn't seem to be a "
                    "valid Agent Spec Component. To load a disaggregated configuration, "
                    "make sure that `import_only_referenced_components` is `True`"
                )
            main_deserialization_context = _DeserializationContextImpl(plugins=self.plugins)
            return main_deserialization_context._load_from_dict(
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
        for component_id, component_as_dict in dict_content["$referenced_components"].items():
            disag_deserialization_context = _DeserializationContextImpl(plugins=self.plugins)
            referenced_components[component_id] = disag_deserialization_context._load_from_dict(
                component_as_dict, components_registry=components_registry
            )

        return referenced_components
