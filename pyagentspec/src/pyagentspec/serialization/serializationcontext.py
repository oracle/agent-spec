# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the classes related to serialization of Agent Spec configurations."""
from abc import abstractmethod
from collections import Counter
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
    overload,
)

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from typing_extensions import TypeGuard

from pyagentspec.component import Component
from pyagentspec.versioning import AGENTSPEC_VERSION_FIELD_NAME, AgentSpecVersionEnum

from .types import ComponentAsDictT, WatchingDict

if TYPE_CHECKING:
    from pyagentspec.serialization.serializationplugin import ComponentSerializationPlugin


T = TypeVar("T", bound=Any)
FieldInfoTypeT = TypeVar("FieldInfoTypeT", bound=Any)


class SerializationContext:
    """Interface for the serialization of Components."""

    agentspec_version: AgentSpecVersionEnum

    @abstractmethod
    def _dump_component_to_dict(self, component: Component) -> ComponentAsDictT:
        pass

    @overload
    def dump_field(self, value: bool, info: Optional[FieldInfoTypeT]) -> bool:
        pass

    @overload
    def dump_field(self, value: int, info: Optional[FieldInfoTypeT]) -> int:
        pass

    @overload
    def dump_field(self, value: float, info: Optional[FieldInfoTypeT]) -> float:
        pass

    @overload
    def dump_field(self, value: str, info: Optional[FieldInfoTypeT]) -> str:
        pass

    @overload
    def dump_field(self, value: List[T], info: Optional[FieldInfoTypeT]) -> List[Any]:
        pass

    @overload
    def dump_field(self, value: Dict[str, T], info: Optional[FieldInfoTypeT]) -> Dict[str, Any]:
        pass

    @overload
    def dump_field(self, value: BaseModel, info: Optional[FieldInfoTypeT]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def dump_field(
        self,
        value: Union[int, float, bool, str, List[T], Dict[str, T], BaseModel, Component],
        info: Optional[FieldInfoTypeT],
    ) -> Union[int, float, bool, str, List[Any], Dict[str, Any]]:
        """Dump a component field based on its value and optional info."""
        pass


class _SerializationContextImpl(SerializationContext):
    def __init__(
        self,
        plugins: Optional[List["ComponentSerializationPlugin"]] = None,
        resolved_components: Optional[Dict[str, ComponentAsDictT]] = None,
        components_id_mapping: Optional[WatchingDict] = None,
        _allow_partial_model_serialization: bool = False,
    ) -> None:

        self._allow_partial_model_serialization = _allow_partial_model_serialization
        self.plugins = list(plugins) if plugins is not None else []

        from pyagentspec.serialization.builtinserializationplugin import (
            BuiltinsComponentSerializationPlugin,
        )

        self.plugins.append(
            BuiltinsComponentSerializationPlugin(
                _allow_partial_model_serialization=self._allow_partial_model_serialization
            )
        )
        self.component_types_to_plugins = self._build_component_types_to_plugins(self.plugins)
        # To avoid repeating the serialization for the same component multiple times, we
        # store in this mapping the intermediary serializations, using component ids as the keys.
        self._resolved_components: Dict[str, ComponentAsDictT] = resolved_components or {}
        self._referencing_structure: Dict[str, str] = {}
        self._components_id_mapping: WatchingDict = components_id_mapping or WatchingDict()

    def _build_component_types_to_plugins(
        self, plugins: List["ComponentSerializationPlugin"]
    ) -> Dict[str, "ComponentSerializationPlugin"]:
        all_handled_component_types = [
            component_type
            for plugin in plugins
            for component_type in plugin.supported_component_types()
        ]

        # check if several plugins are handling the same type
        if len(set(all_handled_component_types)) < len(all_handled_component_types):
            # we have a collision

            # first establish all plugins handling each component
            component_type_collisions: Dict[str, List[ComponentSerializationPlugin]] = {}
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
                "Several plugins are handling the serialization of the same types: "
                f"{collisions_str}. Please remove the problematic plugins."
            )

        # return the map component_type -> plugin (known to have only one plugin per component type)
        return {
            component_type: plugin
            for plugin in plugins
            for component_type in plugin.supported_component_types()
        }

    def _dump_component_to_dict(self, component: Component) -> ComponentAsDictT:
        component_id = component.id
        mapped_id = self._components_id_mapping.get(component_id, component_id)
        if mapped_id not in self._resolved_components:
            component_type: str = component.component_type  # type: ignore
            # get the plugin to use for loading if there is one
            plugin = self.component_types_to_plugins.get(component_type, None)
            if plugin is None:
                raise ValueError(f"There is no plugin to dump the component type {component_type}")

            component_dump: ComponentAsDictT = self._dump_component_with_plugin(
                plugin=plugin, component=component
            )
            component_dump["component_type"] = component.component_type
            if not component._is_builtin_component():
                # Plugin components are serialized with the corresponding
                # plugin name and version.
                component_dump["component_plugin_name"] = plugin.plugin_name
                component_dump["component_plugin_version"] = plugin.plugin_version

            referenced_component_ids = [
                ref_id
                for ref_id, current_id in self._referencing_structure.items()
                if current_id == component_id
            ]
            if len(referenced_component_ids) > 0:
                component_dump["$referenced_components"] = {
                    ref_id: self._resolved_components[ref_id]
                    for ref_id in referenced_component_ids
                    if ref_id not in self._components_id_mapping
                    # ^ If a referenced component is disaggregated
                    # it is only defined in the disaggregated config.
                }

            self._resolved_components[component_id] = component_dump

        if (is_referenced_component := component_id in self._referencing_structure) or (
            is_disaggregated_component := component_id in self._components_id_mapping
        ):
            return {"$component_ref": mapped_id}
        else:
            return self._resolved_components[mapped_id]

    @overload
    def dump_field(self, value: bool, info: Optional[FieldInfoTypeT]) -> bool:
        pass

    @overload
    def dump_field(self, value: int, info: Optional[FieldInfoTypeT]) -> int:
        pass

    @overload
    def dump_field(self, value: float, info: Optional[FieldInfoTypeT]) -> float:
        pass

    @overload
    def dump_field(self, value: str, info: Optional[FieldInfoTypeT]) -> str:
        pass

    @overload
    def dump_field(self, value: List[T], info: Optional[FieldInfoTypeT]) -> List[Any]:
        pass

    @overload
    def dump_field(self, value: Dict[str, T], info: Optional[FieldInfoTypeT]) -> Dict[str, Any]:
        pass

    @overload
    def dump_field(self, value: BaseModel, info: Optional[FieldInfoTypeT]) -> Dict[str, Any]:
        pass

    def dump_field(
        self,
        value: Union[int, float, bool, str, List[T], Dict[str, T], BaseModel, Component],
        info: Optional[FieldInfoTypeT],
    ) -> Union[int, float, bool, str, List[Any], Dict[str, Any]]:
        if isinstance(value, Component):
            return self._dump_component_to_dict(value)
        elif isinstance(value, BaseModel):
            return value.model_dump(context=self)
        elif isinstance(value, Enum) and isinstance(value.value, str):
            return value.value
        elif isinstance(value, list) or isinstance(value, tuple):
            return [self.dump_field(x, None) for x in value]
        elif isinstance(value, dict):
            return {k: self.dump_field(v, None) for k, v in value.items()}
        elif isinstance(value, (int, bool, str, float, type(None))):
            return value
        else:
            raise TypeError(f"Unsupported value type {value!r}")

    def _is_pydantic_field_info(self, field_info: FieldInfoTypeT) -> TypeGuard[FieldInfo]:
        return isinstance(field_info, FieldInfo)

    @overload
    def _make_ordered_dict(
        self,
        obj_dump: Dict[str, Any],
    ) -> Dict[str, Any]: ...
    @overload
    def _make_ordered_dict(
        self, obj_dump: Union[Dict[str, Any], List[Any], Any]
    ) -> Union[Dict[str, Any], List[Any], Any]: ...
    def _make_ordered_dict(
        self, obj_dump: Union[Dict[str, Any], List[Any], Any]
    ) -> Union[Dict[str, Any], List[Any], Any]:
        """
        Make the YAML/JSON look nicer by making the keys "component_type", "id", "name", "description"
        come first in the component's dict.
        """
        priority_keys = ["component_type", "id", "name", "description"]
        if isinstance(obj_dump, dict):
            ordered_dict = {k: obj_dump[k] for k in priority_keys if k in obj_dump}
            for key, value in obj_dump.items():
                if key not in priority_keys:
                    ordered_dict[key] = self._make_ordered_dict(value)

            # since python 3.7, dict preserves the insertion order
            return ordered_dict
        elif isinstance(obj_dump, list):
            return [self._make_ordered_dict(i) for i in obj_dump]
        else:
            # that is a primitive type
            return obj_dump

    def _save_to_dict(
        self, component: Component, agentspec_version: Optional[AgentSpecVersionEnum] = None
    ) -> ComponentAsDictT:
        # Validate requested version is allowed
        min_agentspec_version, _min_component = component._get_min_agentspec_version_and_component()
        max_agentspec_version, _max_component = component._get_max_agentspec_version_and_component()
        if min_agentspec_version > max_agentspec_version:
            raise ValueError(
                f"Incompatible agentspec_versions: min agentspec_version={min_agentspec_version} "
                f"(lower bounded by component '{_min_component.name}') "
                f"is greater than max agentspec_version={max_agentspec_version} "
                f"(upper bounded by component '{_max_component.name}')"
            )
        chosen_version = agentspec_version or min_agentspec_version
        if chosen_version < min_agentspec_version:
            raise ValueError(
                f"Invalid agentspec_version: received agentspec_version={chosen_version} "
                f"but the minimum allowed version is {min_agentspec_version} "
                f"(lower bounded by component '{_min_component.name}')"
            )
        elif chosen_version > max_agentspec_version:
            raise ValueError(
                f"Invalid agentspec_version: received agentspec_version={chosen_version} "
                f"but the maximum allowed version is {max_agentspec_version} "
                f"(upper bounded by component '{_max_component.name}')"
            )

        self.agentspec_version = chosen_version
        # Pydantic will inline all inner components, potentially many times the same component
        # if it is used in many places, but we want to avoid that, and use references instead
        self._referencing_structure = _compute_referencing_structure(component)

        model_dump = self.dump_field(component, info=None)
        model_dump[AGENTSPEC_VERSION_FIELD_NAME] = chosen_version.value
        # Make the YAML/JSON look nicer by putting the informative keys (e.g `component_type`, `id`) first.
        ordered_model_dump = cast(ComponentAsDictT, self._make_ordered_dict(model_dump))
        return ordered_model_dump

    def _dump_component_with_plugin(
        self,
        plugin: "ComponentSerializationPlugin",
        component: Component,
    ) -> ComponentAsDictT:

        return plugin.serialize(component=component, serialization_context=self)


