# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# isort:skip_file
# fmt: off
# mypy: ignore-errors
# docs-title: Code Example - How to Build A2A Agents

# .. start-##_Creating_the_agent
from pyagentspec.a2aagent import A2AAgent

# Define the URL endpoint of the remote server agent to connect
# Replace "<IP ADDRESS>" with the actual IP address or hostname of the server agent
SERVER_AGENT_URL = "<IP ADDRESS>"

# Create an A2A Agent instance to communicate with the specified server agent's URL
a2a_agent = A2AAgent(
    name="Test A2A Agent",
    agent_url=SERVER_AGENT_URL
)
# .. end-##_Creating_the_agent

# .. start-export-config-to-agentspec
from pyagentspec.serialization import AgentSpecSerializer

serialized_assistant = AgentSpecSerializer().to_json(a2a_agent)
# .. end-export-config-to-agentspec
