# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines several Agent Spec components."""

from typing import List, Tuple

from pydantic import Field
from typing_extensions import Self

from pyagentspec.agenticcomponent import AgenticComponent
from pyagentspec.validation_helpers import model_validator_with_error_accumulation
from pyagentspec.versioning import AgentSpecVersionEnum


class Swarm(AgenticComponent):
    """
    Defines a ``Swarm`` conversational component.

    A ``Swarm`` is a multi-agent conversational component in which each agent determines
    the next agent to be executed, based on a list of pre-defined relationships.
    Agents in Swarm can be any ``AgenticComponent``.

    Examples
    --------
    >>> from pyagentspec.agent import Agent
    >>> from pyagentspec.swarm import Swarm
    >>> addition_agent = Agent(name="addition_agent", description="Agent that can do additions", llm_config=llm_config, system_prompt="You can do additions.")
    >>> multiplication_agent = Agent(name="multiplication_agent", description="Agent that can do multiplication", llm_config=llm_config, system_prompt="You can do multiplication.")
    >>> division_agent = Agent(name="division_agent", description="Agent that can do division", llm_config=llm_config, system_prompt="You can do division.")
    >>>
    >>> swarm = Swarm(
    ...     name="swarm",
    ...     first_agent=addition_agent,
    ...     relationships=[
    ...         (addition_agent, multiplication_agent),
    ...         (addition_agent, division_agent),
    ...         (multiplication_agent, division_agent),
    ...     ]
    ... )

    """

    first_agent: AgenticComponent
    """The first agent that interacts with the human user (before any potential handoff occurs within the Swarm)."""
    relationships: List[Tuple[AgenticComponent, AgenticComponent]]
    """Determine the list of allowed interactions in the ``Swarm``.
    Each element in the list is a tuple ``(caller_agent, recipient_agent)``
    specifying that the ``caller_agent`` can query the ``recipient_agent``.
    """
    handoff: bool = True
    """Controls whether agents in the Swarm can transfer the user conversation between each other.

    When ``False``:
        Agents can only communicate with one another, and the ``first_agent`` remains the sole agent directly interacting with the user throughout the conversation.

    When ``True``:
        Agents can *handoff* the conversation — transferring the entire message history between the user and one agent to another agent within the Swarm.
        This allows different agents to take over the user interaction while maintaining context.
        Agents can still exchange messages with each other as in ``handoff=False`` mode.
    """

    @model_validator_with_error_accumulation
    def _validate_one_or_more_relations(self) -> Self:
        if len(self.relationships) == 0:
            raise ValueError(
                "Cannot define a `Swarm` with no relationships between the agents. "
                "Use an `Agent` instead."
            )

        return self

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        return AgentSpecVersionEnum.v25_4_2
