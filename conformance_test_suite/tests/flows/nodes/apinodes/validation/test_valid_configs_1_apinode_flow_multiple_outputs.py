# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pathlib import Path
from typing import Any

import pytest

from .....conftest import AgentSpecConfigLoaderType

CONFIG_DIR = Path(__file__).parent.parent / "valid_configs"
YAML_FILE_NAME = "1_apinode_multiple_outputs_flow.yaml"


# This test not working for now because of issues related to how ApiNode handles multiple outputs. Once ApiNode is fixed this test should normally pass.
@pytest.fixture
def agentspec_component_fixture(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> Any:

    # TO DO: Once above problem fixed, this call should be removed with only YAML file loaded
    create_Flow()

    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    agentspec_component = load_agentspec_config(agentspec_config=agentspec_configuration)
    return agentspec_component


def test_valid_configs_1_apinode_flow_multiple_outputs_can_be_loaded(
    agentspec_component_fixture,
) -> None:
    """Test that the configuration can be loaded successfully."""
    assert agentspec_component_fixture is not None, "valid file, should be loaded"


@pytest.mark.parametrize(
    "user_input, expected_university, expected_city",
    [
        ("Morocco", "UM6P", "Ben Guerir"),
        ("Switzerland", "ETH Zurich", "Zurich"),
    ],
)
def test_valid_configs_1_apinode_flow_multiple_outputs_can_be_executed(
    agentspec_component_fixture,
    user_input,
    expected_university,
    expected_city,
    local_common_server,
) -> None:
    """Test execution, assuming loading already works."""

    agentspec_component = agentspec_component_fixture
    agentspec_component.start({"user_input": user_input})
    result = agentspec_component.run()

    assert (
        result.outputs["university"] == expected_university
        and result.outputs["city"] == expected_city
    ), f"Expected {expected_university} and {expected_city} for {user_input}"


def create_Flow():

    from urllib.parse import urljoin

    from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
    from pyagentspec.flows.flow import Flow
    from pyagentspec.flows.nodes import ApiNode, EndNode, StartNode
    from pyagentspec.property import Property

    country_property = Property(json_schema={"title": "country", "type": "string"})

    user_input_property = Property(json_schema={"title": "user_input", "type": "string"})

    start_node = StartNode(name="start", inputs=[user_input_property])

    city_property = Property(json_schema={"title": "city", "type": "string"})
    university_property = Property(json_schema={"title": "university", "type": "string"})

    apinodes_calls_url: str = "http://localhost:5008/"
    find_university_node = ApiNode(
        name="Find university API call node",
        url=urljoin(apinodes_calls_url, "findUniversity"),
        http_method="GET",
        query_params={
            "country": "{{ country }}",
        },
        inputs=[country_property],
        outputs=[university_property, city_property],
    )

    end_node = EndNode(name="end", outputs=[university_property, city_property])

    assistant_flow = Flow(
        name="Simple prompting flow to find information about a university",
        start_node=start_node,
        nodes=[start_node, find_university_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(
                name="start_to_country", from_node=start_node, to_node=find_university_node
            ),
            ControlFlowEdge(
                name="country_to_end", from_node=find_university_node, to_node=end_node
            ),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="query_edge",
                source_node=start_node,
                source_output="user_input",
                destination_node=find_university_node,
                destination_input="country",
            ),
            DataFlowEdge(
                name="university_edge",
                source_node=find_university_node,
                source_output="university",
                destination_node=end_node,
                destination_input="university",
            ),
            DataFlowEdge(
                name="city_edge",
                source_node=find_university_node,
                source_output="city",
                destination_node=end_node,
                destination_input="city",
            ),
        ],
    )

    # Serialize
    from pyagentspec.serialization.serializer import AgentSpecSerializer

    agentspec_configuration = AgentSpecSerializer().to_yaml(assistant_flow)

    with open(CONFIG_DIR / YAML_FILE_NAME, "w") as agentspec_configuration_file:
        agentspec_configuration_file.write(agentspec_configuration)
