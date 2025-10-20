# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.flows.nodes.llmnode import LlmNode
from pyagentspec.llms.llmconfig import LlmConfig
from pyagentspec.property import Property
from pyagentspec.versioning import AgentSpecVersionEnum


def test_llm_node_has_inputs_from_placeholders_and_one_output(
    default_llm_config: LlmConfig,
) -> None:
    llm_node = LlmNode(
        name="node", llm_config=default_llm_config, prompt_template="Hi {{name}}! {{question}}?"
    )
    assert llm_node.inputs
    assert {p.title: p for p in llm_node.inputs} == {
        "name": Property(json_schema={"title": "name", "type": "string"}),
        "question": Property(json_schema={"title": "question", "type": "string"}),
    }
    assert llm_node.outputs and len(llm_node.outputs) == 1
    assert llm_node.outputs[0].title == LlmNode.DEFAULT_OUTPUT
    assert llm_node.outputs[0].json_schema["type"] == "string"


def test_llm_node_raises_on_incorrectly_titled_inputs(default_llm_config: LlmConfig) -> None:
    with pytest.raises(ValueError, match="NOT_question"):
        LlmNode(
            name="node",
            llm_config=default_llm_config,
            prompt_template="Hi {{name}}! {{question}}?",
            inputs=[
                Property(json_schema={"title": "name", "type": "string"}),
                Property(json_schema={"title": "NOT_question", "type": "string"}),
            ],
        )


def test_llm_node_accepts_renaming_of_output(default_llm_config: LlmConfig) -> None:
    output_override = Property(json_schema={"title": "output_override", "type": "string"})
    llm_node = LlmNode(
        name="node",
        llm_config=default_llm_config,
        prompt_template="Hi {{name}}! {{question}}?",
        outputs=[output_override],
    )
    assert llm_node.outputs == [output_override]


def test_llm_node_supports_specifying_multiple_outputs(default_llm_config: LlmConfig) -> None:
    age_property = Property(json_schema={"title": "age", "type": "integer"})
    birthday_property = Property(json_schema={"title": "birthday", "type": "string"})
    node = LlmNode(
        name="node",
        llm_config=default_llm_config,
        prompt_template="Hi {{name}}! {{question}}?",
        outputs=[age_property, birthday_property],
    )
    assert len(node.outputs or []) == 2
    assert node.min_agentspec_version == AgentSpecVersionEnum.v25_4_2
