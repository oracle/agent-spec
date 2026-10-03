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
YAML_FILE_NAME = "1_apinode_with_data_and_headers_flow.yaml"


@pytest.fixture
def agentspec_component_fixture(
    load_agentspec_config: AgentSpecConfigLoaderType,
) -> Any:

    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    agentspec_component = load_agentspec_config(agentspec_config=agentspec_configuration)
    return agentspec_component


def test_valid_configs_1_apinode_with_data_and_headers_flow_can_be_loaded(
    agentspec_component_fixture,
) -> None:
    """Test that the configuration can be loaded successfully."""
    assert agentspec_component_fixture is not None, "valid file, should be loaded"


@pytest.mark.parametrize(
    "item_id, order_id, store_id, session_id, expected_product_name",
    [
        ("1", "2", "3", "4", "Airplane"),
        ("5", "6", "7", "8", "Car"),
    ],
)
def test_valid_configs_1_apinode_with_data_and_headers_flow_can_be_executed(
    agentspec_component_fixture,
    item_id,
    order_id,
    store_id,
    session_id,
    expected_product_name,
    local_common_server,
) -> None:
    """Test execution, assuming loading already works."""

    agentspec_component = agentspec_component_fixture
    agentspec_component.start(
        {"item_id": item_id, "order_id": order_id, "store_id": store_id, "session_id": session_id}
    )
    result = agentspec_component.run()

    # Test that ApiNode submits all values (in data, query_params, and headers) as expected to the server
    assert (
        result.outputs["product"]["product_name"] == expected_product_name
        and result.outputs["product"]["product_id"] == item_id
        and result.outputs["product"]["product_order_id"] == order_id
        and result.outputs["product"]["product_store_id"] == store_id
        and result.outputs["product"]["product_session_id"] == session_id
    ), f"Expected {expected_product_name}, {item_id}, {order_id}, {store_id}, and {session_id} for {item_id}, {order_id}, {store_id}, {session_id}"
