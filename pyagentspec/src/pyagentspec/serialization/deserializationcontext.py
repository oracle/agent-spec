# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Define the classes and utilities related to deserialization of Agent Spec configurations."""

import inspect
import types
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
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel, ValidationError
from typing_extensions import TypeGuard

from pyagentspec.component import Component
from pyagentspec.property import Property
from pyagentspec.serialization.types import (
    BaseModelAsDictT,
    ComponentAsDictT,
    ComponentsRegistryT,
    LoadedReferencesT,
    _DeserializationInProgressMarker,
)
from pyagentspec.versioning import (
    _LEGACY_VERSION_FIELD_NAME,
    _PRERELEASE_AGENTSPEC_VERSIONS,
    AGENTSPEC_VERSION_FIELD_NAME,
    AgentSpecVersionEnum,
)

from ..validation_helpers import PyAgentSpecErrorDetails

if TYPE_CHECKING:
    from pyagentspec.serialization.deserializationplugin import ComponentDeserializationPlugin


class DeserializationContext(ABC):
    """Interface for the deserialization of Components."""

    @abstractmethod
    def get_component_type(self, content: Dict[str, Any]) -> str:
        """Get the type of component from the dedicated special field."""

    @abstractmethod
    def load_config_dict(
        self,
        content: ComponentAsDictT,
        components_registry: Optional[ComponentsRegistryT],
    ) -> Tuple[Component, List[PyAgentSpecErrorDetails]]:
        """Load an Agent Spec configuration in dictionary form."""

    @abstractmethod
    def load_field(
        self,
        content: BaseModelAsDictT,
        annotation: Optional[type],
    ) -> Any:
        """Load a field based on its serialized field content and annotated type."""

    def _partial_load_field(
        self,
        content: BaseModelAsDictT,
        annotation: Optional[type],
    ) -> Tuple[Any, List[PyAgentSpecErrorDetails]]:
        """Load a field based on its serialized field content and annotated type, allowing incomplete configurations."""
        raise NotImplementedError(
            "Partial configuration deserialization is not implemented in this Context class"
        )


