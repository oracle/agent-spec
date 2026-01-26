# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from unittest.mock import patch

import pytest

from pyagentspec.tools.remotetool import RemoteTool


class DummyResponse:
    def __init__(self, obj):
        self._obj = obj

    @property
    def status_code(self):
        return 200

    def json(self):
        return self._obj


def test_remote_tool_having_nested_inputs_with_langgraph() -> None:
    """
    End-to-end: convert an AgentSpec RemoteTool to a LangGraph StructuredTool and run it.
    Patch httpx.request to capture the outgoing HTTP call and verify the rendered JSON payload.
    """
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    def mock_request(*args, **kwargs):
        city = kwargs["json"]["location"]["city"]
        return DummyResponse({"weather": f"sunny in {city}"})

    # Build a RemoteTool with nested data containing multiple template placeholders.
    remote_tool = RemoteTool(
        name="forecast_weather",
        description="Returns a forecast of the weather for the chosen city",
        url="https://weatherforecast.example/api/forecast/{{city}}",
        http_method="POST",
        data={
            "location": {
                "city": "{{city}}",
                "coordinates": {"lat": "{{lat}}", "lon": "{{lon}}"},
            },
            "meta": ["requested_by:{{user}}", {"note": "hello{{suffix}}"}],
            "raw": "binary-{{bin_suffix}}",
        },
        headers={"X-Caller": "{{user}}"},
    )

    # Convert to a LangGraph StructuredTool using the LangGraph adapter converter.
    lang_tool = AgentSpecLoader().load_component(remote_tool)

    # Expected object passed as the `json` kwarg to httpx.request after rendering.
    expected_json = {
        "location": {"city": "Agadir", "coordinates": {"lat": "30.4", "lon": "-9.6"}},
        "meta": ["requested_by:alice", {"note": "helloworld"}],
        "raw": "binary-blob",
    }

    # Patch httpx.request (used inside the converted langgraph tool) to capture the call.
    with patch("httpx.request", side_effect=mock_request) as patched_request:
        # Call the underlying function of the StructuredTool directly with keyword args.
        # The LangGraph converter wraps the function as a StructuredTool with .func attribute.
        result = lang_tool.func(
            city="Agadir", lat="30.4", lon="-9.6", user="alice", suffix="world", bin_suffix="blob"
        )
        # Ensure httpx.request was invoked and inspect the kwargs it was called with.
        patched_request.assert_called_once()
        called_args, called_kwargs = patched_request.call_args
        # The converter uses `json=remote_tool_data` when calling httpx.request for dict data
        assert (
            "json" in called_kwargs
        ), f"Expected 'json' kwarg in request call since json is a dict, got {called_kwargs}"
        assert called_kwargs["json"] == expected_json
        assert result == {"weather": "sunny in Agadir"}


def test_remote_tool_post_json_array_with_langgraph() -> None:
    """
    Test RemoteTool with JSON array body (data as list).
    """
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    def mock_request(*args, **kwargs):
        json_data = kwargs["json"]
        city = json_data[1]["location"]
        return DummyResponse({"processed_city": city})

    # Build a RemoteTool with data as a list containing placeholders.
    remote_tool = RemoteTool(
        name="process_array",
        description="Processes a JSON array body",
        url="https://example.com/api/process",
        http_method="POST",
        data=[
            "forecast",
            {"location": "{{city}}", "temp": "{{temp}}"},
        ],
        headers={"X-Caller": "{{user}}"},
    )

    # Convert to a LangGraph StructuredTool using the LangGraph adapter converter.
    lang_tool = AgentSpecLoader().load_component(remote_tool)

    # Expected rendered data (list).
    expected_data = [
        "forecast",
        {"location": "Agadir", "temp": "25"},
    ]

    # Patch httpx.request.
    with patch("httpx.request", side_effect=mock_request) as patched_request:
        # Call the underlying function of the StructuredTool directly with keyword args.
        result = lang_tool.func(
            city="Agadir",
            temp="25",
            user="alice",
        )
        patched_request.assert_called_once()
        called_args, called_kwargs = patched_request.call_args
        assert "json" in called_kwargs
        assert called_kwargs["json"] == expected_data
        assert result == {"processed_city": "Agadir"}


