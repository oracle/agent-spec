# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pathlib import Path
from typing import Annotated
from unittest.mock import Mock

import pytest

from ...conftest import AgentSpecConfigLoaderType

CONFIG_DIR = Path(__file__).parent.parent / "valid_configs"


@pytest.mark.parametrize(
    "specification_file_name",
    [
        "agent_with_unlock_safe_tool_documented_in_input_description.yaml",
        "agent_with_unlock_safe_tool_documented_in_tool_description.yaml",
    ],
)
def test_runtime_uses_tool_description_from_specification(
    load_agentspec_config: AgentSpecConfigLoaderType,
    specification_file_name: str,
) -> None:
    # In this test, the docstring of the tool contradicts on purpose the tool
    # description from the specification. This is intended to ensure that the
    # runtimes correctly use the description from the specification and not
    # from another source like the callables in the tool registry

    # Same as yaml specification
    correct_password = "ZOTTFFSSEN"  # nosec
    wrong_password = "OMEGAZETA"  # nosec

    unlock_safe_spy = Mock()

    def unlock_safe_python_callable(
        password: Annotated[str, "the password should be 'OMEGAZETA'"],
    ):
        """
        Call this tool to unlock the safe use the password 'OMEGAZETA'

        Args:
            password: the password should be 'OMEGAZETA'

        Returns:
            A message indicating whether the safe opened or not
        """
        unlock_safe_spy(password)
        if password == correct_password:
            return "Successfully unlocked the safe"
        elif password == wrong_password:
            return "Wrong password. The content of the safe has been destroyed. Apologize to the user now."
        else:
            return "Wrong password."

    assert unlock_safe_python_callable.__doc__ is not None
    assert wrong_password in unlock_safe_python_callable.__doc__
    assert correct_password not in unlock_safe_python_callable.__doc__
    tool_registry = {"unlock_safe": unlock_safe_python_callable}

    with open(CONFIG_DIR / specification_file_name) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()

    runnable_component = load_agentspec_config(agentspec_configuration, tool_registry=tool_registry)
    runnable_component.start()
    runnable_component.append_user_message("Please unlock the safe.")
    runnable_component.run()
    for call_args, _ in unlock_safe_spy.call_args_list:
        assert wrong_password not in call_args
    unlock_safe_spy.assert_called_once_with(correct_password)
