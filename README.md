# Open Agent Specification

Agent Spec is intended to be a portable, platform-agnostic configuration language that allows Agents
and Agentic Systems to be described with sufficient fidelity.
It defines the conceptual objects, called components, that compose Agents in typical Agent systems,
including the properties that determine the components' configuration, and their respective semantics.
Agent Spec is based on two main runnable standalone components:

* Agents (e.g., ReAct), that are conversational agents or agent components;
* Flows (e.g., business process) that are structured, workflow-based processes.

Runtimes implement the Agent Spec components for execution with Agentic frameworks or libraries.
Agent Spec would be supported by SDKs in various languages (e.g. Python) to be able to serialize/deserialize Agents to yaml,
or create them from object representations with the assurance of conformance to the specification.

For more information, including the motivation and specification, see the [dedicated section](https://oracle.github.io/agent-spec/agentspec/index.html) in the Agent Spec documentation.

## PyAgentSpec

To facilitate the process of building framework-agnostic agents programmatically, Agent Spec SDKs can be implemented in various programming languages.
These SDKs are expected to provide two core capabilities:

* Building Agent Spec component abstractions by implementing the relevant interfaces, in full compliance with the Agent Spec specification;
* Importing and exporting these abstraction to and from their serialized YAML representations.

As part of the Agent Spec project, we provide a Python SDK called PyAgentSpec.
It enables users to build Agent Spec-compliant agents in Python.
Using PyAgentSpec, you can define assistants by composing components that mirror the interfaces and behavior specified by Agent Spec, and export them to YAML format.

## Executing Agent Spec configurations

In order to execute Agent Spec configurations, an Agent Spec Runtime Adapter is needed in order
to transform the Agent Spec representation of the agent to an equivalent representation
according to the specifics of an agentic framework.

For example, [WayFlow](https://github.com/oracle/wayflow/) is an Agent Spec reference runtime developed by Oracle,
which offers a complete set of APIs that enable users to load and execute Agent Spec configurations.

## Getting Started

> **Note:**
> `pyagentspec` has been tested to work on Python 3.10, 3.11, 3.12, 3.13.
> While it might work on other versions, those have not been tested.

## Installation

1. Clone the repository:

   ```bash
   git clone git@github.com:oracle/agent-spec.git
   ```
2. Navigate to the project directory:

   ```bash
   cd agent-spec/pyagentspec
   ```

3. Create and activate a Python 3.10 virtual environment:

   ```bash
   python3.10 -m venv <venv_name>
   source <venv_name>/bin/activate
   ```

4. Run the installation script:

   ```bash
   bash install-dev.sh
   ```

5. (For development) Install the pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Documentation

PyAgentSpec documentation is available at the [website](https://oracle.github.io/agent-spec/index.html).
Most of the documentation sources can be found in the _docs/_ directory, organized in the same hierarchy as presented on the site.

## Help

Create a GitHub [issue](https://github.com/oracle/agent-spec/issues).

## Contributing

This project welcomes contributions from the community. Before submitting a pull request, please review the [contributor guide](./CONTRIBUTING.md).

## Security

Please refer to the [security guide](./SECURITY.md) for information on responsibly disclosing security vulnerabilities.

## License
Copyright (c) 2025 Oracle and/or its affiliates.

This software is under the Universal Permissive License (UPL) 1.0 (LICENSE-UPL or [https://oss.oracle.com/licenses/upl](https://oss.oracle.com/licenses/upl)) or Apache License 2.0 (LICENSE-APACHE or [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)), at your option.