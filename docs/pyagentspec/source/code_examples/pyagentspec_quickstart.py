# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# .. full-code:
from pyagentspec.agent import Agent
from pyagentspec.llms import VllmConfig
from pyagentspec.property import Property

llm_config = VllmConfig(
    name="Vllm model",
    url="vllm_url",
    model_id="model_id",
)

expertise_property = Property(json_schema={"title": "domain_of_expertise", "type": "string"})
system_prompt = """
You are an expert in {{domain_of_expertise}}.
Please help the users with their requests.
"""
agent = Agent(
    name="Adaptive expert agent",
    system_prompt=system_prompt,
    llm_config=llm_config,
    inputs=[expertise_property],
)
# .. end-full-code:
