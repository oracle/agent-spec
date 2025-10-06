# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

# isort:skip_file
# fmt: off
# mypy: ignore-errors
# docs-title: Code Example - How to Use OCI Generative AI Agents

# .. start-##_Creating_the_agent
from pyagentspec.llms.ociclientconfig import OciClientConfigWithApiKey
from pyagentspec.ociagent import OciAgent

# Typical service endpoint for OCI GenAI service inference
# <oci region> can be "us-chicago-1" and can also be found in your ~/.oci/config file
OCIGENAI_ENDPOINT = "https://inference.generativeai.<oci region>.oci.oraclecloud.com"

oci_config = OciClientConfigWithApiKey(
    name="oci_client_config",
    service_endpoint=OCIGENAI_ENDPOINT,
    auth_profile="DEFAULT",
    auth_file_location="~/.oci/config",
)

agent = OciAgent(
    name="oci_agent",
    agent_endpoint_id="AGENT_ENDPOINT",
    client_config=oci_config,
)
# .. end-##_Creating_the_agent