class _DeserializationContextImpl(DeserializationContext):
    def __init__(
        self,
        plugins: Optional[List["ComponentDeserializationPlugin"]] = None,
        partial_model_build: bool = False,
    ) -> None:

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
        self.partial_model_build = partial_model_build

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

    def _load_reference(
        self, reference_id: str, annotation: Optional[type] = None
    ) -> Tuple[Any, List[PyAgentSpecErrorDetails]]:
        validation_errors: List[PyAgentSpecErrorDetails] = []
        if reference_id not in self.loaded_references:
            self.loaded_references[reference_id] = _DeserializationInProgressMarker()
            if self.referenced_components is None:
                raise ValueError("No reference components to load from")
            if reference_id not in self.referenced_components:
                raise KeyError(f"Missing reference for ID: {reference_id}")
            ref_content = self.referenced_components[reference_id]
            self.loaded_references[reference_id], validation_errors = (
                self._load_component_from_dict(ref_content)
            )

        loaded_reference = self.loaded_references[reference_id]
        if isinstance(loaded_reference, _DeserializationInProgressMarker):
            raise ValueError(
                f"Found a circular dependency during deserialization of object with id: "
                f"'{reference_id}'"
            )
        if (
            annotation
            and isinstance(annotation, type)
            and issubclass(annotation, Component)
            and not isinstance(loaded_reference, annotation)
        ):
            raise ValueError(
                f"Type mismatch when loading component with reference '{reference_id}': expected "
                f"'{annotation.__name__}', got '{loaded_reference.__class__.__name__}'. "
                "If using a component registry, make sure that the components are correct."
            )
        return loaded_reference, validation_errors

    def load_field(
        self,
        content: BaseModelAsDictT,
        annotation: Optional[type],
    ) -> Any:
        return self._load_field(content=content, annotation=annotation)[0]

    def _partial_load_field(
        self,
        content: BaseModelAsDictT,
        annotation: Optional[type],
    ) -> Tuple[Any, List[PyAgentSpecErrorDetails]]:
        return self._load_field(content=content, annotation=annotation)

    def _load_field(
        self,
        content: BaseModelAsDictT,
        annotation: Optional[type],
    ) -> Tuple[Any, List[PyAgentSpecErrorDetails]]:
        # Some field may be disaggregated and available from the component registry. the condition
        # below handles such fields.
        if isinstance(content, dict) and "$component_ref" in content:
            return self._load_reference(content["$component_ref"], annotation=annotation)

        origin_type = get_origin(annotation)

        if origin_type is Annotated:
            inner_annotation, _ = get_args(annotation)
            return self._load_field(content, inner_annotation)

        if origin_type is None:
            # might be None when we have a primitive type, or the type of a component
            if self._is_component_type(annotation):
                # if it is already a component instance, we just return it
                if annotation and isinstance(content, annotation):
                    return content, []

                # if it is a component, we might have refs
                if not isinstance(content, dict):
                    raise ValueError(
                        "expected the content to be a dictionary, "
                        f"but got {type(content).__name__}"
                    )
                return self._load_component_from_dict(content, annotation)
            elif (
                annotation is not None
                and inspect.isclass(annotation)
                and issubclass(annotation, Property)
            ):
                if isinstance(content, Property):
                    # already an instantiated property (e.g. partial config)
                    return content, []
                return Property(json_schema=content), []
            elif self._is_pydantic_type(annotation):
                return self._load_pydantic_model_from_dict(content, annotation)
            elif inspect.isclass(annotation) and issubclass(annotation, Enum):
                return annotation(content), []
            return content, []

        if origin_type == dict:
            dict_key_annotation, dict_value_annotation = get_args(annotation)
            if dict_key_annotation != str:
                raise ValueError("only dict with str keys are supported")

            if not isinstance(content, dict):
                raise ValueError(
                    f"expected the content to be a dictionary, but got {type(content).__name__}"
                )
            result_dictionary = dict()
            all_validation_errors = []
            for k, v in content.items():
                result_dictionary[k], nested_validation_errors = self._load_field(
                    v, dict_value_annotation
                )
                all_validation_errors.extend(
                    [
                        PyAgentSpecErrorDetails(
                            type=nested_error_details.type,
                            msg=nested_error_details.msg,
                            loc=(k, *nested_error_details.loc),
                        )
                        for nested_error_details in nested_validation_errors
                    ]
                )
            return result_dictionary, all_validation_errors

        elif origin_type in {list, set, tuple}:
            list_value_annotation = get_args(annotation)
            if isinstance(list_value_annotation, tuple):
                list_value_annotation = list_value_annotation[0]

            if not (isinstance(content, origin_type) or isinstance(content, list)):
                raise ValueError(
                    f"Expected the content to be {origin_type}, but got {type(content).__name__}"
                )

            result_list = list()
            all_validation_errors = []
            for i, v in enumerate(content):
                loaded_value, nested_validation_errors = self._load_field(v, list_value_annotation)  # type: ignore
                result_list.append(loaded_value)
                all_validation_errors.extend(
                    [
                        PyAgentSpecErrorDetails(
                            type=nested_error_details.type,
                            msg=nested_error_details.msg,
                            loc=(i, *nested_error_details.loc),
                        )
                        for nested_error_details in nested_validation_errors
                    ]
                )
            return origin_type(result_list), all_validation_errors
        elif origin_type == Union or origin_type == types.UnionType:

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
                    return None, []
                inner_annotations.remove(type(None))

            # Try to deserialize components/pydantic models according to any of the annotations
            # If any of them works, we will proceed with that. This is our best effort.
            for inner_annotation in inner_annotations:
                try:
                    return self._load_field(content, inner_annotation)
                except ValueError:
                    # Something went wrong in deserialization,
                    # it's not the right type, we try the next one
                    pass

            # We tried all the components and pydantic models, and it did not work out,
            # only python type is left. If it is only normal python types, just return the content
            if self._is_python_type(annotation):
                return content, []
            else:
                # If even python type fails, then we do not support this,
                # or there's an error in the representation
                raise ValueError(
                    f"It looks like the annotation {annotation} is a mix of"
                    f" python and Agent Spec types which is not supported."
                )
        elif origin_type == Literal:
            return content, []

        raise ValueError(
            f"It looks like we don't support annotation {annotation} "
            f"(origin {origin_type}, content {content})"
        )

    def _load_pydantic_model_from_dict(
        self,
        content: BaseModelAsDictT,
        model_class: Type[BaseModel],
    ) -> Tuple[BaseModel, List[PyAgentSpecErrorDetails]]:
        resolved_content: BaseModelAsDictT = {}
        all_validation_errors: List[PyAgentSpecErrorDetails] = []
        for field_name, field_info in model_class.model_fields.items():
            annotation = field_info.annotation
            if field_name in content:
                resolved_content[field_name], nested_validation_errors = self._load_field(
                    content[field_name], annotation
                )
                all_validation_errors.extend(
                    [
                        PyAgentSpecErrorDetails(
                            type=nested_error_details.type,
                            msg=nested_error_details.msg,
                            loc=(field_name, *nested_error_details.loc),
                        )
                        for nested_error_details in nested_validation_errors
                    ]
                )
        # If the pydantic model allows extra attributes, we load them
        if model_class.model_config.get("extra", "deny") == "allow":
            for content_key, content_value in content.items():
                if content_key not in resolved_content:
                    resolved_content[content_key], nested_validation_errors = self._load_field(
                        content_value, type(content_value)
                    )
                    all_validation_errors.extend(
                        [
                            PyAgentSpecErrorDetails(
                                type=nested_error_details.type,
                                msg=nested_error_details.msg,
                                loc=(content_key, *nested_error_details.loc),
                            )
                            for nested_error_details in nested_validation_errors
                        ]
                    )
        # We try to build the BaseModel
        try:
            return model_class(**resolved_content), all_validation_errors
        except ValidationError as e:
            # if we fail due to validation, and we are ok with partial build, we do partial build and return the errors
            if self.partial_model_build:
                all_validation_errors += [
                    PyAgentSpecErrorDetails(**error_details)  # type: ignore
                    for error_details in e.errors()
                ]
                return model_class.model_construct(**resolved_content), all_validation_errors
            # If we are not ok with partial build, we forward the exception
            raise e

    def _load_component_with_plugin(
        self,
        plugin: "ComponentDeserializationPlugin",
        content: ComponentAsDictT,
    ) -> Tuple[Component, List[PyAgentSpecErrorDetails]]:
        if not self._agentspec_version:
            raise ValueError(
                "Internal error: `_agentspec_version is not specified. "
                "Make sure that `load_config_dict` is called."
            )
        agentspec_version = self._agentspec_version

        if self.partial_model_build:
            component, validation_errors = plugin._partial_deserialize(
                serialized_component=content, deserialization_context=self
            )
        else:
            validation_errors = []
            component = plugin.deserialize(
                serialized_component=content, deserialization_context=self
            )

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
        return component, validation_errors

    def _load_component_from_dict(
        self,
        content: ComponentAsDictT,
        annotation: Optional[type] = None,
    ) -> Tuple[Component, List[PyAgentSpecErrorDetails]]:

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
            return self._load_reference(content["$component_ref"], annotation)

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
        if components_registry is not None:
            self.loaded_references.update(components_registry)

    def load_config_dict(
        self,
        content: ComponentAsDictT,
        components_registry: Optional[ComponentsRegistryT],
    ) -> Tuple[Component, List[PyAgentSpecErrorDetails]]:
        if (
            AGENTSPEC_VERSION_FIELD_NAME not in content
            and _LEGACY_VERSION_FIELD_NAME not in content
        ):
            warnings.warn(
                "Missing `agentspec_version` field at the top level of the configuration. "
                f"The current Agent Spec version {AgentSpecVersionEnum.current_version} will be used.\n"
                "Note that leaving this unset may cause the configuration to fail in newer versions.",
                UserWarning,
            )
            self._agentspec_version = AgentSpecVersionEnum.current_version
        else:
            self._agentspec_version = AgentSpecVersionEnum(
                value=content.get(
                    AGENTSPEC_VERSION_FIELD_NAME, content.get(_LEGACY_VERSION_FIELD_NAME)
                )
            )

        if (
            self._agentspec_version
            and self._agentspec_version.value in _PRERELEASE_AGENTSPEC_VERSIONS
        ):
            warnings.warn(
                "Using a pre-release `agentspec_version`, deserialization will be performed using the "
                "first official version of Agent Spec (25.4.1) instead. Please update your representation.",
                UserWarning,
            )
            self._agentspec_version = AgentSpecVersionEnum.v25_4_1

        self._load_component_registry(components_registry)
        # the top level object has to be a component, this method will check for that
        component, validation_errors = self._load_component_from_dict(content)

        self._agentspec_version = None
        return component, validation_errors
