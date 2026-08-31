# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import time
from pathlib import Path
from typing import Any

from .....conftest import AgentSpecConfigLoaderType


def load_yaml_file(
    load_agentspec_config: AgentSpecConfigLoaderType, yaml_file_name: str, valid: bool
) -> Any:
    config_dir = Path(__file__).parent.parent / ("valid_configs" if valid else "invalid_configs")
    with open(config_dir / yaml_file_name) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    tool_registry = {"wait_2_seconds_tool": lambda: time.sleep(2)}
    return load_agentspec_config(agentspec_configuration, tool_registry)
