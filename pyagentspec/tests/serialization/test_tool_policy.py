# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Tests for ToolPolicy models and serialization."""

import pytest

from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.tools import ServerTool, Tool
from pyagentspec.tools.toolpolicy import (
    ApprovalGuard,
    JustificationGuard,
    RateLimitGuard,
    ToolPolicy,
)
from pyagentspec.versioning import AgentSpecVersionEnum


def make_tool_with_policy():
    return ServerTool(
        name="delete_record",
        description="Permanently delete a database record",
        id="tool_policy_test",
        inputs=[],
        outputs=[],
        tool_policy=ToolPolicy(
            data_classification="restricted",
            requires_justification=True,
            guards=[
                RateLimitGuard(max_calls=10, window_seconds=3600, on_violation="block"),
                ApprovalGuard(condition="always", on_violation="escalate"),
            ],
        ),
    )


def make_tool_with_conditional_approval():
    return ServerTool(
        name="transfer_funds",
        description="Transfer money between accounts",
        id="conditional_tool",
        inputs=[],
        outputs=[],
        tool_policy=ToolPolicy(
            data_classification="confidential",
            requires_justification=True,
            guards=[
                RateLimitGuard(max_calls=10, window_seconds=3600),
                ApprovalGuard(
                    condition="input_contains",
                    field="destination_account",
                    value="external:",
                    on_violation="escalate",
                ),
            ],
        ),
    )


def make_tool_with_allowed_callers():
    return ServerTool(
        name="audit_log",
        description="Access audit log entries",
        id="caller_restricted_tool",
        inputs=[],
        outputs=[],
        tool_policy=ToolPolicy(
            data_classification="internal",
            allowed_callers=["agent-supervisor", "agent-compliance"],
        ),
    )


class TestToolPolicyModel:
    def test_basic_policy_creation(self):
        policy = ToolPolicy(
            data_classification="confidential",
            requires_justification=True,
        )
        assert policy.data_classification == "confidential"
        assert policy.requires_justification is True
        assert policy.guards == []
        assert policy.allowed_callers is None

    def test_rate_limit_guard(self):
        guard = RateLimitGuard(max_calls=5, window_seconds=60)
        assert guard.type == "rate_limit"
        assert guard.max_calls == 5
        assert guard.window_seconds == 60
        assert guard.on_violation == "block"

    def test_approval_guard_always(self):
        guard = ApprovalGuard(condition="always")
        assert guard.type == "require_approval"
        assert guard.condition == "always"
        assert guard.on_violation == "escalate"

    def test_approval_guard_conditional(self):
        guard = ApprovalGuard(
            condition="input_contains",
            field="amount",
            value="1000",
        )
        assert guard.field == "amount"
        assert guard.value == "1000"

    def test_approval_guard_conditional_missing_field_raises(self):
        with pytest.raises(ValueError, match="`field` is required"):
            ApprovalGuard(condition="input_contains", value="test")

    def test_approval_guard_conditional_missing_value_raises(self):
        with pytest.raises(ValueError, match="`value` is required"):
            ApprovalGuard(condition="input_contains", field="amount")

    def test_justification_guard(self):
        guard = JustificationGuard()
        assert guard.type == "require_justification"
        assert guard.on_violation == "block"

    def test_policy_with_all_guard_types(self):
        policy = ToolPolicy(
            data_classification="restricted",
            guards=[
                RateLimitGuard(max_calls=3, window_seconds=300),
                ApprovalGuard(condition="always"),
                JustificationGuard(),
            ],
        )
        assert len(policy.guards) == 3
        assert policy.guards[0].type == "rate_limit"
        assert policy.guards[1].type == "require_approval"
        assert policy.guards[2].type == "require_justification"


class TestToolPolicyOnTool:
    def test_tool_with_policy_instantiation(self):
        tool = make_tool_with_policy()
        assert tool.tool_policy is not None
        assert tool.tool_policy.data_classification == "restricted"
        assert len(tool.tool_policy.guards) == 2

    def test_tool_without_policy(self):
        tool = ServerTool(name="simple", description="no policy", id="s1", inputs=[], outputs=[])
        assert tool.tool_policy is None

    def test_tool_policy_infers_min_version(self):
        tool = make_tool_with_policy()
        inferred = tool._infer_min_agentspec_version_from_configuration()
        assert inferred >= AgentSpecVersionEnum.v26_2_0


class TestToolPolicySerialization:
    def test_serialize_tool_with_policy(self):
        tool = make_tool_with_policy()
        serializer = AgentSpecSerializer()
        yaml_output = serializer.to_yaml(tool)
        assert "tool_policy" in yaml_output
        assert "data_classification" in yaml_output
        assert "restricted" in yaml_output
        assert "rate_limit" in yaml_output
        assert "require_approval" in yaml_output

    def test_roundtrip_tool_with_policy(self):
        tool = make_tool_with_policy()
        serializer = AgentSpecSerializer()
        deserializer = AgentSpecDeserializer()
        yaml_output = serializer.to_yaml(tool)
        restored = deserializer.from_yaml(yaml_output)
        assert isinstance(restored, Tool)
        assert restored.tool_policy is not None
        assert restored.tool_policy.data_classification == "restricted"
        assert restored.tool_policy.requires_justification is True
        assert len(restored.tool_policy.guards) == 2

    def test_roundtrip_conditional_approval(self):
        tool = make_tool_with_conditional_approval()
        serializer = AgentSpecSerializer()
        deserializer = AgentSpecDeserializer()
        yaml_output = serializer.to_yaml(tool)
        restored = deserializer.from_yaml(yaml_output)
        assert isinstance(restored, Tool)
        assert restored.tool_policy is not None
        approval_guard = restored.tool_policy.guards[1]
        assert approval_guard.type == "require_approval"
        assert approval_guard.condition == "input_contains"
        assert approval_guard.field == "destination_account"
        assert approval_guard.value == "external:"

    def test_roundtrip_allowed_callers(self):
        tool = make_tool_with_allowed_callers()
        serializer = AgentSpecSerializer()
        deserializer = AgentSpecDeserializer()
        yaml_output = serializer.to_yaml(tool)
        restored = deserializer.from_yaml(yaml_output)
        assert isinstance(restored, Tool)
        assert restored.tool_policy.allowed_callers == ["agent-supervisor", "agent-compliance"]

    def test_policy_excluded_for_old_version(self):
        tool = make_tool_with_policy()
        serializer = AgentSpecSerializer()
        with pytest.raises(
            ValueError, match="Invalid agentspec_version:.*but the minimum allowed version is.*"
        ):
            serializer.to_json(tool, agentspec_version=AgentSpecVersionEnum.v25_4_1)
