# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Component allow/block policy helpers used while loading Agent Spec configurations."""

from typing import Iterable, Optional, Set, Tuple, Type, Union, cast

from pyagentspec.component import Component

ComponentPolicyEntry = Union[str, Type[Component]]
ComponentPolicyInput = Union[ComponentPolicyEntry, Iterable[ComponentPolicyEntry]]
_NormalizedComponentPolicyInput = Tuple[ComponentPolicyEntry, ...]


def _normalize_component_types(
    component_types: Optional[ComponentPolicyInput],
) -> Optional[_NormalizedComponentPolicyInput]:
    """Normalizes component policy input to a reusable tuple.

    Accepts a single component type name, a Component class, or an iterable of either
    form. Returns None when no policy was provided.
    """
    if component_types is None:
        return None
    if isinstance(component_types, str):
        component_types = [component_types]
    elif isinstance(component_types, type) and issubclass(component_types, Component):
        component_types = [component_types]
    else:
        try:
            iter(component_types)
        except TypeError:
            raise TypeError(
                "`allowed_components` and `blocked_components` entries must be component "
                f"type names or Component classes, got {component_types!r}."
            ) from None

    normalized_component_types: list[ComponentPolicyEntry] = []
    for component_type in component_types:
        if isinstance(component_type, str):
            normalized_component_types.append(component_type)
        elif isinstance(component_type, type) and issubclass(component_type, Component):
            normalized_component_types.append(component_type)
        else:
            raise TypeError(
                "`allowed_components` and `blocked_components` entries must be component "
                f"type names or Component classes, got {component_type!r}."
            )
    return tuple(normalized_component_types)


def _split_component_types(
    component_types: _NormalizedComponentPolicyInput,
) -> tuple[Set[str], Tuple[Type[Component], ...]]:
    """Splits normalized entries into exact names and class hierarchy entries."""
    component_type_names: Set[str] = set()
    component_classes: list[Type[Component]] = []
    for component_type in component_types:
        if isinstance(component_type, str):
            component_class = Component.get_class_from_name(component_type)
            if component_class is None:
                component_type_names.add(component_type)
            else:
                component_classes.append(component_class)
        else:
            component_classes.append(component_type)
    return component_type_names, tuple(component_classes)


def _get_children_direct_from_field_value(field_value: object) -> list[Component]:
    """Returns Component instances contained directly or through collection values."""
    if isinstance(field_value, Component):
        return [field_value]
    if isinstance(field_value, dict):
        return [
            child
            for inner_field_value in field_value.values()
            for child in _get_children_direct_from_field_value(inner_field_value)
        ]
    if isinstance(field_value, (list, set, tuple)):
        return [
            child
            for inner_field_value in field_value
            for child in _get_children_direct_from_field_value(inner_field_value)
        ]
    return []


class ComponentLoadPolicy:
    """Allow/block policy for component types loaded from Agent Spec configurations.

    Policy entries can be serialized component type names or ``Component`` classes.
    Component type names that resolve to known ``Component`` classes match that class
    and its subclasses, like class entries. Component type names that do not resolve
    to known classes match only that exact serialized component type. When both allow
    and block entries match a component, the closest match in the component class
    hierarchy wins. Exact component type name matches and exact class matches have
    distance 0; block entries win ties at the same hierarchy distance.
    """

    def __init__(
        self,
        allowed_components: Optional[ComponentPolicyInput] = None,
        blocked_components: Optional[ComponentPolicyInput] = None,
    ) -> None:
        """
        Instantiate a component load policy.

        Parameters
        ----------
        allowed_components:
            Optional component type names or Component classes allowed to load. If omitted,
            all component types are allowed unless a matching block entry applies.
            Resolvable type names and Component classes also match subclasses; unresolved
            type names match only the exact serialized component type.
        blocked_components:
            Optional component type names or Component classes blocked from loading.
            Resolvable type names and Component classes also match subclasses; unresolved
            type names match only the exact serialized component type.
        """
        self.allowed_components = _normalize_component_types(allowed_components)
        self.blocked_components = _normalize_component_types(blocked_components) or ()
        (
            self._allowed_component_type_names,
            self._allowed_component_classes,
        ) = _split_component_types(self.allowed_components or ())
        (
            self._blocked_component_type_names,
            self._blocked_component_classes,
        ) = _split_component_types(self.blocked_components)

    def validate_component_type(self, component_type: str) -> None:
        """Raise if the component type is disallowed by the policy."""
        component_class = Component.get_class_from_name(component_type)
        self._validate_component(component_type, component_class)

    def validate_component(self, component: Component) -> None:
        """Raise if the component is disallowed by the policy."""
        self._validate_component(
            cast(str, component.component_type),
            component.__class__,
        )

    def _validate_component(
        self,
        component_type: str,
        component_class: Optional[Type[Component]],
    ) -> None:
        blocked_match_distance = self._get_best_policy_match_distance(
            component_type,
            component_class,
            self._blocked_component_type_names,
            self._blocked_component_classes,
        )
        allowed_match_distance = self._get_best_policy_match_distance(
            component_type,
            component_class,
            self._allowed_component_type_names,
            self._allowed_component_classes,
        )

        if blocked_match_distance is not None and (
            allowed_match_distance is None or blocked_match_distance <= allowed_match_distance
        ):
            raise ValueError(
                f"Loading Agent Spec component type `{component_type}` is in the block list."
            )
        if self.allowed_components is not None and allowed_match_distance is None:
            raise ValueError(
                f"Loading Agent Spec component type `{component_type}` is not in the allow list."
            )

    @staticmethod
    def _get_best_policy_match_distance(
        component_type: str,
        component_class: Optional[Type[Component]],
        component_type_names: Set[str],
        component_classes: Tuple[Type[Component], ...],
    ) -> Optional[int]:
        """Return the distance of the most specific matching policy entry."""
        match_distances: list[int] = []
        if component_type in component_type_names:
            match_distances.append(0)
        if component_class is not None:
            # mro() is Python's built-in class method for method resolution order.
            # component_mro is the ordered list of the component class and its base
            # classes, so its index gives the inheritance distance used to choose
            # the most specific policy.
            component_mro = component_class.mro()
            for policy_class in component_classes:
                if issubclass(component_class, policy_class):
                    match_distances.append(component_mro.index(policy_class))
        return min(match_distances) if match_distances else None

    def validate_component_tree(self, component: Component) -> None:
        """Validate a constructed component and all nested child components."""
        components_to_check = [component]
        visited_component_ids: set[int] = set()
        while components_to_check:
            current_component = components_to_check.pop()
            if id(current_component) in visited_component_ids:
                continue
            visited_component_ids.add(id(current_component))

            self.validate_component(current_component)
            for field_name in current_component.__class__.model_fields:
                field_value = getattr(current_component, field_name, None)
                components_to_check.extend(_get_children_direct_from_field_value(field_value))
