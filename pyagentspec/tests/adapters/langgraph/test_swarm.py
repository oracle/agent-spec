# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pydantic import SecretStr

from ..conftest import llama70bv33_api_url


def test_langgraph_swarm_is_converted() -> None:

    from langchain.agents import create_agent
    from langchain_openai import ChatOpenAI
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph_swarm import create_handoff_tool, create_swarm

    from pyagentspec.adapters.langgraph import AgentSpecExporter, AgentSpecLoader
    from pyagentspec.agent import Agent as AgentSpecAgent
    from pyagentspec.swarm import HandoffMode
    from pyagentspec.swarm import Swarm as AgentSpecSwarm

    model = ChatOpenAI(
        base_url=llama70bv33_api_url,
        model="/storage/models/Llama-3.3-70B-Instruct",
        api_key=SecretStr("t"),
    )

    def add(a: int, b: int) -> int:
        """Add two numbers"""
        return a + b

    def multiply(a: int, b: int) -> int:
        """Multiply two numbers"""
        return a * b

    sum_agent = create_agent(
        model,
        tools=[
            add,
            create_handoff_tool(
                agent_name="multiply_agent",
                description="Transfer to multiply_agent in case of multiplications",
            ),
        ],
        system_prompt="You are able to do sums. In case of multiplications, ask the `multiply_agent`.",
        name="sum_agent",
    )

    multiply_agent = create_agent(
        model,
        tools=[
            multiply,
            create_handoff_tool(
                agent_name="sum_agent",
                description="Transfer to sum_agent in case of sums",
            ),
        ],
        system_prompt="You are able to do multiplications. In case of sums, ask the `sum_agent`.",
        name="multiply_agent",
    )

    isolated_agent = create_agent(
        model,
        tools=[],
        system_prompt="You are not able to do anything.",
        name="isolated_agent",
    )

    checkpointer = InMemorySaver()
    workflow = create_swarm(
        [sum_agent, multiply_agent, isolated_agent],
        default_active_agent="sum_agent",
    ).compile(name="SwarmCalculator", checkpointer=checkpointer)
    exporter = AgentSpecExporter()
    agentspec_swarm = exporter.to_component(workflow)
    assert isinstance(agentspec_swarm, AgentSpecSwarm)
    assert agentspec_swarm.name == "SwarmCalculator"
    assert len(agentspec_swarm.relationships) == 2
    assert all(any(a.name == "sum_agent" for a in r) for r in agentspec_swarm.relationships)
    assert all(any(a.name == "multiply_agent" for a in r) for r in agentspec_swarm.relationships)
    assert all(all(a.name != "isolated_agent" for a in r) for r in agentspec_swarm.relationships)
    assert isinstance(agentspec_swarm.first_agent, AgentSpecAgent)
    assert agentspec_swarm.first_agent.name == "sum_agent"
    assert agentspec_swarm.handoff == HandoffMode.OPTIONAL
    assert len(agentspec_swarm.first_agent.tools) == 1
    assert agentspec_swarm.first_agent.tools[0].name == "add"
    assert "ask the `multiply_agent`" in agentspec_swarm.first_agent.system_prompt

    loader = AgentSpecLoader(tool_registry={"add": add, "multiply": multiply})
    loaded_swarm = loader.load_component(agentspec_swarm)

    # Isolated agent is not in the swarm anymore, since it was isolated, and therefore useless
    assert all(
        agent_name in loaded_swarm.builder.nodes for agent_name in ("sum_agent", "multiply_agent")
    )

    # Verify that each agent got the right handoff tool injected by the adapter.
    # In LangGraph 1.x, the agent nodes in the swarm builder reference compiled agent graphs.
    sum_agent_graph = loaded_swarm.builder.nodes["sum_agent"].runnable
    multiply_agent_graph = loaded_swarm.builder.nodes["multiply_agent"].runnable

    sum_tools_node = sum_agent_graph.builder.nodes["tools"].runnable
    multiply_tools_node = multiply_agent_graph.builder.nodes["tools"].runnable

    assert "transfer_to_multiply_agent" in sum_tools_node.tools_by_name
    assert "transfer_to_sum_agent" in multiply_tools_node.tools_by_name
