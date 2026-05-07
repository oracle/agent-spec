# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from .....conftest import AgentSpecConfigLoaderType
from .conftest import load_yaml_file


@pytest.mark.parametrize(
    "yaml_file_name",
    [
        "flow_with_parallelflownode_with_overlapping_outputs.yaml",
        "flow_with_parallelflownode_with_overlapping_inputs_with_different_types.yaml",
    ],
)
def test_invalid_configuration_of_flow_with_parallelmapnode_raise(
    load_agentspec_config: AgentSpecConfigLoaderType, yaml_file_name: str
) -> None:
    with pytest.raises(Exception):
        _ = load_yaml_file(load_agentspec_config, yaml_file_name, False)
