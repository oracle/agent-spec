# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

import pytest

from pyagentspec.flows.nodes import ApiNode
from pyagentspec.property import Property


def test_api_node_has_no_inputs_when_config_are_not_templated() -> None:
    api_node = ApiNode(
        name="Weather API call node",
        url="https://example.com/weather",
        http_method="GET",
        query_params={"location": "zurich"},
    )
    assert api_node.inputs == []
    assert api_node.outputs and len(api_node.outputs) == 1


def test_api_node_infers_inputs_from_templated_configs() -> None:
    order_id_property = Property(json_schema={"title": "order_id", "type": "string"})
    item_id_property = Property(json_schema={"title": "item_id", "type": "string"})
    store_id_property = Property(json_schema={"title": "store_id", "type": "string"})
    session_id_property = Property(json_schema={"title": "session_id", "type": "string"})
    api_node = ApiNode(
        name="Orders api call node",
        url="https://example.com/orders/{{ order_id }}",
        http_method="POST",
        data={"topic_id": 12345, "item_id": "{{ item_id }}"},
        query_params={"store_id": "{{ store_id }}"},
        headers={"session_id": "{{ session_id }}"},
    )
    assert api_node.inputs == [
        order_id_property,
        item_id_property,
        store_id_property,
        session_id_property,
    ]
    assert api_node.outputs and len(api_node.outputs) == 1


def test_api_node_raises_if_ios_with_incorrect_names() -> None:
    order_id_property = Property(json_schema={"title": "order_id", "type": "string"})
    item_id_property = Property(json_schema={"title": "item_id", "type": "string"})
    incorrect_property = Property(json_schema={"title": "INCORRECT_NAME", "type": "string"})
    session_id_property = Property(json_schema={"title": "session_id", "type": "string"})
    with pytest.raises(ValueError, match="INCORRECT_NAME"):
        ApiNode(
            name="Orders api call node",
            url="https://example.com/orders/{{ order_id }}",
            http_method="POST",
            data={"topic_id": 12345, "item_id": "{{ item_id }}"},
            query_params={"store_id": "{{ store_id }}"},
            headers={"session_id": "{{ session_id }}"},
            inputs=[order_id_property, item_id_property, incorrect_property, session_id_property],
        )


def test_api_node_accepts_output_renaming() -> None:
    override_output = Property(json_schema={"title": "nice_api_response"})
    api_node = ApiNode(
        name="Weather API call node",
        url="https://example.com/weather",
        http_method="GET",
        query_params={"location": "zurich"},
        outputs=[override_output],
    )
    assert api_node.outputs == [override_output]


# TODO test_api_node_raises_if_ios_with_incompatible_types
# TODO test_api_node_accepts_ios_with_castable_types
