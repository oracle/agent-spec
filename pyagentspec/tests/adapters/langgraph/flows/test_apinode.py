# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from unittest.mock import AsyncMock, patch

import pytest

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import ApiNode, EndNode, StartNode
from pyagentspec.property import StringProperty


class DummyResponse:
    def __init__(self, obj):
        self._obj = obj

    def json(self):
        return self._obj


@pytest.fixture
def api_node_flow() -> Flow:
    host_property = StringProperty(title="host")
    order_id_property = StringProperty(title="order_id")
    status_property = StringProperty(title="status")

    start_node = StartNode(name="start", inputs=[host_property, order_id_property])
    api_node = ApiNode(
        name="api",
        url="https://{{host}}/orders/{{order_id}}",
        http_method="GET",
        url_allow_list=["https://allowed.example.com/orders/"],
        outputs=[status_property],
    )
    end_node = EndNode(name="end", outputs=[status_property])

    return Flow(
        name="api_flow",
        start_node=start_node,
        nodes=[start_node, api_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_api", from_node=start_node, to_node=api_node),
            ControlFlowEdge(name="api_to_end", from_node=api_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="host_to_api",
                source_node=start_node,
                source_output=host_property.title,
                destination_node=api_node,
                destination_input=host_property.title,
            ),
            DataFlowEdge(
                name="order_id_to_api",
                source_node=start_node,
                source_output=order_id_property.title,
                destination_node=api_node,
                destination_input=order_id_property.title,
            ),
            DataFlowEdge(
                name="status_to_end",
                source_node=api_node,
                source_output=status_property.title,
                destination_node=end_node,
                destination_input=status_property.title,
            ),
        ],
        inputs=[host_property, order_id_property],
        outputs=[status_property],
    )


def test_apinode_can_be_imported_and_executed(api_node_flow: Flow) -> None:
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader().load_component(api_node_flow)

    with patch("httpx.request", return_value=DummyResponse({"status": "ok"})) as mocked_request:
        result = agent.invoke({"inputs": {"host": "allowed.example.com", "order_id": "123"}})

    assert "outputs" in result
    assert result["outputs"] == {"status": "ok"}
    mocked_request.assert_called_once()
    assert mocked_request.call_args.kwargs["url"] == "https://allowed.example.com/orders/123"


def test_apinode_rejects_rendered_url_outside_allow_list(api_node_flow: Flow) -> None:
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader().load_component(api_node_flow)

    with patch("httpx.request") as mocked_request:
        with pytest.raises(ValueError, match="Requested URL is not in allowed list"):
            agent.invoke({"inputs": {"host": "blocked.example.com", "order_id": "123"}})

    mocked_request.assert_not_called()


@pytest.mark.anyio
async def test_apinode_can_be_executed_async(api_node_flow: Flow) -> None:
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader().load_component(api_node_flow)

    with patch(
        "httpx.AsyncClient.request",
        new_callable=AsyncMock,
        return_value=DummyResponse({"status": "ok"}),
    ) as mocked_request:
        result = await agent.ainvoke({"inputs": {"host": "allowed.example.com", "order_id": "123"}})

    assert "outputs" in result
    assert result["outputs"] == {"status": "ok"}
    mocked_request.assert_awaited_once()
    assert mocked_request.await_args.kwargs["url"] == "https://allowed.example.com/orders/123"
