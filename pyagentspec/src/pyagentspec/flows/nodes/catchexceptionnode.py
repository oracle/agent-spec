# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the CatchExceptionNode component."""

from typing import ClassVar, List

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema
from typing_extensions import Self

from pyagentspec.flows.flow import Flow
from pyagentspec.flows.node import Node
from pyagentspec.flows.nodes.endnode import EndNode
from pyagentspec.property import (
    NullProperty,
    Property,
    StringProperty,
    UnionProperty,
    _empty_default,
)
from pyagentspec.validation_helpers import model_validator_with_error_accumulation
from pyagentspec.versioning import AgentSpecVersionEnum


class CatchExceptionNode(Node):
    """
    Node to execute a Flow and catch exceptions.

    - If no exception is caught, the node will transition to the branches of its subflow.
    - If an exception is caught, it will transition to an exception branch.

    Inputs
    ------
    Same as the inputs from the ``subflow``.

    Outputs
    -------

    - The outputs of the ``subflow``.
      If an exception is raised, the default values of each output property are used.
    - An additional output named ``caught_exception_info`` with type ``string | null``
      and default value ``null``. Executors may populate it with a non-sensitive
      error description when an exception is caught.

    Branches
    --------

    - The branches of the ``subflow``
    - One additional branch named ``caught_exception_branch``

    Security Considerations
    -----------------------

    See security considerations regarding exception catching in
    the :ref:`Security Considerations <securitycatchexceptionnode>`

    """

    CAUGHT_EXCEPTION_BRANCH: ClassVar[str] = "caught_exception_branch"
    """Name of the branch used when an exception is caught."""

    DEFAULT_EXCEPTION_INFO_VALUE: ClassVar[str] = "caught_exception_info"
    """Name of the output property containing exception details."""

    subflow: Flow
    """Flow to execute and catch errors from."""

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v26_2_0, init=False, exclude=True
    )

    @model_validator_with_error_accumulation
    def _validate_subflow_has_default_values_in_outputs(self) -> Self:
        if (
            not hasattr(self, "subflow")
            or not hasattr(self.subflow, "outputs")
            or not hasattr(self, "outputs")
        ):
            # partial construction not completed, stop validation
            return self

        subflow_outputs = self.subflow.outputs or []
        node_outputs = self.outputs or []
        # ^ note that those are either inferred or overriden by the user because
        # ComponentWithIO.model_post_init is called before the validation methods

        node_output_titles = {p.title for p in node_outputs}
        subflow_output_titles = {p.title for p in subflow_outputs}
        if node_output_titles != {*subflow_output_titles, self.DEFAULT_EXCEPTION_INFO_VALUE}:
            # when provided by the user, node outputs should match subflow outputs
            raise ValueError(
                f"CatchExceptionNode '{self.name}': provided outputs must have the same names as subflow outputs. "
                f"Provided: {sorted(node_output_titles)}, Subflow: {sorted(subflow_output_titles)}"
            )

        for property_ in node_outputs:
            if getattr(property_, "default", _empty_default) is _empty_default:
                raise ValueError(
                    f"CatchExceptionNode '{self.name}': output '{property_.title}' "
                    "must define a default value to be used when exceptions are caught."
                )
        return self

    @model_validator_with_error_accumulation
    def _validate_subflow_branches_do_not_conflict_with_exception_branch(self) -> Self:
        if not hasattr(self, "subflow"):
            return self
        # Gather branch names from EndNodes of the subflow
        subflow_branch_names = {
            node.branch_name for node in self.subflow.nodes if isinstance(node, EndNode)
        }
        if CatchExceptionNode.CAUGHT_EXCEPTION_BRANCH in subflow_branch_names:
            raise ValueError(
                f"CatchExceptionNode '{self.name}': subflow contains a branch named "
                f"'{CatchExceptionNode.CAUGHT_EXCEPTION_BRANCH}', which conflicts with the exception branch name."
            )
        return self

    @model_validator_with_error_accumulation
    def _validate_subflow_outputs_do_not_conflict_with_exception_info(self) -> Self:
        if not hasattr(self, "subflow"):
            return self
        for property_ in getattr(self, "subflow").outputs or []:
            if property_.title == CatchExceptionNode.DEFAULT_EXCEPTION_INFO_VALUE:
                raise ValueError(
                    f"CatchExceptionNode '{self.name}': subflow output '{property_.title}' "
                    "conflicts with the reserved exception information output name."
                )
        return self

    def _get_inferred_branches(self) -> List[str]:
        if hasattr(self, "subflow"):
            end_node_branches = sorted(
                list({node.branch_name for node in self.subflow.nodes if isinstance(node, EndNode)})
            )
            return [CatchExceptionNode.CAUGHT_EXCEPTION_BRANCH, *end_node_branches]
        return [CatchExceptionNode.CAUGHT_EXCEPTION_BRANCH]

    def _get_inferred_inputs(self) -> List[Property]:
        return (self.subflow.inputs or []) if hasattr(self, "subflow") else []

    def _get_inferred_outputs(self) -> List[Property]:
        subflow_outputs = (self.subflow.outputs or []) if hasattr(self, "subflow") else []
        node_outputs = getattr(self, "outputs", None) or subflow_outputs
        # ^ node outputs override subflow outputs when present
        titles = {property_.title for property_ in node_outputs}
        if self.DEFAULT_EXCEPTION_INFO_VALUE in titles:
            # ^ validators check that the subflow outputs to not conflict
            return node_outputs
        return [
            *node_outputs,
            UnionProperty(
                title=self.DEFAULT_EXCEPTION_INFO_VALUE,
                any_of=[StringProperty(), NullProperty()],
                default=None,
            ),
        ]
