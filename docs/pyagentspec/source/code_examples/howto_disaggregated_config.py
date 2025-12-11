# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# mypy: ignore-errors

# .. start-define-components:
from pyagentspec.llms.vllmconfig import OpenAiCompatibleConfig
from pyagentspec.tools import ClientTool
from pyagentspec.property import StringProperty
from pyagentspec.agent import Agent
from pyagentspec.serialization import AgentSpecSerializer, AgentSpecDeserializer

llm_config_dev = OpenAiCompatibleConfig(
    name="llm-dev",
    model_id="llm-model_1",
    url="http://dev.llm.url",
)

city_input = StringProperty(title="city_name", default="zurich")
weather_output = StringProperty(title="forecast")

weather_tool = ClientTool(
    id="weather_tool",
    name="get_weather",
    description="Gets the weather for a city",
    inputs=[city_input],
    outputs=[weather_output],
)

agent = Agent(
    id="agent_id",
    name="Weather Agent",
    llm_config=llm_config_dev,
    system_prompt="You are a helpful weather assistant.",
    tools=[weather_tool],
)
# .. end-define-components:

# .. start-export-serialization:
serializer = AgentSpecSerializer()
main_yaml, disagg_yaml = serializer.to_yaml(
    agent,
    disaggregated_components=[
        (llm_config_dev, "llm_config"),
        (weather_tool, "client_weather_tool"),
    ],
    export_disaggregated_components=True,
)
# .. end-export-serialization:

# .. start-export-deserialization:
deserializer = AgentSpecDeserializer()
component_registry = deserializer.from_yaml(
    disagg_yaml,
    import_only_referenced_components=True,
)

# Change the components dynamically
# For example, in this case we want to use a different LLM from the one we built the agent with
llm_config_prod = OpenAiCompatibleConfig(
    name="llm-prod",
    model_id="llm_model_2",
    url="http://prod.llm.url",
)

component_registry["llm_config"] = llm_config_prod
# The `client_weather_tool` remains the one that was deserialized from `disagg_yaml`

# Load the agent with the updated component registry
loaded_agent = deserializer.from_yaml(
    main_yaml,
    components_registry=component_registry,
)
# .. end-export-deserialization:

# .. start-complete:
from pyagentspec.llms.vllmconfig import OpenAiCompatibleConfig
from pyagentspec.tools import ClientTool
from pyagentspec.property import StringProperty
from pyagentspec.agent import Agent
from pyagentspec.serialization import AgentSpecSerializer, AgentSpecDeserializer

llm_config_dev = OpenAiCompatibleConfig(
    name="llm-dev",
    model_id="llm-model_1",
    url="http://dev.llm.url",
)

city_input = StringProperty(title="city_name", default="zurich")
weather_output = StringProperty(title="forecast")

weather_tool = ClientTool(
    id="weather_tool",
    name="get_weather",
    description="Gets the weather for a city",
    inputs=[city_input],
    outputs=[weather_output],
)

agent = Agent(
    id="agent_id",
    name="Weather Agent",
    llm_config=llm_config_dev,
    system_prompt="You are a helpful weather assistant.",
    tools=[weather_tool],
)

serializer = AgentSpecSerializer()
main_yaml, disagg_yaml = serializer.to_yaml(
    agent,
    disaggregated_components=[
        (llm_config_dev, "llm_config"),
        (weather_tool, "client_weather_tool"),
    ],
    export_disaggregated_components=True,
)

deserializer = AgentSpecDeserializer()
component_registry = deserializer.from_yaml(
    disagg_yaml,
    import_only_referenced_components=True,
)

# Change the components dynamically
# For example, in this case we want to use a different LLM from the one we built the agent with
llm_config_prod = OpenAiCompatibleConfig(
    name="llm-prod",
    model_id="llm_model_2",
    url="http://prod.llm.url",
)

component_registry["llm_config"] = llm_config_prod
# The `client_weather_tool` remains the one that was deserialized from `disagg_yaml`

# Load the agent with the updated component registry
loaded_agent = deserializer.from_yaml(
    main_yaml,
    components_registry=component_registry,
)
# .. end-complete:
