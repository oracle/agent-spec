# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.flows.nodes import ApiNode
from pyagentspec.property import BooleanProperty
from pyagentspec.tools.remotetool import RemoteTool


def make_remote_tool_with_json_serializable_objects(data, query_params, headers):
    subscription_success_output = BooleanProperty(
        title="subscription_success",
    )
    return RemoteTool(
        id="city_newsletter_subscribe_tool",
        name="subscribe_to_city_newsletter",
        description="Subscribe to the newsletter of a city",
        url="https://my.url/tool",
        http_method="POST",
        api_spec_uri="https://my.api.spec.url/tool",
        data=data,
        query_params=query_params,
        headers=headers,
        outputs=[subscription_success_output],
    )


def make_api_node_with_templated_params(data, query_params, headers):
    return ApiNode(
        name="Orders api call node",
        url="https://example.com/orders/2",
        http_method="POST",
        data=data,
        query_params=query_params,
        headers=headers,
    )


@pytest.mark.parametrize(
    "func",
    [(make_remote_tool_with_json_serializable_objects), (make_api_node_with_templated_params)],
)
@pytest.mark.parametrize(
    "data, query_params, headers, expected_inputs",
    [
        (
            {"city_name": "{{city_name}}"},
            {"my_query_param": "abc"},
            {"my_header": "123"},
            ["city_name"],
        ),
        (
            {"{{state_name}}": "{{city_name}}"},
            {"my_query_param": "abc"},
            {"my_header": "123"},
            ["state_name", "city_name"],
        ),
        (
            {
                "{{state_name}}": {
                    "{{city_name}}{{temperature}}": {"query": ["{{answer1}}", "{{answer2}}"]}
                }
            },
            {"{{my_query_param}}": set(["{{abc1}}", "{{abc2}}"])},
            {"{{my_header}}": "{{123}}"},
            [
                "state_name",
                "city_name",
                "temperature",
                "answer1",
                "answer2",
                "my_query_param",
                "abc1",
                "abc2",
                "my_header",
                "123",
            ],
        ),
        (
            {"query1": ["x{{query2}}x{{query3}}x", {"{{query4}}": "{{query5}}"}]},
            {},
            {},
            ["query2", "query3", "query4", "query5"],
        ),
        (b"{{ query1 }}{{ query2 }}", {}, {}, ["query1", "query2"]),
        (
            [({"{{query1}}": b"{{query2}}"}, {"{{query3}}": [set(["{{query4}}"])]})],
            {},
            {},
            ["query1", "query2", "query3", "query4"],
        ),
        (
            {"{{query1}}": "{{query1}}"},
            {"{{query1}}": "{{query2}}"},
            {"{{query2}}": "{{query1}}"},
            ["query1", "query2"],
        ),  # Check that duplicate variables are handled
        ({1: "{{query}}"}, {}, {}, ["query"]),  # Integer is ignored for templating
    ],
)
def test_node_infers_inputs_from_nested_objects(func, data, query_params, headers, expected_inputs):
    node_with_nested_io = func(data, query_params, headers)
    remote_tool_input_list = [param.title for param in node_with_nested_io.inputs or []]
    assert set(remote_tool_input_list or []) == set(expected_inputs)
