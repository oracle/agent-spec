# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines several Agent Spec components."""

from enum import Enum
from typing import Any, List, Tuple, Union

from pydantic import Field, model_validator
from pydantic.json_schema import SkipJsonSchema
from typing_extensions import Self

from pyagentspec.agenticcomponent import AgenticComponent
from pyagentspec.component import SerializeAsEnum
from pyagentspec.validation_helpers import model_validator_with_error_accumulation
from pyagentspec.versioning import AgentSpecVersionEnum


class HandoffMode(str, Enum):
    """
    Controls how agents in a Swarm may delegate work to one another.

    This setting determines whether an agent is equipped with:

      * *send_message* — a tool for asking another agent to perform a sub-task and reply back.

      * *handoff_conversation* — a tool for transferring the full user–agent conversation to another agent.

    Depending on the selected mode, agents have different capabilities for delegation and collaboration.
    """

    NEVER = "never"
    """
    Agent is not equipped with the *handoff_conversation* tool.

    Delegation is limited to message-passing:

      * Agents *can* use *send_message* to request a sub-task from another agent.

      * Agents *cannot* transfer the user conversation to another agent.

    As a consequence, the ``first_agent`` always remains the primary point of contact with the user.
    """

    OPTIONAL = "optional"
    """
    Agents receive **both** *handoff_conversation* and *send_message* tool.

    This gives agents full flexibility:

      * They may pass a message to another agent and wait for a reply.

      * Or they may fully hand off the user conversation to another agent.

    Use this mode when you want agents to intelligently choose the most natural delegation strategy.
    """

    ALWAYS = "always"
    """
    Agents receive **only** the *handoff_conversation* tool.

    Message-passing is disabled:

      * Agents *must* hand off the user conversation when delegating work.

      * They cannot simply send a message and receive a response.

    This mode enforces a strict chain-of-ownership: whenever an agent involves another agent,
    it must transfer the full dialogue context. The next agent can either respond directly to the user
    or continue handing off the conversation to another agent.
    """


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
    handoff: Union[bool, SerializeAsEnum[HandoffMode]] = HandoffMode.OPTIONAL
    """Specifies how agents are allowed to delegate work. See ``HandoffMode`` for full details.

    ``HandoffMode.NEVER``: Agents can only use *send_message*. The ``first_agent`` is the only agent that can interact with the user;

    ``HandoffMode.OPTIONAL``: Agents may either send messages or fully hand off the conversation. This provides the most flexibility and often results in natural delegation;

    ``HandoffMode.ALWAYS``: Agents cannot send messages to other agents. Any delegation must be performed through *handoff_conversation*;

    A key benefit of using Handoff is the reduced response latency: While talking to other agents increases the "distance"
    between the human user and the current agent, transferring a conversation to another agent keeps this distance unchanged
    (i.e. the agent interacting with the user is different but the user is still the same). However, transferring the full conversation might increase the token usage.
    """

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v25_4_2, init=False, exclude=True
    )

    @model_validator(mode="before")
    def _raise_warning_if_handoff_is_bool(cls: Self, values: Any) -> Any:
        import warnings

        handoff = values.get("handoff")

        if isinstance(handoff, bool):
            warnings.warn(
                "Passing `handoff` as a boolean is deprecated and will be removed in a "
                "future release. Please use `HandoffMode` instead. The provided boolean "
                "value will be automatically converted to the corresponding `HandoffMode`.",
                DeprecationWarning,
            )

            values["handoff"] = HandoffMode.OPTIONAL if handoff else HandoffMode.NEVER

        return values

    @model_validator_with_error_accumulation
    def _validate_one_or_more_relations(self) -> Self:
        if len(self.relationships) == 0:
            raise ValueError(
                "Cannot define a `Swarm` with no relationships between the agents. "
                "Use an `Agent` instead."
            )

        return self
