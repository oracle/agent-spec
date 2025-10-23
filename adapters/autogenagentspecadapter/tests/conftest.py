# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import random
import socket
import subprocess  # nosec, test-only code, args are trusted
import time
from pathlib import Path
from typing import Optional

import pytest
from autogen_agentchat.teams import GraphFlow as AutogenGraphFlow

from pyagentspec.flows.flow import Flow as AgentSpecFlow
from pyagentspec.flows.nodes import AgentNode, BranchingNode, EndNode, StartNode, ToolNode


def is_port_busy(port: Optional[int]):
    if port is None:
        return True
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


# We try to find an open port between 8000 and 9000 for 5 times, if we don't we skip remote tests
attempt = 0
JSON_SERVER_PORT: Optional[int] = None
while (
    is_port_busy(JSON_SERVER_PORT := random.randint(8000, 9000))  # nosec, not for security/crypto
    and attempt < 5
):
    time.sleep(1)
    attempt += 1

JSON_SERVER_PORT = JSON_SERVER_PORT if attempt < 5 else None
IS_JSON_SERVER_RUNNING = False


def _start_json_server() -> subprocess.Popen:
    api_server = Path(__file__).parent / "api_server.py"
    process = subprocess.Popen(  # nosec, test context and trusted env
        [
            "fastapi",
            "run",
            str(api_server.absolute()),
            f"--port={JSON_SERVER_PORT}",
        ]
    )
    time.sleep(3)
    return process


@pytest.fixture(scope="session")
def json_server():
    global IS_JSON_SERVER_RUNNING
    if JSON_SERVER_PORT is not None:
        IS_JSON_SERVER_RUNNING = True
        process = _start_json_server()
        yield
        process.kill()
        process.wait()
    IS_JSON_SERVER_RUNNING = False


def inspect_names_and_nodes_and_branching_mappings_of_generated_agentspec_flow(
    autogen_flow: AutogenGraphFlow, agentspec_flow: AgentSpecFlow, list_branch_names=[]
) -> None:
    assert isinstance(agentspec_flow, AgentSpecFlow)
    assert agentspec_flow.name == autogen_flow.name

    # 1. Gather original agent names from AutoGen flow to check if they match with those of the generated AgentSpec flow
    original_agent_names = set([agent.name for agent in autogen_flow._participants])

    # 2. Build mapping of AgentSpec node types and names
    found_agent_nodes = {}
    found_branching_nodes = {}
    found_branching_tool_nodes = {}
    found_start = found_end = None

    for node in agentspec_flow.nodes:
        # Identify AgentNodes (agents) by type
        if isinstance(node, AgentNode):
            found_agent_nodes[node.name] = node
        elif isinstance(node, StartNode):
            found_start = node
        elif isinstance(node, EndNode):
            found_end = node
        elif isinstance(node, BranchingNode):
            found_branching_nodes[node.name] = node
        elif isinstance(node, ToolNode):
            found_branching_tool_nodes[node.name] = node

    # 3. Assert every original agent name produces an AgentNode
    assert set(found_agent_nodes.keys()) == original_agent_names

    # 4. Assert start/end nodes types are present as expected
    assert found_start is not None
    assert found_end is not None

    for branch_name in list_branch_names:
        # 5. Check branching node is linked to correct source node name
        assert branch_name + "_branch" in set(found_branching_nodes.keys())

        # 6. Check tool node is for branching of the right branch of source node
        assert "tool_node_branching_" + branch_name in set(found_branching_tool_nodes.keys())

    # Verify branch count for each generated Branching node
    autogen_graph = autogen_flow._graph
    for branch_node_name, branching_node in found_branching_nodes.items():
        # Recover source node name (AutoGen node)
        src_name = branch_node_name.rsplit("_branch", 1)[0]
        if src_name not in autogen_graph.nodes:
            raise AssertionError(
                f"Could not find original AutoGen node '{src_name}' in the flow's graph."
            )
        autogen_node = autogen_graph.nodes[src_name]

        # Count conditions (string or callable) on outgoing edges
        edges = getattr(autogen_node, "edges", []) or []
        num_conditions = sum(
            (getattr(e, "condition", None) is not None and isinstance(getattr(e, "condition"), str))
            or (
                getattr(e, "condition_function", None) is not None
                and callable(getattr(e, "condition_function", None))
            )
            for e in edges
        )
        # Compare with AgentSpec branching options (mapping, ignoring the default branch)
        num_agentspec_branches = len(branching_node.mapping)
        assert num_conditions == num_agentspec_branches, (
            f"Branching node '{branch_node_name}' expected {num_conditions} branches "
            f"(from original AutoGen conditions), but found {num_agentspec_branches} in AgentSpec."
        )
