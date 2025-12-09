# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
from typing import Any

import pytest

from pyagentspec.llms import OpenAiCompatibleConfig
from pyagentspec.property import StringProperty


@pytest.mark.parametrize(
    "incorrect_api_key,expected_error_message",
    [
        (["abc", "def"], r"api_key[\s\S]*string.*abc.*def.*list"),
        ({"some": "dict"}, r"api_key[\s\S]*string.*some.*dict.*dict"),
        (StringProperty(title="hey"), r"api_key[\s\S]*string.*StringProperty.*StringProperty"),
    ],
)
def test_passing_a_non_sting_api_key_raises(
    incorrect_api_key: Any, expected_error_message: str
) -> None:
    with pytest.raises(ValueError, match=expected_error_message):
        OpenAiCompatibleConfig(
            name="config",
            url="https://example.com",
            model_id="custom_model_id",
            api_key=incorrect_api_key,
        )
