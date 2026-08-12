# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the deserialization plugin for Pydantic Components."""

from typing import Any, Dict, List, Mapping, Tuple, Type, cast

from pydantic import BaseModel, ValidationError
from pydantic_core import InitErrorDetails

from pyagentspec.component import Component
from pyagentspec.serialization.deserializationcontext import DeserializationContext
from pyagentspec.serialization.deserializationplugin import ComponentDeserializationPlugin
from pyagentspec.validation_helpers import PyAgentSpecErrorDetails


class PydanticComponentDeserializationPlugin(ComponentDeserializationPlugin):
    """Deserialization plugin for Pydantic Components."""

    def __init__(self, component_types_and_models: Mapping[str, Type[BaseModel]]) -> None:
        """
        Instantiate a Pydantic deserialization plugin.

        component_types_and_models:
            Mapping of component classes by their class name.
        """
        self._supported_component_types = list(component_types_and_models.keys())
        self.component_types_and_models = dict(component_types_and_models)

    @property
    def plugin_name(self) -> str:
        """Return the plugin name."""
        return "PydanticComponentPlugin"

    @property
    def plugin_version(self) -> str:
        """Return the plugin version."""
        from pyagentspec import __version__

        return __version__

    def supported_component_types(self) -> List[str]:
        """Indicate what component types the plugin supports."""
        return self._supported_component_types

    def deserialize(
        self, serialized_component: Dict[str, Any], deserialization_context: DeserializationContext
    ) -> Component:
        """Deserialize a serialized Pydantic model."""
        component, validation_errors = self._resolve_content_and_build(
            serialized_component=serialized_component,
            deserialization_context=deserialization_context,
        )
        if len(validation_errors) > 0:
            line_errors = [
                InitErrorDetails(
                    type=e.type,
                    loc=e.loc,
                    input=(),
                )
                for e in validation_errors
            ]
            raise ValidationError.from_exception_data(
                title=component.__class__.__name__,
                line_errors=line_errors,
            )
        return cast(Component, component)

    def _partial_deserialize(
        self, serialized_component: Dict[str, Any], deserialization_context: DeserializationContext
    ) -> Tuple[Component, List[PyAgentSpecErrorDetails]]:
        """Deserialize a serialized Pydantic model, including incomplete ones. Uses model_construct."""
        component, validation_errors = self._resolve_content_and_build(
            serialized_component=serialized_component,
            deserialization_context=deserialization_context,
        )
        return cast(Component, component), validation_errors

    def _resolve_content_and_build(
        self, serialized_component: Dict[str, Any], deserialization_context: DeserializationContext
    ) -> Tuple[BaseModel, List[PyAgentSpecErrorDetails]]:
        # resolve the content leveraging the pydantic annotations
        all_validation_errors: List[PyAgentSpecErrorDetails] = []
        component_type = deserialization_context.get_component_type(serialized_component)
        model_class = self.component_types_and_models[component_type]
        resolved_content: Dict[str, Any] = {}
        for field_name, field_info in model_class.model_fields.items():
            annotation = field_info.annotation
            if field_name in serialized_component:
                # We always do partial build, and we raise in the caller function
                # if we are not allowed to have validation issues
                resolved_content[field_name], nested_validation_errors = (
                    deserialization_context._partial_load_field(
                        serialized_component[field_name], annotation
                    )
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

        try:
            return model_class(**resolved_content), all_validation_errors
        except ValidationError as e:
            all_validation_errors.extend(
                [
                    PyAgentSpecErrorDetails(
                        type=error_details["type"],
                        msg=error_details["msg"],
                        loc=error_details["loc"],
                    )
                    for error_details in e.errors()
                ]
            )
            return model_class.model_construct(**resolved_content), all_validation_errors
