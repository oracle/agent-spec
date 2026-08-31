# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


from agentframeworkruntime import AgentFrameworkAgentSpecLoader
from agentspec_cts_sdk import AgentSpecUserMessageRequestExecutionStatus


def test_agent_spec_loader_loads_and_runs_simple_agent(vllmconfig_with_agent: str) -> None:
    runnable_component = AgentFrameworkAgentSpecLoader.load(agentspec_config=vllmconfig_with_agent)
    runnable_component.start()
    runnable_component.append_user_message("30x6")
    status = runnable_component.run()
    assert isinstance(status, AgentSpecUserMessageRequestExecutionStatus)

    # NOTE: That means that the textcontent type has the correct "assistant" Role
    assert len(status.agent_messages) == 1


def test_agent_correctly_uses_info_from_long_conversation(vllmconfig_with_agent: str) -> None:
    runnable_component = AgentFrameworkAgentSpecLoader.load(agentspec_config=vllmconfig_with_agent)
    runnable_component.start()
    runnable_component.append_user_message("Remember what I tell you")
    status = runnable_component.run()
    runnable_component.append_user_message("My name is Sam")
    runnable_component.run()

    runnable_component.append_user_message("I live in Agadir")
    runnable_component.run()

    runnable_component.append_user_message("What's my name and where do I live?")
    status = runnable_component.run()
    assert isinstance(status, AgentSpecUserMessageRequestExecutionStatus)
    last_message = status.agent_messages[-1]
    assert "sam" in last_message.lower() and "agadir" in last_message.lower()
