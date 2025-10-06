# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""This module defines several Agent Spec components."""

from typing import List

from pydantic import Field
from typing_extensions import Self

from pyagentspec._utils import beta
from pyagentspec.agent import Agent
from pyagentspec.component import ComponentWithIO
from pyagentspec.validation_helpers import model_validator_with_error_accumulation


@beta
class Swarm(ComponentWithIO):
    """
    Defines a ``Swarm`` conversational component.

    A ``Swarm`` is a multi-agent conversational component in which each agent determines
    the next agent to be executed, based on a list of pre-defined relationships.

    .. warning::
        The ``Swarm`` is currently in beta and may undergo significant changes.
        The API and behaviour are not guaranteed to be stable and may change in future versions.

    Parameters
    ----------
    first_agent:
        What is the first ``Agent`` to interact with the human user.
    relationships:
        Determine the list of allowed interactions in the ``Swarm``.
        Each element in the list is a tuple ``(caller_agent, recipient_agent)``
        specifying that the ``caller_agent`` can query the ``recipient_agent``.
    """

    first_agent: Agent
    relationships: List[List[Agent]] = Field(default_factory=list)

    @model_validator_with_error_accumulation
    def _validate_one_or_more_relations(self) -> Self:
        if len(self.relationships) == 0:
            raise ValueError(
                "Cannot define a `Swarm` with no relationships between the agents. "
                "Use an `Agent` instead."
            )

        return self
