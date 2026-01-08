# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Callable

import httpx

from pyagentspec.adapters._utils import render_nested_object_template, render_template
from pyagentspec.tools.remotetool import RemoteTool as AgentSpecRemoteTool


def _create_remote_tool_func(remote_tool: AgentSpecRemoteTool) -> Callable[..., Any]:
    def _remote_tool(**kwargs: Any) -> Any:
        remote_tool_data = render_nested_object_template(remote_tool.data, kwargs)
        remote_tool_headers = {
            render_template(k, kwargs): render_nested_object_template(v, kwargs)
            for k, v in remote_tool.headers.items()
        }
        remote_tool_query_params = {
            render_template(k, kwargs): render_nested_object_template(v, kwargs)
            for k, v in remote_tool.query_params.items()
        }
        remote_tool_url = render_template(remote_tool.url, kwargs)

        data = None
        json_data = None
        content = None
        if isinstance(remote_tool_data, dict):
            data = remote_tool_data
        elif isinstance(remote_tool_data, (str, bytes)):
            content = remote_tool_data
        else:
            json_data = remote_tool_data

        response = httpx.request(
            method=remote_tool.http_method,
            url=remote_tool_url,
            params=remote_tool_query_params,
            headers=remote_tool_headers,
            data=data,
            json=json_data,
            content=content,
        )
        return response.json()

    return _remote_tool
