# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""Define the classes and utilities related to deserialization of Agent Spec configurations."""

import inspect
import warnings
from abc import ABC, abstractmethod
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel
from typing_extensions import TypeGuard

from pyagentspec.component import Component
from pyagentspec.property import Property
from pyagentspec.versioning import (
    _LEGACY_VERSION_FIELD_NAME,
    AGENTSPEC_VERSION_FIELD_NAME,
    AgentSpecVersionEnum,
)

from .types import (
    BaseModelAsDictT,
    ComponentAsDictT,
    ComponentsRegistryT,
    LoadedReferencesT,
    _DeserializationInProgressMarker,
)

if TYPE_CHECKING:
    from pyagentspec.serialization.deserializationplugin import ComponentDeserializationPlugin


class DeserializationContext(ABC):
    """Interface for the deserialization of Components."""

    @abstractmethod
    def get_component_type(self, content: Dict[str, Any]) -> str:
        """Get the type of a component from the dedicated special field."""
        pass

    @abstractmethod
    def load_field(
        self,
        content: BaseModelAsDictT,
        annotation: Optional[type],
    ) -> Any:
        """Load a field based on its serialized field content and annotated type."""
        pass


class _DeserializationContextImpl(DeserializationContext):
    def __init__(self, plugins: Optional[List["ComponentDeserializationPlugin"]] = None) -> None:

        self.plugins = list(plugins) if plugins is not None else []

        # Add the deserialization plugin that loads all builtin Agent Spec components
        # All other components must be loaded by custom components
        from pyagentspec.serialization.builtinsdeserializationplugin import (
            BuiltinsComponentDeserializationPlugin,
        )

        self.plugins.append(BuiltinsComponentDeserializationPlugin())

        self.component_types_to_plugins = self._build_component_types_to_plugins(self.plugins)

        # TODO: do a better job at creating sub-deserialization contexts to not pollute
        # loaded references
        self.loaded_references: LoadedReferencesT = {}
        self.referenced_components: Dict[str, ComponentAsDictT] = {}
        self._agentspec_version: Optional[AgentSpecVersionEnum] = None

    def _build_component_types_to_plugins(
        self, plugins: List["ComponentDeserializationPlugin"]
    ) -> Dict[str, "ComponentDeserializationPlugin"]:
        all_handled_component_types = [
            component_type
            for plugin in plugins
            for component_type in plugin.supported_component_types()
        ]

        # check if several plugins are handling the same type
        if len(set(all_handled_component_types)) < len(all_handled_component_types):
            # we have a collision

            # first establish all plugins handling each component
            component_type_collisions: Dict[str, List[ComponentDeserializationPlugin]] = {}
            for plugin in plugins:
                for component_type in plugin.supported_component_types():
                    plugins_for_type = component_type_collisions.get(component_type, [])
                    plugins_for_type.append(plugin)

                    component_type_collisions[component_type] = plugins_for_type

            # only keep the entries with actual collisions
            component_type_collisions = {
                component_type: plugins
                for component_type, plugins in component_type_collisions.items()
                if len(plugins) > 1
            }

            # report collisions
            collisions_str = {
                component_type: [str(plugin) for plugin in plugins]
                for component_type, plugins in component_type_collisions.items()
            }
            raise ValueError(
                "Several plugins are handling the deserialization of the same types: "
                f"{collisions_str}. Please remove the problematic plugins."
            )

        # return the map component_type -> plugin (known to have only one plugin per component type)
        return {
            component_type: plugin
            for plugin in plugins
            for component_type in plugin.supported_component_types()
        }

    def _is_python_primitive_type(self, annotation: Optional[type]) -> bool:
        if annotation is None:
            return False
        return issubclass(annotation, (bool, int, float, str))

    def _is_python_type(self, annotation: Optional[type]) -> bool:
        origin_type = get_origin(annotation)

        if origin_type is None:
            return True
        if origin_type == dict:
            dict_key_annotation, dict_value_annotation = get_args(annotation)
            return self._is_python_type(dict_key_annotation) and self._is_python_type(
                dict_value_annotation
            )
        elif origin_type == list or origin_type == set:
            (list_value_annotation,) = get_args(annotation)
            return self._is_python_type(list_value_annotation)
        elif origin_type == set:
            (set_value_annotation,) = get_args(annotation)
            return self._is_python_type(set_value_annotation)
        elif origin_type == Union:
            return all(self._is_python_type(t) for t in get_args(annotation))
        else:
            return self._is_python_primitive_type(annotation)

    def _is_pydantic_type(self, annotation: Optional[type]) -> TypeGuard[Type[BaseModel]]:
        try:
            return issubclass(annotation, BaseModel) if annotation is not None else False
        except TypeError:
            # If annotation is not a type, like a typing type, a TypeError is raised
            # Automatically, this means that they are not subclasses of BaseModel
            return False

    def _is_optional_type(self, annotation: Optional[type]) -> bool:
        origin_type = get_origin(annotation)
        if origin_type is not Union:
            return False
        inner_annotations = get_args(annotation)
        return type(None) in inner_annotations

    def _is_component_type(self, annotation: Optional[type]) -> bool:
        try:
            return issubclass(annotation, Component) if annotation is not None else False
        except TypeError:
            # If annotation is not a type, like a typing type, a TypeError is raised
            # Automatically, this means that they are not subclasses of Component
            return False

    def get_component_type(self, content: Dict[str, Any]) -> str:
        # Make sure we have a component, and determine its type
        component_type = content.get("component_type", None)

        if component_type is None:
            raise ValueError(
                "Cannot deserialize the given content, it doesn't seem to be a "
                + f"valid Agent Spec Component: {content}. Missing property 'component_type'."
            )

        if not isinstance(component_type, str):
            raise ValueError("component_type is not a string as expected")

        return component_type

    def _get_component_class(self, component_type: str) -> Type[Component]:

        component_class = Component.get_class_from_name(component_type)
        if component_class is None:
            raise ValueError(f"Unknown Agent Spec Component type {component_type}")
        return component_class

    def _load_reference(self, reference_id: str) -> Component:
        if reference_id not in self.loaded_references:
            self.loaded_references[reference_id] = _DeserializationInProgressMarker()
            if self.referenced_components is None:
                raise ValueError("No reference components to load from")
            if reference_id not in self.referenced_components:
                raise KeyError(f"Missing reference for ID: {reference_id}")
            ref_content = self.referenced_components[reference_id]
            self.loaded_references[reference_id] = self._load_component_from_dict(ref_content)

        loaded_reference = self.loaded_references[reference_id]
        if isinstance(loaded_reference, _DeserializationInProgressMarker):
            raise ValueError(
                f"Found a circular dependency during deserialization of object with id: "
                f"'{reference_id}'"
            )
        else:
            return loaded_reference

    def load_field(
        self,
        content: BaseModelAsDictT,
        annotation: Optional[type],
    ) -> Any:
        return self._load_field(content=content, annotation=annotation)

    def _load_field(
        self,
        content: BaseModelAsDictT,
        annotation: Optional[type],
    ) -> Any:
        origin_type = get_origin(annotation)

        if origin_type is Annotated:
            inner_annotation, _ = get_args(annotation)
            return self._load_field(content, inner_annotation)

        if origin_type is None:
            # might be None when we have a primitive type, or the type of a component
            if self._is_component_type(annotation):
                # if it is a component, we might have refs
                return self._load_component_from_dict(content, annotation)
            elif annotation is not None and issubclass(annotation, Property):
                return Property(json_schema=content)
            elif self._is_pydantic_type(annotation):
                return self._load_pydantic_model_from_dict(content, annotation)
            elif inspect.isclass(annotation) and issubclass(annotation, Enum):
                return annotation(content)
            return content

        if origin_type == dict:
            dict_key_annotation, dict_value_annotation = get_args(annotation)
            if dict_key_annotation != str:
                raise ValueError("only dict with str keys are supported")

            if not isinstance(content, dict):
                raise ValueError(
                    f"expected the content to be a dictionary, but got {type(content).__name__}"
                )

            return {k: self._load_field(v, dict_value_annotation) for k, v in content.items()}

        elif origin_type == list or origin_type == set:
            (list_value_annotation,) = get_args(annotation)

            if not isinstance(content, origin_type):
                raise ValueError(
                    f"Expected the content to be {origin_type}, but got {type(content).__name__}"
                )

            return origin_type(self._load_field(v, list_value_annotation) for v in content)
        elif origin_type == Union:

            # order-preserving deduplicated list
            inner_annotations = list(dict.fromkeys(get_args(annotation)))

            if str in inner_annotations:
                # best-effort: if `str` in inner annotations, try to deserialize with all other types before
                inner_annotations.remove(str)
                inner_annotations.append(str)

            # The Optional is interpreted as Union[Type[None], Type]
            # Therefore, we must isolate this case to make the type inference work as intended
            if self._is_optional_type(annotation):
                if content is None:
                    return None
                inner_annotations.remove(type(None))

            # Try to deserialize components/pydantic models according to any of the annotations
            # If any of them works, we will proceed with that. This is our best effort.
            for inner_annotation in inner_annotations:
                try:
                    return self._load_field(content, inner_annotation)
                except Exception:  # nosec
                    # Something went wrong in deserialization,
                    # it's not the right type, we try the next one
                    pass

            # We tried all the components and pydantic models, and it did not work out,
            # only python type is left. If it is only normal python types, just return the content
            if self._is_python_type(annotation):
                return content
            else:
                # If even python type fails, then we do not support this,
                # or there's an error in the representation
                raise ValueError(
                    f"It looks like the annotation {annotation} is a mix of"
                    f" python and Agent Spec types which is not supported."
                )
        elif origin_type == Literal:
            return content

        raise ValueError(
            f"It looks like we don't support annotation {annotation} "
            f"(origin {origin_type}, content {content})"
        )

    def _load_pydantic_model_from_dict(
        self,
        content: BaseModelAsDictT,
        model_class: Type[BaseModel],
    ) -> BaseModel:
        resolved_content: BaseModelAsDictT = {}
        for field_name, field_info in model_class.model_fields.items():
            annotation = field_info.annotation
            if field_name in content:
                resolved_content[field_name] = self._load_field(content[field_name], annotation)
        # If the pydantic model allows extra attributes, we load them
        if model_class.model_config.get("extra", "deny") == "allow":
            for content_key, content_value in content.items():
                if content_key not in resolved_content:
                    resolved_content[content_key] = self._load_field(
                        content_value, type(content_value)
                    )
        return model_class(**resolved_content)

    def _load_component_with_plugin(
        self,
        plugin: "ComponentDeserializationPlugin",
        content: ComponentAsDictT,
    ) -> Component:
        if not self._agentspec_version:
            raise ValueError(
                "Internal error: `_agentspec_version is not specified. "
                "Make sure that `_load_from_dict` is called."
            )
        agentspec_version = self._agentspec_version

        component = plugin.deserialize(serialized_component=content, deserialization_context=self)

        # Validate air version is allowed
        min_agentspec_version, _min_component = component._get_min_agentspec_version_and_component()
        max_agentspec_version, _max_component = component._get_max_agentspec_version_and_component()
        if agentspec_version < min_agentspec_version:
            raise ValueError(
                f"Invalid agentspec_version: component agentspec_version={agentspec_version} "
                f"but the minimum allowed version is {min_agentspec_version} "
                f"(lower bounded by component '{_min_component.name}')"
            )
        elif agentspec_version > max_agentspec_version:
            raise ValueError(
                f"Invalid agentspec_version: component agentspec_version={agentspec_version} "
                f"but the maximum allowed version is {max_agentspec_version} "
                f"(upper bounded by component '{_max_component.name}')"
            )

        component.min_agentspec_version = agentspec_version
        return component

    def _load_component_from_dict(
        self,
        content: ComponentAsDictT,
        annotation: Optional[type] = None,
    ) -> Component:

        if "$referenced_components" in content:
            new_referenced_components = content["$referenced_components"]
            duplicated_ids = set.intersection(
                set(new_referenced_components), set(self.referenced_components)
            )
            if any(duplicated_ids):
                raise ValueError(
                    f"The objects: '{duplicated_ids}' appear multiple times at different levels in"
                    f" referenced components."
                )
            self.referenced_components.update(new_referenced_components)

        if "$component_ref" in content:
            component_ref = content["$component_ref"]
            cached_component = self._load_reference(component_ref)
            if (
                annotation
                and issubclass(annotation, Component)
                and not isinstance(cached_component, annotation)
            ):
                raise ValueError(
                    f"Type mismatch when loading component with reference '{component_ref}': expected "
                    f"'{annotation.__name__}', got '{cached_component.__class__.__name__}'. "
                    "If using a component registry, make sure that the components are correct."
                )
            return cached_component

        component_type = self.get_component_type(content)

        # get the plugin to use for loading if there is one
        plugin = self.component_types_to_plugins.get(component_type, None)
        if plugin is not None:
            # Load with a plugin if there is one
            return self._load_component_with_plugin(
                plugin=plugin,
                content=content,
            )
        else:
            raise ValueError(f"There is no plugin to load the component type {component_type}")

    def _load_component_registry(
        self,
        components_registry: Optional[ComponentsRegistryT],
    ) -> None:
        if not components_registry:
            return None
        for field_id, config_ in components_registry.items():
            if isinstance(config_, Component):
                self.loaded_references[field_id] = config_
            elif isinstance(config_, tuple) and len(config_) == 2:
                raise NotImplementedError("Component field disaggregation is not supported yet")
            else:
                raise ValueError(
                    f"Type mismatch for ID {field_id}: expected Component, got {type(config_).__name__}"
                )

    def _load_from_dict(
        self,
        content: ComponentAsDictT,
        components_registry: Optional[ComponentsRegistryT],
    ) -> Component:
        if (
            AGENTSPEC_VERSION_FIELD_NAME not in content
            and _LEGACY_VERSION_FIELD_NAME not in content
        ):
            warnings.warn(
                "Missing `agentspec_version` field at the top level of the configuration\n"
                "Leaving this unset may cause the configuration to fail in newer versions",
                UserWarning,
            )
            self._agentspec_version = Component.model_fields["min_agentspec_version"].default
        else:
            self._agentspec_version = AgentSpecVersionEnum(
                value=content.get(
                    AGENTSPEC_VERSION_FIELD_NAME, content.get(_LEGACY_VERSION_FIELD_NAME)
                )
            )

        self._load_component_registry(components_registry)
        # the top level object has to be a component, this method will check for that
        component = self._load_component_from_dict(content)

        self._agentspec_version = None
        return component
