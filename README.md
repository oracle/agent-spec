[![AgentSpec](docs/pyagentspec/source/_static/agentspec-dark.svg)][website-agentspec]


[![AgentSpec downloads][badge-dl]][downloads] [![AgentSpec docs][badge-docs]][docs] [![AgentSpec Reference Sheet][badge-reference-sheet]][reference-sheet] [![License][badge-license]](#license)


# Open Agent Specification

Agent Spec is a portable, platform-agnostic configuration language that allows Agents
and Agentic Systems to be described with sufficient fidelity.
It defines the conceptual objects and called components that compose Agents in typical Agent systems,
including the properties that determine the components' configuration, and their respective semantics.
Agent Spec is based on two main runnable standalone components:

* Agents (e.g., ReAct), that are conversational agents or agent components;
* Flows (e.g., business process) that are structured, workflow-based processes.

Runtimes implement the Agent Spec components for execution with Agentic frameworks or libraries.
Agent Spec would be supported by SDKs in various languages (e.g. Python) to be able to serialize/deserialize Agents to JSON/YAML,
or create them from object representations with the assurance of conformance to the specification.

For more information, including the motivation and specification, see the [dedicated section](https://oracle.github.io/agent-spec/development/agentspec/index.html) in the Agent Spec documentation.


## Get started

To get started, set up your Python environment (Python 3.10 or newer required), and then install the PyAgentSpec package.

### venv

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install pyagentspec
```


## Hello world example


Initialize a Large Language Model (LLM) of your choice:


| OCI Gen AI                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Open AI                                                                                                                                      | Ollama                                                                                                                                                                |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| <pre>from pyagentspec.llms import OciGenAiConfig<br>from pyagentspec.llms.ociclientconfig import OciClientConfigWithApiKey<br><br>OCIGENAI_ENDPOINT = "https://inference.generativeai.<oci region>.oci.oraclecloud.com"<br>COMPARTMENT_ID = "ocid1.compartment.oc1..<compartment_id>"<br>llm = OciGenAiConfig(<br>    name="OCI model",<br>    model_id="model_id",<br>    compartment_id=COMPARTMENT_ID,<br>    client_config=OciClientConfigWithApiKey(<br>        name="client_config",<br>        service_endpoint=OCIGENAI_ENDPOINT,<br>        auth_file_location="~/.oci/config",<br>        auth_profile="DEFAULT",<br>    ),<br>)</pre> | <pre>from pyagentspec.llms import OpenAiConfig<br><br>llm = OpenAiConfig(<br>    name="OpenAI model",<br>    model_id="model_id",<br>)</pre> | <pre>from pyagentspec.llms import OllamaConfig<br><br>llm = OllamaConfig(<br>    name="Ollama model",<br>    url="ollama_url",<br>    model_id="model_id",<br>)</pre> |



> See the list of supported LLMs in the [PyAgentSpec documentation](https://oracle.github.io/agent-spec/development/howtoguides/howto_llm_from_different_providers.html).


Then, create an agent using a [PyAgentSpec Agent](https://oracle.github.io/agent-spec/development/api/agent.html#pyagentspec.agent.Agent):

```python
from pyagentspec.agent import Agent
from pyagentspec.property import Property

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
```


For more information on how to build flexible Agents, structured Flows and multi-agent patterns, read the [PyAgentSpec Guides](https://oracle.github.io/agent-spec/development/howtoguides/index.html)


## Why Agent Spec

To facilitate the process of building framework-agnostic agents programmatically, Agent Spec SDKs can be implemented in various programming languages.
These SDKs are expected to provide two core capabilities:

* Building Agent Spec component abstractions by implementing the relevant interfaces, in full compliance with the Agent Spec specification;
* Importing and exporting these abstraction to and from their serialized JSON/YAML representations.

As part of the Agent Spec project, we provide a Python SDK called PyAgentSpec.
It enables users to build Agent Spec-compliant agents in Python.
Using PyAgentSpec, you can define assistants by composing components that mirror the interfaces and behavior specified by Agent Spec, and export them to JSON/YAML format.

## Executing Agent Spec configurations

In order to execute Agent Spec configurations, an Agent Spec Runtime Adapter is needed in order
to transform the Agent Spec representation of the agent to an equivalent representation
according to the specifics of an agentic framework.

For example, [WayFlow](https://github.com/oracle/wayflow/) is an Agent Spec reference runtime developed by Oracle,
which offers a complete set of APIs that enable users to load and execute Agent Spec configurations.


## Positioning in the Agentic Ecosystem


[![Positioning](docs/pyagentspec/source/_static/agentspec_spec_img/agentspec_positioning.svg)][website-ecosystem]



## Get Support

* Open a [GitHub issue][issues] for bug reports, questions, or requests for enhancements.
* Report a security vulnerability according to the [Reporting Vulnerabilities guide][reporting-vulnerabilities].


## Contributing

This project welcomes contributions from the community. Before submitting a pull request, please review the [contributor guide](./CONTRIBUTING.md).

## Security

Please refer to the [security guide](./SECURITY.md) for information on responsibly disclosing security vulnerabilities.

## License
Copyright (c) 2025 Oracle and/or its affiliates.

This software is under the Apache License 2.0 (LICENSE-APACHE or [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)) or Universal Permissive License (UPL) 1.0 (LICENSE-UPL or [https://oss.oracle.com/licenses/upl](https://oss.oracle.com/licenses/upl)), at your option.



[badge-dl]: https://img.shields.io/badge/download-latest-blue
[badge-docs]: https://img.shields.io/badge/documentation-AgentSpec-orange
[badge-license]: https://img.shields.io/badge/license-apache_2.0+UPL_1.0-green
[badge-reference-sheet]: https://img.shields.io/badge/reference%20sheet-read-red
[contributors]: https://oracle.github.io/agent-spec/development/contributing.html
[docs]: https://oracle.github.io/agent-spec/index.html
[downloads]: https://oracle.github.io/agent-spec/development/installation.html
[getting-started]: https://oracle.github.io/agent-spec/development/docs_home.html
[issues]: https://github.com/oracle/agent-spec/issues
[reference-sheet]: https://oracle.github.io/agent-spec/development/misc/reference_sheet.html
[reporting-vulnerabilities]: https://www.oracle.com/corporate/security-practices/assurance/vulnerability/reporting.html
[website-wayflow]: https://oracle.github.io/wayflow/
[website-agentspec]: https://oracle.github.io/agent-spec/
[website-ecosystem]: https://oracle.github.io/agent-spec/development/agentspec/positioning.html
