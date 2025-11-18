# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines several Agent Spec components."""

from typing import Any, ClassVar, List

from pydantic import Field
from typing_extensions import Self

from pyagentspec.component import ComponentWithIO
from pyagentspec.validation_helpers import model_validator_with_error_accumulation


class Node(ComponentWithIO, abstract=True):
    """Base class for all nodes that can be put inside a flow."""

    DEFAULT_NEXT_BRANCH: ClassVar[str] = "next"
    """Name used for the default branch"""

    branches: List[str] = Field(default_factory=list)
    """The list of outgoing branch names that the node will expose"""

    def model_post_init(self, __context: Any) -> None:
        """Override of the method used by ComponentWithIO as post-init."""
        super().model_post_init(__context)
        if not self.branches:
            # Sorting below is just a nice optimization to ensure consistency in the order of
            # branches
            self.branches = sorted(set(self._get_inferred_branches()))

    @model_validator_with_error_accumulation
    def _validate_branches(self) -> Self:
        if len(self.branches) > len(set(self.branches)):
            raise ValueError("The branches of a node should have no duplicate")
        inferred_branches = self._get_inferred_branches()
        if self.branches and set(self.branches) != set(inferred_branches):
            raise ValueError(
                f"Specified branches {self.branches} does not match expected branches "
                f"{inferred_branches}"
            )
        return self

    def _get_inferred_branches(self) -> List[str]:
        return [Node.DEFAULT_NEXT_BRANCH]
