# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


import os
from pathlib import Path

import pytest


def get_weather(city: str) -> str:
    """Returns the weather in a specific city.
    Args
    ----
        city: The city to check the weather for

    Returns
    -------
        weather: The weather in that city
    """
    return f"The weather in {city} is sunny."


CONFIGS = Path(__file__).parent / "configs"


def _replace_config_placeholders(yaml_config: str) -> str:
    llama_api_url = os.environ.get("LLAMA_API_URL")
    llama70bv33_api_url = os.environ.get("LLAMA70BV33_API_URL")
    assert llama_api_url, "Please set LLAMA_API_URL"
    assert llama70bv33_api_url, "Please set LLAMA70BV33_API_URL"
    return yaml_config.replace("[[LLAMA_API_URL]]", llama_api_url).replace(
        "[[LLAMA70BV33_API_URL]]", llama70bv33_api_url
    )


@pytest.fixture()
def vllmconfig_with_agent() -> str:
    return _replace_config_placeholders((CONFIGS / "vllmconfig_with_agent.yaml").read_text())
