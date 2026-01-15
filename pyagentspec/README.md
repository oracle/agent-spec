# 🔗 Open Agent Specification (PyAgentSpec)

[![AgentSpec downloads][badge-dl]][downloads] [![AgentSpec docs][badge-docs]][docs] [![AgentSpec Reference Sheet][badge-reference-sheet]][reference-sheet] [![License][badge-license]](#license)

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

---

## ⚡ Quick Install

```bash
pip install pyagentspec
```

(Optional, faster installation using `uv`)

```bash
pip install uv
uv pip install pyagentspec
```

---

## 🧠 Quick Start

### 1) Configure an LLM

Initialize a Large Language Model (LLM) of your choice using PyAgentSpec configs:


| OCI Gen AI                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Open AI                                                                                                                                      | Ollama                                                                                                                                                                |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| <pre>from pyagentspec.llms import OciGenAiConfig<br>from pyagentspec.llms.ociclientconfig import OciClientConfigWithApiKey<br><br>OCIGENAI_ENDPOINT = "https://inference.generativeai.<oci region>.oci.oraclecloud.com"<br>COMPARTMENT_ID = "ocid1.compartment.oc1..<compartment_id>"<br>llm = OciGenAiConfig(<br>    name="OCI model",<br>    model_id="model_id",<br>    compartment_id=COMPARTMENT_ID,<br>    client_config=OciClientConfigWithApiKey(<br>        name="client_config",<br>        service_endpoint=OCIGENAI_ENDPOINT,<br>        auth_file_location="~/.oci/config",<br>        auth_profile="DEFAULT",<br>    ),<br>)</pre> | <pre>from pyagentspec.llms import OpenAiConfig<br><br>llm = OpenAiConfig(<br>    name="OpenAI model",<br>    model_id="model_id",<br>)</pre> | <pre>from pyagentspec.llms import OllamaConfig<br><br>llm = OllamaConfig(<br>    name="Ollama model",<br>    url="ollama_url",<br>    model_id="model_id",<br>)</pre> |


> See the list of supported LLMs in the PyAgentSpec documentation: https://oracle.github.io/agent-spec/development/howtoguides/howto_llm_from_different_providers.html

### 2) Create an Agent

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
    llm_config=llm_config,  # from step 1
    inputs=[expertise_property],
)
```

For more examples on building flexible Agents, structured Flows, and multi-agent patterns, read the Guides: https://oracle.github.io/agent-spec/development/howtoguides/index.html

---

## 🚀 Execute Agent Spec configurations

Agent Spec configurations can be executed using Agent Spec–compatible runtimes or adapters that translate the spec into the target framework representation.

- WayFlow is an Agent Spec reference runtime developed by Oracle: https://github.com/oracle/wayflow/
- PyAgentSpec includes adapters for common frameworks (install extras as needed). Examples are available in the `adapters_examples` folder:
  - LangGraph: https://github.com/oracle/agent-spec/tree/main/adapters_examples/langgraph
  - AutoGen: https://github.com/oracle/agent-spec/tree/main/adapters_examples/autogen

Refer to the installation guide for adapter-specific extras: https://oracle.github.io/agent-spec/development/installation.html

---

## 💁 Get Support

- Open a GitHub issue for bugs, questions, or enhancement requests: https://github.com/oracle/agent-spec/issues
- Report a security vulnerability: https://www.oracle.com/corporate/security-practices/assurance/vulnerability/reporting.html

---

## 🤝 Contributing

Contributions are welcome! Please refer to the contributor guide located at the root of the repository.

---

## 🔐 Security

For responsibly reporting security issues, please refer to the project's security guidelines.

---

## 📄 License

Copyright (c) 2025 Oracle and/or its affiliates.

This software is dual-licensed under the Apache License 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) and the Universal Permissive License (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl).


[badge-dl]: https://img.shields.io/pepy/dt/pyagentspec
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
