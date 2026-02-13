# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os

import pytest

from pyagentspec.llms.llmgenerationconfig import LlmGenerationConfig


@pytest.fixture
def default_generation_parameters() -> LlmGenerationConfig:
    return LlmGenerationConfig(temperature=0.4, max_tokens=256, top_p=0.9)


# required env variables to run OCI tests here
# as well as OCI_GENAI_API_KEY_CONFIG and OCI_GENAI_API_KEY_PEM
OCI_INSTANCE_PRINCIPAL_ENDPOINT_BASE_URL = os.getenv("INSTANCE_PRINCIPAL_ENDPOINT_BASE_URL")
OCI_COMPARTMENT_ID = os.getenv("COMPARTMENT_ID")
OCI_SERVICE_ENDPOINT = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
OCI_AUTH_PROFILE_WITH_SECURITY_TOKEN = os.getenv("OCI_AUTH_PROFILE_WITH_SECURITY_TOKEN")
OCI_IS_INSTANCE_PRINCIPAL_MACHINE = os.getenv("IS_INSTANCE_PRINCIPAL_MACHINE")
