# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
import os

llama_api_url = os.environ.get("LLAMA_API_URL")
if not llama_api_url:
    raise Exception("LLAMA_API_URL is not set in the environment")

llama70bv33_api_url = os.environ.get("LLAMA70BV33_API_URL")
if not llama70bv33_api_url:
    raise Exception("LLAMA70BV33_API_URL is not set in the environment")

oss_api_url = os.environ.get("OSS_API_URL")
if not oss_api_url:
    raise Exception("OSS_API_URL is not set in the environment")


def _replace_config_placeholders(yaml_config: str) -> str:
    return (
        yaml_config.replace("[[LLAMA_API_URL]]", llama_api_url)
        .replace("[[LLAMA70BV33_API_URL]]", llama70bv33_api_url)
        .replace("[[OSS_API_URL]]", oss_api_url)
    )
