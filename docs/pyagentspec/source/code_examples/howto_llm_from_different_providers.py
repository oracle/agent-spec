# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# isort:skip_file
# fmt: off
# mypy: ignore-errors

# .. oci-start
from pyagentspec.llms import OciGenAiConfig
from pyagentspec.llms import LlmGenerationConfig
from pyagentspec.llms.ociclientconfig import OciClientConfigWithApiKey

# Get the list of available models from:
# https://docs.oracle.com/en-us/iaas/Content/generative-ai/deprecating.htm#
# under the "Model Retirement Dates (On-Demand Mode)" section.
OCIGENAI_MODEL_ID = "xai.grok-3"
# Typical service endpoint for OCI GenAI service inference
# <oci region> can be "us-chicago-1" and can also be found in your ~/.oci/config file
OCIGENAI_ENDPOINT = "https://inference.generativeai.<oci region>.oci.oraclecloud.com"
# <compartment_id> can be obtained from your personal OCI account (not the key config file).
# Please find it under "Identity > Compartments" on the OCI console website after logging in to your user account.
COMPARTMENT_ID = "ocid1.compartment.oc1..<compartment_id>"

generation_config = LlmGenerationConfig(max_tokens=256, temperature=0.8)

llm = OciGenAiConfig(
    name="oci-genai-grok3",
    model_id=OCIGENAI_MODEL_ID,
    compartment_id=COMPARTMENT_ID,
    client_config=OciClientConfigWithApiKey(
        name="client_config",
        service_endpoint=OCIGENAI_ENDPOINT,
        auth_file_location="~/.oci/config",
        auth_profile="DEFAULT",
    ),
    default_generation_parameters=generation_config,
)
# .. oci-end

# .. openaicompatible-start
from pyagentspec.llms import OpenAiCompatibleConfig
from pyagentspec.llms.openaicompatibleconfig import OpenAIAPIType

generation_config = LlmGenerationConfig(max_tokens=512, temperature=1.0, top_p=1.0)

llm = OpenAiCompatibleConfig(
    name="vllm-llama-4-maverick",
    model_id="llama-4-maverick",
    url="http://url.to.my.vllm.server/llama4mav",
    api_type=OpenAIAPIType.RESPONSES,
    default_generation_parameters=generation_config,
)
# .. openaicompatible-end

# .. vllm-start
from pyagentspec.llms import VllmConfig

generation_config = LlmGenerationConfig(max_tokens=512, temperature=1.0, top_p=1.0)

llm = VllmConfig(
    name="vllm-llama-4-maverick",
    model_id="llama-4-maverick",
    url="http://url.to.my.vllm.server/llama4mav",
    default_generation_parameters=generation_config,
    api_key="optional_api_key",
)
# .. vllm-end

# .. openai-start
from pyagentspec.llms import OpenAiConfig

generation_config = LlmGenerationConfig(max_tokens=256, temperature=0.7, top_p=0.9)

llm = OpenAiConfig(
    name="openai-gpt-5",
    model_id="gpt-5",
    default_generation_parameters=generation_config,
)
# .. openai-end

# .. ollama-start
from pyagentspec.llms import OllamaConfig

generation_config = LlmGenerationConfig(max_tokens=512, temperature=0.9, top_p=0.9)

llm = OllamaConfig(
    name="ollama-llama-4",
    model_id="llama-4-maverick",
    url="http://url.to.my.ollama.server/llama4mav",
    default_generation_parameters=generation_config,
    api_key="optional_api_key",
)
# .. ollama-end

# .. full-code-start
from pyagentspec.llms import OciGenAiConfig
from pyagentspec.llms import LlmGenerationConfig
from pyagentspec.llms.ociclientconfig import OciClientConfigWithApiKey

# Get the list of available models from:
# https://docs.oracle.com/en-us/iaas/Content/generative-ai/deprecating.htm#
# under the "Model Retirement Dates (On-Demand Mode)" section.
OCIGENAI_MODEL_ID = "xai.grok-3"
# Typical service endpoint for OCI GenAI service inference
# <oci region> can be "us-chicago-1" and can also be found in your ~/.oci/config file
OCIGENAI_ENDPOINT = "https://inference.generativeai.<oci region>.oci.oraclecloud.com"
# <compartment_id> can be obtained from your personal OCI account (not the key config file).
# Please find it under "Identity > Compartments" on the OCI console website after logging in to your user account.
COMPARTMENT_ID = "ocid1.compartment.oc1..<compartment_id>"

generation_config = LlmGenerationConfig(max_tokens=256, temperature=0.8)

llm = OciGenAiConfig(
    name="oci-genai-grok3",
    model_id=OCIGENAI_MODEL_ID,
    compartment_id=COMPARTMENT_ID,
    client_config=OciClientConfigWithApiKey(
        name="client_config",
        service_endpoint=OCIGENAI_ENDPOINT,
        auth_file_location="~/.oci/config",
        auth_profile="DEFAULT",
    ),
    default_generation_parameters=generation_config,
)

from pyagentspec.llms import VllmConfig

generation_config = LlmGenerationConfig(max_tokens=512, temperature=1.0, top_p=1.0)

llm = VllmConfig(
    name="vllm-llama-4-maverick",
    model_id="llama-4-maverick",
    url="http://url.to.my.vllm.server/llama4mav",
    default_generation_parameters=generation_config,
)

from pyagentspec.llms import OpenAiConfig

generation_config = LlmGenerationConfig(max_tokens=256, temperature=0.7, top_p=0.9)

llm = OpenAiConfig(
    name="openai-gpt-5",
    model_id="gpt-5",
    default_generation_parameters=generation_config,
)

from pyagentspec.llms import OllamaConfig

generation_config = LlmGenerationConfig(max_tokens=512, temperature=0.9, top_p=0.9)

llm = OllamaConfig(
    name="ollama-llama-4",
    model_id="llama-4-maverick",
    url="http://url.to.my.ollama.server/llama4mav",
    default_generation_parameters=generation_config
)
# .. full-code-end