def _get_children_direct_from_field_value(field_value: Any) -> List[Component]:
    """
    Extract all child component contained in the field of a component.

    Given a potentially deeply nested dict or list structure containing components, returns the
    list of all contained components.
    """
    if isinstance(field_value, Component):
        return [field_value]
    elif isinstance(field_value, (list, dict, set, tuple)):
        inner_field_values = field_value.values() if isinstance(field_value, dict) else field_value
        return [
            child
            for inner_field_value in inner_field_values
            for child in _get_children_direct_from_field_value(inner_field_value)
        ]
    else:
        # that is a primitive type (such as int or str) so it does not have children
        return []


def _get_all_direct_children(component: Component) -> Dict[str, List[str]]:
    """
    Return direct children of all components.

    Return a dictionary with one entry for every subcomponent which contains the list of its
    direct children. Direct children include child components in nested dict or list, but not
    components in fields of child components.
    """
    children = {}
    component_queue = [component]
    while component_queue:
        current_component = component_queue.pop()
        if current_component.id in children:
            continue
        direct_children = []
        for field_name in current_component.model_fields_set:
            inner_component = getattr(current_component, field_name)
            inner_children = _get_children_direct_from_field_value(inner_component)
            direct_children.extend([inner_child.id for inner_child in inner_children])
            component_queue.extend(inner_children)
        children[current_component.id] = direct_children
    return children


