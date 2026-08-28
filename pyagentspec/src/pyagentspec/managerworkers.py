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
from pyagentspec.property import Property, properties_have_same_type
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

    def _get_inferred_inputs(self) -> List[Property]:
        # Per the language spec, the inputs of a ManagerWorkers are the inputs of its
        # group manager (same name and type): the manager drives the conversation.
        return (
            self.group_manager.inputs or []
            if getattr(self, "group_manager", None)
            and self.min_agentspec_version >= AgentSpecVersionEnum.v26_4_0
            else []
        )

    def _get_inferred_outputs(self) -> List[Property]:
        # Symmetric with the inferred inputs: the group manager's outputs.
        return (
            self.group_manager.outputs or []
            if getattr(self, "group_manager", None)
            and self.min_agentspec_version >= AgentSpecVersionEnum.v26_4_0
            else []
        )

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        min_version = super()._infer_min_agentspec_version_from_configuration()
        # ManagerWorkers I/O matching was introduced in 26.4.0. Omitted I/O
        # inherits from the group manager; explicitly empty I/O is legacy-only.
        manager = getattr(self, "group_manager", None)
        inherits_manager_io = bool(
            manager
            and (
                ("inputs" not in self.model_fields_set and manager.inputs)
                or ("outputs" not in self.model_fields_set and manager.outputs)
            )
        )
        if inherits_manager_io or getattr(self, "inputs", []) or getattr(self, "outputs", []):
            min_version = max(min_version, AgentSpecVersionEnum.v26_4_0)
        return min_version

    def _infer_max_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        max_version = super()._infer_max_agentspec_version_from_configuration()
        # Before 26.4.0 a ManagerWorkers did not inherit its manager's I/O.
        manager = getattr(self, "group_manager", None)
        inherits_manager_io = bool(
            manager
            and (
                ("inputs" not in self.model_fields_set and manager.inputs)
                or ("outputs" not in self.model_fields_set and manager.outputs)
            )
        )
        if manager and (manager.inputs or manager.outputs) and not inherits_manager_io and not (
            self.inputs or self.outputs
        ):
            max_version = min(max_version, AgentSpecVersionEnum.v26_3_0)
        return max_version

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

    @model_validator_with_error_accumulation
    def _validate_ios_match_group_manager_ios(self) -> Self:
        # Per the language spec, the I/Os of a ManagerWorkers must be the I/Os of its
        # group manager, same name and type. The base ComponentWithIO validators
        # already enforce matching titles; use the shared property helper here so
        # nested JSON Schema types are compared correctly as well.
        for kind, own_properties, manager_properties, explicitly_provided in (
            ("input", self.inputs or [], self.group_manager.inputs or [], "inputs"),
            ("output", self.outputs or [], self.group_manager.outputs or [], "outputs"),
        ):
            if explicitly_provided not in self.model_fields_set:
                continue
            manager_property_by_title = {p.title: p for p in manager_properties}
            for own_property in own_properties:
                manager_property = manager_property_by_title.get(own_property.title)
                if manager_property is not None and not properties_have_same_type(
                    own_property, manager_property
                ):
                    raise ValueError(
                        f"The {kind}s of a `ManagerWorkers` must match the {kind}s of its "
                        f"group manager (same name and type), but {kind} "
                        f"`{own_property.title}` has a different type from the group manager."
                    )
        return self
