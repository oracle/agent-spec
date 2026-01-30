# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


import os
from secrets import choice
from typing import TYPE_CHECKING, Any, Dict

import pytest

from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.flows.flow import Flow as AgentSpecFlow

if TYPE_CHECKING:
    from crewai import Flow as CrewAIFlow

    from pyagentspec.adapters.crewai import AgentSpecExporter


@pytest.fixture
def agentspec_exporter() -> "AgentSpecExporter":
    from pyagentspec.adapters.crewai import AgentSpecExporter

    return AgentSpecExporter()


@pytest.fixture
def crewai_flow() -> "CrewAIFlow":
    from crewai import LLM as CrewAILlm
    from crewai import Flow as CrewAIFlow
    from crewai.flow.flow import listen, start

    class PoemFlow(CrewAIFlow):

        @start()
        def generate_sentence_count(self) -> int:
            return choice([1, 2, 3])

        @listen(generate_sentence_count)
        def generate_poem(self, sentence_count) -> str:
            try:
                llm = CrewAILlm(
                    model="openai//storage/models/Llama-3.3-70B-Instruct",
                    api_base=f"http://{os.environ.get('LLAMA_API_URL')}/v1",
                    api_key="fake-api-key",
                )
                return llm.call(f"Generate a very short poem with {sentence_count} sentences")
            except Exception:
                return " ".join(["Very poetic sentence."] * sentence_count)

        @listen(generate_poem)
        def add_title(self, poem_text) -> str:
            return f"The Best Poem\n{poem_text}"

    return PoemFlow()


def _get_tool_registry(flow: "CrewAIFlow") -> Dict[str, Any]:
    """
    CrewAI flows store the callables for their nodes in a private dict field called _methods.
    We can reuse this as the tool registry for AgentSpecLoader.
    """
    return flow._methods


def test_convert_flow_to_agentspec(
    crewai_flow: "CrewAIFlow",
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    agentspec_flow: AgentSpecComponent = agentspec_exporter.to_component(crewai_flow)

    assert isinstance(agentspec_flow, AgentSpecFlow)
    assert len(agentspec_flow.nodes) == 5
    assert set([n.name for n in agentspec_flow.nodes]) == set(
        ["START", "END", "generate_sentence_count", "generate_poem", "add_title"]
    )
    assert len(agentspec_flow.control_flow_connections) == 4
    assert len(agentspec_flow.data_flow_connections) == 3
    assert len(agentspec_flow.outputs) == 1
    assert agentspec_flow.outputs[0].title == "add_title_output"


@pytest.mark.usefixtures("mute_crewai_console_prints")
def test_convert_flow_to_agentspec_and_back_with_kickoff(
    crewai_flow: "CrewAIFlow",
    agentspec_exporter: "AgentSpecExporter",
):
    from pyagentspec.adapters.crewai import AgentSpecLoader

    agentspec_flow_json: AgentSpecComponent = agentspec_exporter.to_json(crewai_flow)

    tool_registry = _get_tool_registry(crewai_flow)
    agentspec_loader = AgentSpecLoader(tool_registry=tool_registry)
    crewai_flow_reproduced = agentspec_loader.load_json(agentspec_flow_json)

    result = crewai_flow_reproduced.kickoff()

    assert isinstance(result, dict)
    assert len(result) == 1
    assert "add_title_output" in result
    assert result["add_title_output"].startswith("The Best Poem")