def test_remote_tool_post_raw_body_with_langgraph() -> None:
    """
    Test RemoteTool with raw string body (non-JSON, uses data=).
    """
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    def mock_request(*args, **kwargs):
        raw_data = kwargs["content"]
        # Extract city from raw body for dependency.
        city = raw_data.split("city: ")[1].split(" ")[0]
        return DummyResponse({"echoed_body": raw_data, "city": city})

    # Build a RemoteTool with data as a string containing placeholders.
    remote_tool = RemoteTool(
        name="send_raw",
        description="Sends a raw string body",
        url="https://example.com/api/raw",
        http_method="POST",
        data="request body for city: {{city}} with note: {{note}}",
        headers={"X-Caller": "{{user}}"},
    )

    # Convert to a LangGraph StructuredTool using the LangGraph adapter converter.
    lang_tool = AgentSpecLoader().load_component(remote_tool)

    # Expected rendered data (str).
    expected_data = "request body for city: Agadir with note: urgent"

    # Patch httpx.request.
    with patch("httpx.request", side_effect=mock_request) as patched_request:
        # Call the underlying function of the StructuredTool directly with keyword args.
        result = lang_tool.func(
            city="Agadir",
            note="urgent",
            user="alice",
        )
        patched_request.assert_called_once()
        called_args, called_kwargs = patched_request.call_args
        assert "content" in called_kwargs
        assert called_kwargs["content"] == expected_data
        assert result["city"] == "Agadir"


@pytest.mark.parametrize(
    "data, headers, is_json_payload",
    [
        (
            {"value": "{{ v1 }}", "listofvalues": ["a", "{{ v2 }}", "c"]},
            {"header1": "{{ h1 }}"},
            True,
        ),
        (
            {"value": "{{ v1 }}", "listofvalues": ["a", "{{ v2 }}", "c"]},
            {"header1": "{{ h1 }}", "Content-Type": "application/x-www-form-urlencoded"},
            False,
        ),
        ("value: {{ v1 }}, listofvalues: [a, {{ v2 }}, c]", {"header1": "{{ h1 }}"}, False),
        (["value: {{ v1 }}", "listofvalues: [a, {{ v2 }}, c]"], {"header1": "{{ h1 }}"}, True),
    ],
)
def test_remote_tool_actual_endpoint_with_langgraph(
    json_server: str, data, headers, is_json_payload
) -> None:
    """
    Real-server test using the in-repo FastAPI app (json_server fixture).
    Validates templating, JSON vs form vs raw payload handling, headers, query params, and path rendering.
    """
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    # Remote tool hitting the local test server echo endpoint
    remote_tool = RemoteTool(
        name="echo_tool",
        description="Echo tool for testing",
        url=f"{json_server}/api/echo/" + "{{u1}}",
        http_method="POST",
        data=data,
        query_params={"param": "{{ p1 }}"},
        headers=headers,
    )

    lang_tool = AgentSpecLoader().load_component(remote_tool)

    # Inputs used to render templates in url, headers, params and body
    inputs = {
        "v1": "test1",
        "v2": "test2",
        "p1": "test3",
        "h1": "test4",
        "u1": "u_seg",
    }

    result = lang_tool.func(**inputs)
    expected_msg = "JSON received" if is_json_payload else "JSON not received"

    # Core assertions from the echo server
    assert result["test"] == "test"
    assert result["__parsed_path"] == "/api/echo/u_seg"
    assert result["param"] == "test3"
    assert result["header1"] == "test4"
    assert result["json_body_received"] == expected_msg

    # Body-derived assertions (work for JSON, form-encoded, and parsed text formats)
    assert result["value"] == "test1"
    assert result["listofvalues"] == ["a", "test2", "c"]
