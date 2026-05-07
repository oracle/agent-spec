# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.flows.nodes import ApiNode
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum


@pytest.fixture
def api_node_with_url_allow_list() -> ApiNode:
    return ApiNode(
        name="orders_api",
        url="https://example.invalid/orders/{{order_id}}",
        http_method="POST",
        api_spec_uri="https://example.invalid/openapi.json",
        data={"status": "{{status}}"},
        query_params={"expand": "items"},
        headers={"X-Trace-Id": "trace-123"},
        url_allow_list=["https://example.invalid/orders/"],
    )


@pytest.fixture
def api_node() -> ApiNode:
    return ApiNode(
        name="orders_api",
        url="https://example.invalid/orders/{{order_id}}",
        http_method="POST",
        api_spec_uri="https://example.invalid/openapi.json",
        data={"status": "{{status}}"},
        query_params={"expand": "items"},
        headers={"X-Trace-Id": "trace-123"},
    )


def test_api_node_serialization_roundtrip(api_node_with_url_allow_list: ApiNode) -> None:
    dumped = AgentSpecSerializer().to_dict(api_node_with_url_allow_list)
    loaded = AgentSpecDeserializer().from_dict(dumped)

    assert loaded.name == api_node_with_url_allow_list.name
    assert loaded.url == api_node_with_url_allow_list.url
    assert loaded.http_method == api_node_with_url_allow_list.http_method
    assert loaded.data == api_node_with_url_allow_list.data
    assert loaded.query_params == api_node_with_url_allow_list.query_params
    assert loaded.headers == api_node_with_url_allow_list.headers
    assert loaded.url_allow_list == api_node_with_url_allow_list.url_allow_list
    assert AgentSpecSerializer().to_dict(loaded) == dumped


def test_api_node_with_url_allow_list_requires_v26_2_0(
    api_node_with_url_allow_list: ApiNode,
) -> None:
    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        AgentSpecSerializer().to_dict(
            api_node_with_url_allow_list,
            agentspec_version=AgentSpecVersionEnum.v26_1_0,
        )


def test_api_node_older_version_serialization_omits_url_allow_list(api_node: ApiNode) -> None:
    dumped = AgentSpecSerializer().to_dict(
        api_node,
        agentspec_version=AgentSpecVersionEnum.v25_4_1,
    )
    loaded = AgentSpecDeserializer().from_dict(dumped)

    assert dumped["agentspec_version"] == AgentSpecVersionEnum.v25_4_1.value
    assert "url_allow_list" not in dumped
    assert loaded.name == api_node.name
    assert loaded.url == api_node.url
    assert loaded.http_method == api_node.http_method
    assert loaded.query_params == api_node.query_params
    assert loaded.headers == api_node.headers
    assert loaded.url_allow_list is None
