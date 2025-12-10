# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines an Agent Spec component"""

from typing import List

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema
from typing_extensions import Self

from pyagentspec.agenticcomponent import AgenticComponent
from pyagentspec.validation_helpers import model_validator_with_error_accumulation
from pyagentspec.versioning import AgentSpecVersionEnum


class ManagerWorkers(AgenticComponent):
    """
    Defines a ``ManagerWorkers`` conversational component.

    A ``ManagerWorkers`` is a multi-agent conversational component in which a group manager
    assigns tasks to the workers. The group manager and workers can be instantiated from
    any ``AgenticComponent`` type.

    Examples
    --------
    >>> from pyagentspec.agent import Agent
    >>> from pyagentspec.managerworkers import ManagerWorkers
    >>> manager_agent = Agent(
    ...     name="manager_agent",
    ...     description="Agent that manages a group of math agents",
    ...     llm_config=llm_config,
    ...     system_prompt="You are the manager of a group of math agents"
    ... )
    >>> multiplication_agent = Agent(
    ...     name="multiplication_agent",
    ...     description="Agent that can do multiplication",
    ...     llm_config=llm_config,
    ...     system_prompt="You can do multiplication."
    ... )
    >>> division_agent = Agent(
    ...     name="division_agent",
    ...     description="Agent that can do division",
    ...     llm_config=llm_config,
    ...     system_prompt="You can do division."
    ... )
    >>> group = ManagerWorkers(
    ...     name="managerworkers",
    ...     group_manager=manager_agent,
    ...     workers=[multiplication_agent, division_agent],
    ... )

    """

    group_manager: AgenticComponent
    """An agentic component (e.g. Agent) that is used as the group manager,
    responsible for coordinating and assigning tasks to the workers."""
    workers: List[AgenticComponent]
    """List of agentic components that participate in the group. There should be at least one agentic component in the list."""

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v25_4_2, init=False, exclude=True
    )

    @model_validator_with_error_accumulation
    def _validate_one_or_more_workers(self) -> Self:
        if len(self.workers) == 0:
            raise ValueError(
                "Cannot define a `ManagerWorkers` with no worker. Use an `Agent` instead."
            )

        return self

    @model_validator_with_error_accumulation
    def _validate_group_manager_is_not_included_as_a_worker(self) -> Self:
        if any(self.group_manager is agent for agent in self.workers):
            raise ValueError("Group manager cannot be a worker.")
        return self
