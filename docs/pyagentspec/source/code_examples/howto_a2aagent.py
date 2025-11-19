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
from pyagentspec.a2aagent import A2AAgent, A2AConnectionConfig, A2ASessionParameters

# Define the URL endpoint of the remote server agent to connect
# Replace "<IP ADDRESS>" with the actual IP address or hostname of the server agent
SERVER_AGENT_URL = "<IP ADDRESS>"

# Define the connection configuration with timeout and paths to SSL/TLS certificates
# This ensures a secure connection to the remote server agent
a2aconnection_config = A2AConnectionConfig(
    name="connection_config",
    timeout=30,  # Connection timeout in seconds
    key_file="/path/to/client/key.pem",    # Path to client private key
    cert_file="/path/to/client/cert.pem",  # Path to client certificate for SSL/TLS
    ssl_ca_cert="/path/to/ca/cert.pem"     # Path to CA certificate for server verification
)

# Define session parameters for controlling communication behavior
# These settings help manage session timeouts and retry mechanisms for reliability
a2asession_params = A2ASessionParameters(
    timeout=60, # Timeout in seconds for polling responses from the server
    poll_interval=2, # Polling time interval in seconds
    max_retries=3, # Maximum number of retries on connection or request failure
)

# Create an A2A Agent instance to communicate with the specified server agent's URL
a2a_agent = A2AAgent(
    name="Test A2A Agent",
    agent_url=SERVER_AGENT_URL,
    connection_config=a2aconnection_config,
    session_parameters=a2asession_params
)
# .. end-##_Creating_the_agent

# .. start-export-config-to-agentspec
from pyagentspec.serialization import AgentSpecSerializer

serialized_assistant = AgentSpecSerializer().to_json(a2a_agent)
# .. end-export-config-to-agentspec
