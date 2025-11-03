# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines data flow edges that can be used to propagate values between flow nodes."""
from pydantic import SerializeAsAny
from typing_extensions import Self

from pyagentspec.component import Component
from pyagentspec.flows.node import Node
from pyagentspec.property import property_is_castable_to
from pyagentspec.validation_helpers import model_validator_with_error_accumulation


class DataFlowEdge(Component):
    """
    A data flow edge specifies how the output of a node propagates as input of another node.

    An outputs can be propagated as input of several nodes.
    """

    source_node: SerializeAsAny[Node]  # See for context
    """The instance of the source Node"""
    source_output: str
    """The name of the property among the source node outputs that should be connected"""
    destination_node: SerializeAsAny[Node]  # See for context
    """The instance of the destination Node"""
    destination_input: str
    """The name of the property among the destination node inputs that should be connected"""

    @model_validator_with_error_accumulation
    def _validate_source_and_destination_names_are_in_node_properties_with_right_type(
        self,
    ) -> Self:

        edge_name = getattr(self, "name", "")
        source_node = getattr(self, "source_node", None)
        source_output = getattr(self, "source_output", None)
        destination_node = getattr(self, "destination_node", None)
        destination_input = getattr(self, "destination_input", None)

        if (
            source_node is None
            or source_output is None
            or destination_node is None
            or destination_input is None
        ):
            return self

        source_property = next(
            (
                property_
                for property_ in (source_node.outputs or [])
                if property_.title == source_output
            ),
            None,
        )
        if source_property is None:
            raise ValueError(
                f"Flow data connection named `{edge_name}` is connected to a property "
                f"named `{source_output}` of the source node `{source_node.name}`, "
                f"but the node does not have any property with that name."
            )

        destination_property = next(
            (
                property_
                for property_ in (destination_node.inputs or [])
                if property_.title == destination_input
            ),
            None,
        )
        if destination_property is None:
            raise ValueError(
                f"Flow data connection named `{edge_name}` is connected to a property "
                f"named `{destination_input}` of the destination node `{destination_node.name}`, "
                f"but the node does not have any property with that name."
            )

        if not property_is_castable_to(source_property, destination_property):
            raise ValueError(
                f"Flow data connection named `{edge_name}` connects two properties "
                f"with incompatible types: `{source_property}` and `{destination_property}`."
            )

        return self
