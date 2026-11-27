# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes.flownode import FlowNode
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum


def test_flow_node_propagates_pending_input_by_default(simplest_flow: Flow) -> None:
    flow_node = FlowNode(name="flow_node", subflow=simplest_flow)

    assert flow_node.propagate_pending_input is True


def test_flow_node_serializes_pending_input_propagation_in_26_2_0(
    simplest_flow: Flow,
) -> None:
    flow_node = FlowNode(name="flow_node", subflow=simplest_flow)

    serialized = AgentSpecSerializer().to_dict(
        flow_node,
        agentspec_version=AgentSpecVersionEnum.v26_2_0,
    )

    assert serialized["propagate_pending_input"] is True


def test_flow_node_excludes_default_pending_input_propagation_before_26_2_0(
    simplest_flow: Flow,
) -> None:
    flow_node = FlowNode(name="flow_node", subflow=simplest_flow)

    serialized = AgentSpecSerializer().to_dict(
        flow_node,
        agentspec_version=AgentSpecVersionEnum.v26_1_2,
    )

    assert "propagate_pending_input" not in serialized


def test_flow_node_can_disable_pending_input_propagation(simplest_flow: Flow) -> None:
    flow_node = FlowNode(
        name="flow_node",
        subflow=simplest_flow,
        propagate_pending_input=False,
    )

    assert flow_node.min_agentspec_version == AgentSpecVersionEnum.v26_2_0
    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        AgentSpecSerializer().to_dict(
            flow_node,
            agentspec_version=AgentSpecVersionEnum.v26_1_2,
        )

    serialized = AgentSpecSerializer().to_dict(flow_node)
    assert serialized["agentspec_version"] == AgentSpecVersionEnum.v26_2_0.value
    assert serialized["propagate_pending_input"] is False

    deserialized = AgentSpecDeserializer().from_dict(serialized)
    assert isinstance(deserialized, FlowNode)
    assert deserialized.propagate_pending_input is False
