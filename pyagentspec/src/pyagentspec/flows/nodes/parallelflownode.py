# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines several Agent Spec components."""

from typing import Dict, List, Set

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema
from typing_extensions import Self

from pyagentspec.flows.flow import Flow
from pyagentspec.flows.node import Node
from pyagentspec.property import (
    Property,
    deduplicate_properties_by_title_and_type,
    properties_have_same_type,
)
from pyagentspec.validation_helpers import model_validator_with_error_accumulation
from pyagentspec.versioning import AgentSpecVersionEnum


class ParallelFlowNode(Node):
    """The parallel flow node executes multiple subflows in parallel.

    - **Inputs**
        Inferred from the inner structure. It's the union of the sets of inputs of the inner flows.
        Inputs of different inner flows that have the same name are merged if they have the same type.

    - **Outputs**
        Inferred from the inner structure. It's the union of the outputs of the inner flows.
        Outputs of different inner flows that have the same name are not allowed.

    - **Branches**
        One, the default next.

    Examples
    --------

    """

    subflows: List[Flow] = Field(default_factory=list)
    """The flows that should be executed in parallel"""

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v25_4_2, init=False, exclude=True
    )

    def _get_inferred_inputs(self) -> List[Property]:
        if self.inputs is not None:
            return self.inputs
        all_inputs: List[Property] = []
        for subflow in self.subflows:
            all_inputs.extend(subflow.inputs or [])
        return deduplicate_properties_by_title_and_type(all_inputs)

    def _get_inferred_outputs(self) -> List[Property]:
        if self.outputs is not None:
            return self.outputs
        all_outputs: List[Property] = []
        # We gather all the outputs, also if they have the same name,
        # validation will take care of raising the error
        for subflow in self.subflows:
            all_outputs.extend(subflow.outputs or [])
        return all_outputs

    @model_validator_with_error_accumulation
    def _validate_inputs_with_same_name_and_different_type_do_not_exist(self) -> Self:
        """Check that there aren't inputs with the same name and different type"""
        union_of_inputs: Dict[str, Property] = dict()
        for input_property in getattr(self, "inputs", []):
            if input_property.title not in union_of_inputs:
                union_of_inputs[input_property.title] = input_property
            elif not properties_have_same_type(
                input_property, union_of_inputs[input_property.title]
            ):
                raise ValueError(
                    f"Two subflows of ParallelFlowNode `{getattr(self, 'name', '')}` have inputs with "
                    f"the same name `{input_property.title}`, but different types:\n"
                    f"{union_of_inputs[input_property.title].json_schema}\n"
                    f"{input_property.json_schema}\n"
                )
        return self

    @model_validator_with_error_accumulation
    def _validate_outputs_with_same_name_do_not_exist(self) -> Self:
        """Check that there aren't outputs with the same name"""
        union_of_outputs: Set[str] = set()
        for output_property in getattr(self, "outputs", []):
            if output_property.title in union_of_outputs:
                raise ValueError(
                    f"Two subflows of ParallelFlowNode `{getattr(self, 'name', '')}` have outputs with "
                    f"the same name `{output_property.title}`."
                )
            union_of_outputs.add(output_property.title)
        return self