def _compute_referencing_structure(component: Component) -> Dict[str, str]:
    """
    Return the referencing structure of a component.

    The referencing structure is a dictionary with entries for every child component pointing the
    parent (possibly grandparent) component that should contain it as a reference.

    The way this is computed consists in a DFS that finds the highest component in the DAG of
    components that refers to each component. This is achieved by keeping track of all references
    going down the DAG back to its root and merging references of children while ensuring that when
    two children reference the same component in a different manner, then the parent component will
    take the corresponding reference.
    """
    children = _get_all_direct_children(component)
    # The data structure `reference_levels_at_node` will be filled by the recursive loop
    # `_inner_compute_references` defined below.
    # For every `node_id` as key it has a value of type `Dict[str, Union[str, Tuple[None, str]]]`
    # which is the assignment of the reference level for all child component from the point of
    # view of this `node_id`, which means including the whole sub-graph reachable from this
    # component by following the DAG structure.
    reference_levels_at_node: Dict[str, Dict[str, Union[str, Tuple[None, str]]]] = {}

    def _inner_compute_references(node_id: str) -> None:
        if node_id in reference_levels_at_node:
            return
        for child_node in children[node_id]:
            _inner_compute_references(child_node)

        current_reference_levels: Dict[str, Union[str, Tuple[None, str]]] = {}
        all_children_with_counts = Counter(children[node_id]).items()
        for child_node_id, child_usage_count in all_children_with_counts:
            # Some component may have two fields referencing the same child. This condition takes
            # care of this situation. For example, it is the case of Flow which may have the same
            # child node as part of `Flow.start_node` and `Flow.nodes`
            if child_usage_count > 1 or child_node_id in current_reference_levels:
                current_reference_levels[child_node_id] = node_id
            else:
                # This tuple (None, str) is used to indicate that child_node_id
                # does not need to be referenced and is under parent node_id
                # If in the loop below another version of this tuple with a different
                # parent is encountered, then the value will be updated to indicate that
                # a reference is needed.
                current_reference_levels[child_node_id] = (None, node_id)
            for referenced_by_child, reference_level_at_child_node in reference_levels_at_node[
                child_node_id
            ].items():
                if referenced_by_child not in current_reference_levels:
                    current_reference_levels[referenced_by_child] = reference_level_at_child_node
                else:
                    if (
                        current_reference_levels[referenced_by_child]
                        != reference_level_at_child_node
                    ):
                        current_reference_levels[referenced_by_child] = node_id

        reference_levels_at_node[node_id] = current_reference_levels

    _inner_compute_references(component.id)
    reference_levels_at_root = reference_levels_at_node[component.id]
    resolved_reference_levels_at_root = {
        nid: level for nid, level in reference_levels_at_root.items() if isinstance(level, str)
    }
    return resolved_reference_levels_at_root
