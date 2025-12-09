# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the base class for all components in Agent Spec."""

import uuid
from collections import Counter, deque
from copy import deepcopy
from enum import Enum
from operator import itemgetter
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    SerializationInfo,
    TypeAdapter,
    computed_field,
    model_serializer,
)
from pydantic.fields import FieldInfo
from pydantic.json_schema import (
    DEFAULT_REF_TEMPLATE,
    GenerateJsonSchema,
    JsonSchemaMode,
    JsonSchemaValue,
    SkipJsonSchema,
)
from typing_extensions import Annotated, Self

from pyagentspec.property import Property
from pyagentspec.validation_helpers import (
    PyAgentSpecErrorDetails,
    model_validator_with_error_accumulation,
)
from pyagentspec.versioning import (
    _LEGACY_AGENTSPEC_VERSIONS,
    AGENTSPEC_VERSION_FIELD_NAME,
    AgentSpecVersionEnum,
)

if TYPE_CHECKING:
    from pyagentspec.serialization import ComponentDeserializationPlugin

EnumType = TypeVar("EnumType", bound=Enum)
SerializeAsEnum = Annotated[EnumType, PlainSerializer(lambda x: x.value)]
ComponentT = TypeVar("ComponentT", bound="Component")


def _unwrap_optional(annotation: Any) -> Any:
    """Unwrap Optional/Union to ignore NoneType and return the core annotation."""
    origin = get_origin(annotation)
    if origin is Union:
        args = {a for a in get_args(annotation) if a is not type(None)}
        return args.pop() if args else Any
    return annotation


def _get_collection_element_type(annotation: Any) -> Any:
    annotation = _unwrap_optional(annotation)
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (list, set, frozenset):
        return args[0] if args else Any
    elif origin is tuple:
        if len(args) == 2 and args[1] is Ellipsis:
            return args[0]
        return args
    elif origin is dict:
        return args[1] if len(args) == 2 else Any
    return Any


def _get_class_from_component_config(value: Dict[str, Any]) -> Optional[Type["Component"]]:
    return next(
        (
            cls_
            for cls_ in Component._get_all_subclasses()
            if cls_.__name__ == value.get("component_type", "")
        ),
        None,
    )


class AbstractableModel(BaseModel):
    """
    Define abstract models that cannot be instantiated.

    Example Usage:
    --------------
    ```python
    class Component(AbstractableModel, abstract=True):
        pass
    ```

    """

    _is_abstract: bool = False

    def __init_subclass__(
        cls: Type["AbstractableModel"], abstract: bool = False, **kwargs: Any
    ) -> None:
        """
        Set the _is_abstract attribute on the class.

        Parameters
        ----------
        abstract:
            If True, the class cannot be instantiated
        """
        cls._is_abstract = abstract
        super().__init_subclass__(**kwargs)

    def __new__(cls, *args: Any, **kwargs: Any) -> "AbstractableModel":
        """Create a new instance of the class."""
        if cls._is_abstract:
            raise TypeError(
                f"Class '{cls.__name__}' is meant to be abstract and cannot be instantiated"
            )
        return super().__new__(cls)


