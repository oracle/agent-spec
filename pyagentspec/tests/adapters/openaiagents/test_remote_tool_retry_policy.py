# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import json
from typing import Any

from pyagentspec.tools import RemoteTool

from ..test_remote_tool_retry_policy_cases import RemoteToolRetryPolicyCases


class TestRemoteToolRetryPolicy(RemoteToolRetryPolicyCases):
    async def invoke_remote_tool(self, remote_tool: RemoteTool) -> Any:
        from pyagentspec.adapters.openaiagents import AgentSpecLoader

        openai_agents_tool = AgentSpecLoader().load_component(remote_tool)
        return await openai_agents_tool.on_invoke_tool(  # type: ignore[arg-type]
            None, json.dumps({})
        )