class Component(AbstractableModel, abstract=True):
    """
    Base class for all components that can be used in Agent Spec.

    In Agent Spec, there are components to represent Agents, Flows, LLMs, etc.
    """

    model_config = ConfigDict(extra="forbid")

    def __init_subclass__(cls: Type["Component"], **kwargs: Any) -> None:
        """
        Registry pattern for serializable models, compatible with pydantic.

        See https://github.com/pydantic/pydantic/issues/5124 for more info
        """
        super().__init_subclass__(**kwargs)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), frozen=True)
    """A unique identifier for this Component"""
    name: str
    """Name of this Component"""
    description: Optional[str] = None
    """Optional description of this Component"""
    metadata: Optional[Dict[str, Any]] = Field(default_factory=lambda: dict())
    """Optional, additional metadata related to this Component"""

    min_agentspec_version: SkipJsonSchema[SerializeAsEnum["AgentSpecVersionEnum"]] = Field(
        default=AgentSpecVersionEnum.v25_4_1, init=False, exclude=True
    )
    max_agentspec_version: SkipJsonSchema[SerializeAsEnum["AgentSpecVersionEnum"]] = Field(
        default=AgentSpecVersionEnum.current_version, init=False, exclude=True
    )

    def model_post_init(self, __context: Any) -> None:
        """Override of the method used by Pydantic as post-init."""
        super().model_post_init(__context)
        self.min_agentspec_version = self._infer_min_agentspec_version_from_configuration()

    @computed_field
    def component_type(self) -> str:
        """Return the name of this Component's type."""
        return self.__class__.__name__

    @classmethod
    def _is_builtin_component(cls) -> bool:
        from pyagentspec._component_registry import BUILTIN_CLASS_MAP

        return cls.__name__ in BUILTIN_CLASS_MAP

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        """
        Returns the minimum agentspec version needed to correctly represent
        this Component and its behavior based on its configuration.
        """
        # By default, we just return the min_agentspec_version defined for the Component
        # If a Component changes its behavior based on the spec version, it should override this method accordingly
        return self.min_agentspec_version

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        """Returns the set of model fields names to exclude for the component.
        Can be overridden by components to include version-specific fields.
        """
        return set()

    def get_versioned_model_fields(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> Dict[str, FieldInfo]:
        """Returns the dictionary of model fields info."""
        model_fields = self.__class__.model_fields
        fields_to_exclude = self._versioned_model_fields_to_exclude(agentspec_version)
        return {
            f_name: f_info
            for f_name, f_info in model_fields.items()
            if f_name not in fields_to_exclude
        }

    @property
    def model_fields_set(self) -> set[str]:
        """
        Returns the set of fields that have been explicitly set on this model instance,
        except the min_agentspec_version which is manually specified.
        """
        return super().model_fields_set.difference({"min_agentspec_version"})

    @model_validator_with_error_accumulation
    def _validate_versioning(self) -> Self:
        if self.min_agentspec_version > self.max_agentspec_version:
            raise ValueError(
                f"Invalid min/max versioning for component with name '{self.name}': "
                f"min_agentspec_version={self.min_agentspec_version} > "
                f"max_agentspec_version={self.max_agentspec_version}"
            )
        return self

    def _get_min_agentspec_version_and_component(
        self, visited: Optional[Set[str]] = None
    ) -> Tuple[AgentSpecVersionEnum, "Component"]:
        """
        Return the minimum required Agent Spec version to export this component
        and the component enforcing that minimum version.
        """
        from pyagentspec.serialization.serializationcontext import (
            _get_children_direct_from_field_value,
        )

        if visited is None:
            visited = set()

        min_agentspec_version: AgentSpecVersionEnum = self.min_agentspec_version
        min_component: Component = self
        for field_name in self.__class__.model_fields:
            field_value = getattr(self, field_name, None)
            if field_value is not None:
                sub_components = _get_children_direct_from_field_value(field_value)
                items: List[Tuple[AgentSpecVersionEnum, Component]] = [
                    (min_agentspec_version, min_component)
                ]
                for component in sub_components:
                    if component.id in visited:
                        continue
                    visited.add(component.id)
                    items.append(
                        component._get_min_agentspec_version_and_component(visited=visited)
                    )
                min_agentspec_version, min_component = max(items, key=itemgetter(0))
        return min_agentspec_version, min_component

    def _get_max_agentspec_version_and_component(
        self, visited: Optional[Set[str]] = None
    ) -> Tuple[AgentSpecVersionEnum, "Component"]:
        """
        Return the maximum required Agent Spec version to export this component
        and the component enforcing that maximum version.
        """
        from pyagentspec.serialization.serializationcontext import (
            _get_children_direct_from_field_value,
        )

        if visited is None:
            visited = set()

        max_agentspec_version: AgentSpecVersionEnum = self.max_agentspec_version
        max_component = self
        for field_name in self.__class__.model_fields:
            field_value = getattr(self, field_name, None)
            if field_value is not None:
                sub_components = _get_children_direct_from_field_value(field_value)
                items: List[Tuple[AgentSpecVersionEnum, Component]] = [
                    (max_agentspec_version, max_component)
                ]
                for component in sub_components:
                    if component.id in visited:
                        continue
                    visited.add(component.id)
                    items.append(
                        component._get_max_agentspec_version_and_component(visited=visited)
                    )
                max_agentspec_version, max_component = min(items, key=itemgetter(0))
        return max_agentspec_version, max_component

    @staticmethod
    def get_class_from_name(class_name: str) -> Optional[Type["Component"]]:
        """
        Given the class name of a component, return the respective class.

        Parameters
        ----------
        class_name:
            The name of the component's class to retrieve

        Returns
        -------
            The component's class
        """
        # We start from the top level component, and we look for the subclass with the given name
        # This solution makes us support also components that are not builtin (e.g., plugin components)
        queue = deque([Component])
        while queue:
            new_subclasses = queue.pop().__subclasses__()
            subclass_found = next(
                (subclass for subclass in new_subclasses if subclass.__name__ == class_name), None
            )
            if subclass_found is not None:
                return subclass_found
            queue.extend(new_subclasses)
        return None

    @classmethod
    def _get_all_subclasses(
        cls: Type["Component"], only_core_components: bool = False
    ) -> Tuple[Type["Component"], ...]:
        queue, all_subclasses = deque([cls]), set()
        while queue:
            new_subclasses = queue.pop().__subclasses__()
            queue.extend(new_subclasses)
            all_subclasses.update(new_subclasses)
        return tuple(
            s
            for s in sorted(all_subclasses, key=lambda subclass: subclass.__name__)
            if not only_core_components or s._is_builtin_component()
        )

    def _is_equal(self, other: Any, fields_to_exclude: Optional[List[str]] = None) -> bool:
        # The default __eq__ of pydantic's BaseModel has worst case exponential time complexity.
        #
        # For example, on the component with the nested definition:
        #
        #     o--> B1 --o--> C1 --o--> D1 --o--> E1
        #     |         |         |         |
        # A --o--> B2 --o--> C2 --o--> D2 --o--> E2
        #     |         |         |         |
        #     o--> B3 --o--> C3 --o--> D3 --o--> E3
        #
        # "A" uses "B1", "B2" and "B3" in its definition.
        # "B1" uses "C1", "C2" and "C3" in its definition.
        # "C1" uses "D1", "D2" and "D3" in its definition.
        # ...etc
        #
        # In that case evaluating "A == A" leads to checking 3^3 times the value "E1 == E1". Once for
        # every possible paths "E1" can be reach from the definition of "A"
        visited = set()
        values_to_check = [(self, other)]
        while values_to_check:
            value_a, value_b = values_to_check.pop()
            if value_a is value_b:
                continue
            if (id(value_a), id(value_b)) in visited:
                continue
            visited.add((id(value_a), id(value_b)))
            if isinstance(value_a, Component):
                if not isinstance(value_b, value_a.__class__):
                    return False
                field_names = [
                    f_name
                    for f_name in value_a.__class__.model_fields.keys()
                    if f_name not in (fields_to_exclude or [])
                ]
                values_to_check.extend(
                    (getattr(value_a, field_name_), getattr(value_b, field_name_))
                    for field_name_ in field_names
                )
            elif isinstance(value_a, (list, tuple)):
                if len(value_a) != len(value_b):
                    return False
                values_to_check.extend(zip(value_a, value_b))
            elif isinstance(value_a, dict):
                if set(value_a) != set(value_b):
                    return False
                values_to_check.extend((value_a[k], value_b[k]) for k in value_a.keys())
            else:
                if value_a != value_b:
                    return False
        return True

    def __eq__(self, other: Any) -> bool:
        return self._is_equal(other)

    def __repr__(self) -> str:
        # The default __repr__ of pydantic's BaseModel may produce representations of exponential
        # size.
        #
        # For example, on the component with the nested definition:
        #
        #     o--> B1 --o--> C1 --o--> D1 --o--> E1
        #     |         |         |         |
        # A --o--> B2 --o--> C2 --o--> D2 --o--> E2
        #     |         |         |         |
        #     o--> B3 --o--> C3 --o--> D3 --o--> E3
        #
        # "A" uses "B1", "B2" and "B3" in its definition.
        # "B1" uses "C1", "C2" and "C3" in its definition.
        # "C1" uses "D1", "D2" and "D3" in its definition.
        # ...etc
        #
        # In that case evaluating the repr(A) will contain 3^3 times the repr(E1). Once for
        # every possible paths "E1" can be reach from the definition of "A".
        return f"{self.__class__.__name__}(id={self.id}, name={self.name}, ...)"

    @classmethod
    def model_json_schema(
        cls: Type["Component"],
        by_alias: bool = True,
        ref_template: str = DEFAULT_REF_TEMPLATE,
        schema_generator: type[GenerateJsonSchema] = GenerateJsonSchema,
        mode: JsonSchemaMode = "validation",
        only_core_components: bool = False,
        **kwargs: Any,
    ) -> JsonSchemaValue:
        """
        Build the json schema for Agent Spec Components.

        Note that arguments of the method are ignored.

        Parameters
        ----------
        by_alias:
            Whether to use attribute aliases or not.
        ref_template:
            The reference template.
        schema_generator:
            To override the logic used to generate the JSON schema, as a subclass of
            ``GenerateJsonSchema`` with your desired modifications
        mode:
            The mode in which to generate the schema.
        only_core_components:
            Generate the schema containing only core Agent Spec components as per language specification

        Returns
        -------
            The json schema specification for the chosen Agent Spec Component
        """
        if cls._is_abstract:
            all_subclasses = cls._get_all_subclasses(only_core_components=only_core_components)
            adapter = TypeAdapter(Union[all_subclasses])  # type: ignore
            json_schema = adapter.json_schema(by_alias=by_alias, mode=mode)
        else:
            json_schema = super().model_json_schema(by_alias=by_alias, mode=mode, **kwargs)
        json_schema_with_all_types = replace_abstract_models_and_hierarchical_definitions(
            json_schema, mode, only_core_components=only_core_components, by_alias=by_alias
        )
        json_schema_with_references = _add_references(json_schema_with_all_types, cls.__name__)
        json_schema_with_agentspec_version = _add_agentspec_version_field(
            json_schema_with_references
        )
        return json_schema_with_agentspec_version

    @model_serializer()
    def serialize_model(self, info: SerializationInfo):  # type: ignore
        """
        Serialize a Pydantic Component.

        Is invoked upon a ``model_dump`` call.
        """
        from pyagentspec.serialization.serializationcontext import SerializationContext

        serialization_context = info.context
        if isinstance(serialization_context, SerializationContext):
            return serialization_context._dump_component_to_dict(self)

        raise ValueError("Missing proper serialization context")

    @classmethod
    def build_from_partial_config(
        cls: Type[ComponentT],
        partial_config: Dict[str, Any],
        plugins: Optional[List["ComponentDeserializationPlugin"]] = None,
    ) -> ComponentT:
        """
        Build the component without running any validation.

        Parameters
        ----------
        partial_config:
            A dictionary containing an incomplete configuration that should be used to build this Component
        plugins:
            The list of ``ComponentDeserializationPlugin`` instances needed to build the component

        Returns
        -------
            The constructed component
        """
        from pyagentspec.serialization import AgentSpecDeserializer
        from pyagentspec.versioning import AGENTSPEC_VERSION_FIELD_NAME, AgentSpecVersionEnum

        deserializer = AgentSpecDeserializer(plugins=plugins)
        # Deserialization needs an agentspec_version to deserialized for
        # If it is given, we use that, otherwise we use the current version
        if AGENTSPEC_VERSION_FIELD_NAME not in partial_config:
            if "min_agentspec_version" in partial_config:
                partial_config[AGENTSPEC_VERSION_FIELD_NAME] = partial_config[
                    "min_agentspec_version"
                ]
            else:
                partial_config[AGENTSPEC_VERSION_FIELD_NAME] = AgentSpecVersionEnum.current_version
        partial_config["component_type"] = cls.__name__
        partial_component, validation_errors = deserializer.from_partial_dict(partial_config)
        # Deserialization ignores min and max agentspec versions (besides validation), so we set them manually
        if "min_agentspec_version" in partial_config:
            partial_component.min_agentspec_version = AgentSpecVersionEnum(  # type: ignore
                partial_config["min_agentspec_version"]
            )
        if "max_agentspec_version" in partial_config:
            partial_component.max_agentspec_version = AgentSpecVersionEnum(  # type: ignore
                partial_config["max_agentspec_version"]
            )
        return cast(ComponentT, partial_component)

    @classmethod
    def get_validation_errors(
        cls: Type[ComponentT],
        partial_config: Dict[str, Any],
        plugins: Optional[List["ComponentDeserializationPlugin"]] = None,
    ) -> List[PyAgentSpecErrorDetails]:
        """
        Return a list of validation errors for this Component.

        Parameters
        ----------
        partial_config:
            The partial configuration of the Component.
        plugins:
            The list of ``ComponentDeserializationPlugin`` instances needed to build the component

        Returns
        -------
            The list of validation errors for this Component. If the returned list is empty, the
            component can be constructed without any additional validation.
        """
        from pyagentspec.serialization import AgentSpecDeserializer
        from pyagentspec.versioning import AGENTSPEC_VERSION_FIELD_NAME, AgentSpecVersionEnum

        deserializer = AgentSpecDeserializer(plugins=plugins)
        if AGENTSPEC_VERSION_FIELD_NAME not in partial_config:
            partial_config[AGENTSPEC_VERSION_FIELD_NAME] = AgentSpecVersionEnum.current_version
        partial_config["component_type"] = cls.__name__
        _, validation_errors = deserializer.from_partial_dict(partial_config)
        return validation_errors


def replace_abstract_models_and_hierarchical_definitions(
    json_schema: JsonSchemaValue,
    mode: JsonSchemaMode,
    only_core_components: bool = False,
    by_alias: bool = True,
) -> JsonSchemaValue:
    """
    Modify the json schema to expand abstract and hierarchical component types.

    The concept of abstract components and handling of inheritance is missing in Pydantic, thus
    Agent Spec is adding it. The role of this method is to modify the generated schemas to ensure
    that serialized forms of abstract and extended component types are correctly typed.

    For example when a component points to an abstract type ``Node``, the abstract type is modified
    in the json schema specification to be replaced by an ``anyOf`` listing all concrete subtypes
    of the ``Node`` type, these include ``StartNode``, ``LlmNode``, ``AgentNode``, and more...

    Quick explanations of the algorithm below:
    -   If the json schema does not have an entry ``$defs``, it means that it is not referencing
        any type at all, so as a consequence, it is not referencing abstract types and nothing
        needs to be done.
    -   The list ``abstract_types_to_resolve`` is used as a stack. It contains all the abstract
        types that must be extended to the definition. It is first initialized as all the abstract
        types initially defined in the schema.
    -   Whenever an abstract type definition requires other abstract types to be defined these new
        abstract types are appended to the stack ``abstract_types_to_resolve``. For
        example: the abstract type ``Node`` definition requires the definition of concrete
        ``LlmNode``, which has the attribute ``llm_config`` of abstract type ``LlmConfig``, thus
        the definition of the ``Node`` abstract type requires to get the definition of the
        ``LlmConfig`` abstract type.
    """
    if "$defs" in json_schema:
        # Resolve abstract types first
        abstract_types_to_resolve: deque[str] = deque(
            [
                component_type_name
                for component_type_name in json_schema["$defs"]
                if (component_type := Component.get_class_from_name(component_type_name))
                and component_type._is_abstract
            ]
        )
        resolved_abstract_types: Set[str] = set()
        while abstract_types_to_resolve:
            component_type_name = abstract_types_to_resolve.pop()
            component_type = Component.get_class_from_name(component_type_name)
            if component_type is None:
                raise RuntimeError(f"Tried to resolve a missing type: '{component_type_name}'.")
            all_subclasses = component_type._get_all_subclasses(
                only_core_components=only_core_components
            )
            num_subclasses = len(all_subclasses)
            if num_subclasses > 1:
                abstract_type_json_schema = TypeAdapter(Union[tuple(all_subclasses)]).json_schema(
                    mode=mode, by_alias=by_alias
                )
            elif num_subclasses == 1:
                subclass_ = all_subclasses[0]
                abstract_type_json_schema = TypeAdapter(Union[subclass_, None]).json_schema(
                    mode=mode, by_alias=by_alias
                )
                abstract_type_json_schema["anyOf"].remove({"type": "null"})
                # ^ pop the null ref (ok since python list.remove relies on equality)
            else:
                raise ValueError(
                    f"No subclass was found for abstract type `{component_type_name}`."
                )

            new_type_definitions = abstract_type_json_schema.pop("$defs")
            abstract_types_to_resolve.extend(
                [
                    new_component_type_name
                    for new_component_type_name in new_type_definitions
                    if (
                        new_component_type := Component.get_class_from_name(new_component_type_name)
                    )
                    and new_component_type._is_abstract
                    and new_component_type_name not in resolved_abstract_types
                ]
            )
            json_schema["$defs"].update(
                {
                    new_component_type_name: new_type_definition
                    for new_component_type_name, new_type_definition in new_type_definitions.items()
                    if not (
                        new_component_type := Component.get_class_from_name(new_component_type_name)
                    )
                    or not new_component_type._is_abstract
                }
            )
            json_schema["$defs"][component_type_name] = abstract_type_json_schema
            resolved_abstract_types.add(component_type_name)

        # Resolve concrete types
        concrete_types_to_resolve: List[str] = [
            component_type_name
            for component_type_name in json_schema["$defs"]
            if (component_type := Component.get_class_from_name(component_type_name))
            and not component_type._is_abstract
        ]
        for component_type_name in concrete_types_to_resolve:
            # For each type we take its json schema, and we replace it with an anyOf
            # of its own json schema, plus the reference to the schemas of all its subclasses
            component_type = Component.get_class_from_name(component_type_name)
            if component_type is None:
                raise RuntimeError(f"Tried to resolve a missing type: '{component_type_name}'.")
            all_subclasses = component_type._get_all_subclasses(
                only_core_components=only_core_components
            )
            if len(all_subclasses) > 0:
                concrete_type_json_schema = json_schema["$defs"][component_type_name]
                json_schema["$defs"][component_type_name] = {
                    "anyOf": [
                        {"$ref": f"#/$defs/{subcomponent_type.__name__}"}
                        for subcomponent_type in all_subclasses
                    ]
                    + [concrete_type_json_schema]
                }
    return json_schema


def _add_references(json_schema: JsonSchemaValue, root_type_name: str) -> JsonSchemaValue:
    """
    Modify the json schema to include the concept of references of components.

    The concept of referenced components is missing in Pydantic, thus Agent Spec is adding it. The
    role of this method is to modify the generated schemas to ensure that serialized forms using
    references are correctly typed.

    Some useful infos:
    -   The types ``ReferencedComponents``, ``ComponentReference``,
        ``ComponentReferenceWithNestedReferences`` are added to the definitions in the schema
    -   ``ReferencedComponents`` is an object with any number of keys, whose values must be of any
        of the Agent Spec Component Types
    -   ``ComponentReference`` is an object with a single key ``$component_ref`` of type string
    -   ``ComponentReferenceWithNestedReferences`` is an object with two keys ``$component_ref`` and
        ``$referenced_components`` (optional)
    -   Every Agent Spec Component type is modified to specify that it can be either a
        ``ComponentReference`` or the object with its properties
    -   Every Agent Spec Component type is modified to also have an optional properties
        ``$referenced_components``
    """
    if "$defs" in json_schema:
        all_component_types = [
            component_type
            for component_type in json_schema["$defs"]
            if Component.get_class_from_name(component_type)
        ]
        for component_type in all_component_types:
            if component_type_class := Component.get_class_from_name(component_type):
                json_schema["$defs"][component_type][
                    "x-abstract-component"
                ] = component_type_class._is_abstract
            json_schema["$defs"][f"Base{component_type}"] = json_schema["$defs"][component_type]

            base_def: JsonSchemaValue = json_schema["$defs"][f"Base{component_type}"]
            component_schema_def: Optional[JsonSchemaValue] = (
                base_def
                if "properties" in base_def
                else next((x for x in base_def.get("anyOf", []) if "properties" in x), {})
            )
            if component_schema_def:
                props = component_schema_def["properties"]
                props["$referenced_components"] = {"$ref": "#/$defs/ReferencedComponents"}
                props["component_type"] = {"const": component_type}
                component_schema_def["additionalProperties"] = False
            json_schema["$defs"][component_type] = {
                "anyOf": [
                    {"$ref": "#/$defs/ComponentReference"},
                    {"$ref": f"#/$defs/Base{component_type}"},
                ]
            }
        json_schema["$defs"]["ReferencedComponents"] = {
            "type": "object",
            "additionalProperties": {
                "anyOf": [
                    {"$ref": f"#/$defs/Base{component_type}"}
                    for component_type in all_component_types
                ]
                + [{"$ref": "#/$defs/ComponentReferenceWithNestedReferences"}]
            },
        }
        json_schema["$defs"]["ComponentReference"] = {
            "type": "object",
            "properties": {
                "$component_ref": {"type": "string"},
            },
            "additionalProperties": False,
            "required": ["$component_ref"],
        }
        json_schema["$defs"]["ComponentReferenceWithNestedReferences"] = {
            "type": "object",
            "properties": {
                "$component_ref": {"type": "string"},
                "$referenced_components": {"$ref": "#/$defs/ReferencedComponents"},
            },
            "additionalProperties": False,
            "required": ["$component_ref", "$referenced_components"],
        }
        if "$ref" in json_schema:
            del json_schema["$ref"]
            json_schema["anyOf"] = [
                {"$ref": "#/$defs/ComponentReferenceWithNestedReferences"},
                {"$ref": f"#/$defs/Base{root_type_name}"},
            ]
        elif "properties" in json_schema:
            schema_defs = json_schema.pop("$defs", {})
            schema_defs[root_type_name] = {
                "anyOf": [
                    {"$ref": "#/$defs/ComponentReference"},
                    {"$ref": f"#/$defs/Base{root_type_name}"},
                ]
            }
            schema_defs[f"Base{root_type_name}"] = json_schema
            schema_defs[f"Base{root_type_name}"]["properties"]["$referenced_components"] = {
                "$ref": "#/$defs/ReferencedComponents"
            }
            schema_defs[f"Base{root_type_name}"]["properties"]["component_type"] = {
                "const": root_type_name
            }
            referenced_components_any_of = schema_defs["ReferencedComponents"][
                "additionalProperties"
            ]["anyOf"]
            root_type_base_def = {"$ref": f"#/$defs/Base{root_type_name}"}
            if root_type_base_def not in referenced_components_any_of:
                referenced_components_any_of.append(root_type_base_def)

            json_schema = {
                "$defs": schema_defs,
                "anyOf": [
                    {"$ref": "#/$defs/ComponentReferenceWithNestedReferences"},
                    {"$ref": f"#/$defs/Base{root_type_name}"},
                ],
            }
        elif "anyOf" in json_schema:
            json_schema["anyOf"].append({"$ref": "#/$defs/ComponentReferenceWithNestedReferences"})
    return json_schema


def _add_agentspec_version_field(json_schema: JsonSchemaValue) -> JsonSchemaValue:
    """
    Modify the json schema to include the `agentspec_version` field in the top level component.
    """
    if "$defs" in json_schema and "anyOf" in json_schema:
        agentspec_version_json_schema = TypeAdapter(AgentSpecVersionEnum).json_schema()
        agentspec_versions_list = list(
            sorted(set(agentspec_version_json_schema["enum"]) - _LEGACY_AGENTSPEC_VERSIONS)
        )
        agentspec_version_json_schema["enum"] = agentspec_versions_list
        json_schema["$defs"][AgentSpecVersionEnum.__name__] = agentspec_version_json_schema
        all_component_types = [
            component_type["$ref"].split("/")[-1] for component_type in json_schema["anyOf"]
        ]
        for component_type in all_component_types:
            json_schema["$defs"][f"Versioned{component_type}"] = deepcopy(
                json_schema["$defs"][component_type]
            )
            if "properties" not in json_schema["$defs"][f"Versioned{component_type}"]:
                json_schema["$defs"][f"Versioned{component_type}"]["properties"] = {}
            json_schema["$defs"][f"Versioned{component_type}"]["properties"][
                AGENTSPEC_VERSION_FIELD_NAME
            ] = {"$ref": f"#/$defs/{AgentSpecVersionEnum.__name__}"}
        json_schema["anyOf"] = [
            {"$ref": f"#/$defs/Versioned{component_type}"} for component_type in all_component_types
        ]
    return json_schema


class ComponentWithIO(Component, abstract=True):
    """Base class for all components that have input and output schemas."""

    inputs: Optional[List["Property"]] = None
    """List of inputs accepted by this component"""

    outputs: Optional[List["Property"]] = None
    """List of outputs exposed by this component"""

    def model_post_init(self, __context: Any) -> None:
        """Override of the method used by Pydantic as post-init."""
        super().model_post_init(__context)
        if self.inputs is None:
            self.inputs = self._get_inferred_inputs()
        if self.outputs is None:
            self.outputs = self._get_inferred_outputs()

    @classmethod
    def _validate_no_duplicate_properties(cls, properties: List[Property]) -> None:
        property_title_counts = Counter(p.title for p in properties)
        duplicated_property_titles = [
            property_title for property_title, count in property_title_counts.items() if count > 1
        ]
        if len(duplicated_property_titles) > 0:
            raise ValueError(
                "Found multiple instances of properties (inputs or outputs) with the same title in "
                f"a {cls.__name__}. Please ensure titles are unique: {duplicated_property_titles}"
            )

    @classmethod
    def _validate_no_missing_property(
        cls, property_titles: Set[str], inferred_property_titles: Set[str]
    ) -> None:
        """
        Validate properties of ComponentWithIO.

        Raises when a ComponentWithIO expects some properties which are missing in the
        properties passed at initialization.
        """
        missing_property_titles = [
            title for title in inferred_property_titles if title not in property_titles
        ]
        if len(missing_property_titles) > 0:
            raise ValueError(
                f"The {cls.__name__} component expected a property titled `{missing_property_titles[0]}`, but none"
                f" of the passed properties have this title: {list(property_titles)}."
            )

    @classmethod
    def _validate_no_extra_property(
        cls, property_titles: Set[str], inferred_property_titles: Set[str]
    ) -> None:
        """
        Validate properties of ComponentWithIO.

        Raises when a ComponentWithIO is initialized by passing extra properties that do not match
        the expected properties of the component.
        """
        extra_property_titles = [
            title for title in property_titles if title not in inferred_property_titles
        ]
        if len(extra_property_titles) > 0:
            if len(inferred_property_titles) == 0:
                raise ValueError(
                    f"The {cls.__name__} component received a property titled `{extra_property_titles[0]}`, but "
                    "did not expect any properties"
                )
            raise ValueError(
                f"The {cls.__name__} component received a property titled `{extra_property_titles[0]}`, but "
                f"expected only properties with the titles: {list(inferred_property_titles)}."
            )

    def _get_inferred_inputs(self) -> List[Property]:
        """
        Return inputs inferred based on the configuration of the components.

        This method is helpful to save time from assistant developers who don't need to always
        specify the inputs explicitly. For some components, this method can be made to allow
        renaming of inputs by copying the names of inputs specified by assistant developers. It may
        also impose names and not allow renaming.
        """
        return getattr(self, "inputs", []) or []

    def _get_inferred_outputs(self) -> List[Property]:
        """
        Return outputs inferred based on the configuration of the components.

        This method is helpful to save time from assistant developers who don't need to always
        specify the outputs explicitly. For some components, this method can be made to allow
        renaming of outputs by copying the names of inputs specified by assistant developers. It
        may also impose names and not allow renaming.
        """
        return getattr(self, "outputs", []) or []

    @model_validator_with_error_accumulation
    def _validate_inputs(self) -> Self:
        inferred_inputs = self._get_inferred_inputs()
        if self.inputs is None:
            raise ValueError("Something went wrong, inputs should not be None")
        self._validate_no_duplicate_properties(self.inputs)
        inputs_by_title = {p.title: p for p in self.inputs}
        inferred_inputs_by_title = {p.title: p for p in inferred_inputs}
        input_titles = set(inputs_by_title)
        inferred_input_titles = set(inferred_inputs_by_title)
        self._validate_no_missing_property(input_titles, inferred_input_titles)
        self._validate_no_extra_property(input_titles, inferred_input_titles)
        return self

    @model_validator_with_error_accumulation
    def _validate_outputs(self) -> Self:
        inferred_outputs = self._get_inferred_outputs()
        if self.outputs is None:
            raise ValueError("Something went wrong, outputs should not be None")
        self._validate_no_duplicate_properties(self.outputs)
        outputs_by_title = {p.title: p for p in self.outputs}
        inferred_outputs_by_title = {p.title: p for p in inferred_outputs}
        output_titles = set(outputs_by_title)
        inferred_output_titles = set(inferred_outputs_by_title)
        self._validate_no_missing_property(output_titles, inferred_output_titles)
        self._validate_no_extra_property(output_titles, inferred_output_titles)
        return self
