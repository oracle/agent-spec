# Agent Spec Python SDK – Assistant Operating Manual

These instructions keep AI coding agents aligned with the expectations for contributing to the Agent Spec language, and the `pyagentspec` package. Follow them before making changes.


## Agent Spec Language Highlights

Agent Spec is an open specification language for expressing the structure and configuration of agentic systems. It centers on the concept of a `Component`, a flexible building block that captures the type, identity, name, description, and optional metadata of an element in an agent system. Components can be composed or referenced symbolically, allowing complex graphs to reuse subcomponents without duplicating definitions. To describe how data moves through these graphs, Component subclasses expose inputs and outputs via JSON Schema definitions, ensuring each connection is type compatible and well documented.
The language standardizes a set of component families—such as agentic components, flows, nodes, LLM configurations, and tools—so that SDKs, runtimes, and editing GUIs share a common understanding of their behavior. By relying on JSON Schema for property typing and conversion rules, Agent Spec enables structured generation, validation, and runtime automation while remaining serialization-format agnostic. Because serialized specifications are not intended to contain executable code, producers and consumers must treat them as configurations and apply appropriate security practices when loading them.
Each component captures type, identity, inputs, outputs, and optional metadata, enabling deterministic reconstruction of agent graphs across runtimes.

### Component Model Fundamentals
- **Component** – Base abstraction with immutable `id`, declarative `type`, `name`, `description`, and extensible `metadata` for UI/runtime hints.
- **ComponentWithIO** – Adds explicit `inputs` and `outputs`, each defined via JSON Schema annotations (`title`, `type`, optional `default`/`description`). Inputs/outputs can be inferred from configuration (e.g., prompts) but must be consistent with declared schemas.
- **Symbolic references** – Components reuse others via `{"$component_ref": "COMPONENT_ID"}`, ensuring graphs stay acyclic and deduplicated.
- **Type compatibility** – Agent Spec relies on the JSON schema typing system. Output types must be castable to connected input types. Numeric/string/boolean coercions follow JSON Schema conventions.

### Schema & Placeholder Guidance
- Declare every exposed input/output. Runtime or SDK-inferred schemas must match names and be type-compatible with the declared list.
- Use double-curly placeholders (`{{placeholder}}`) in templates to infer string inputs. Complex templating is intentionally limited; prefer explicit JSON Schema for lists/objects.

### Component Families
Agent Spec organizes common constructs into specialized subclasses for validation and tooling:
- **Agentic Components** – Interactive entry points (`Agent`, `Flow`, `RemoteAgent`, `Swarm`, `ManagerWorkers`, `SpecializedAgent`).
- **Agents** – Conversational entities with `llm_config`, tools, and system prompts.
- **Flows** – Graphs of nodes (`StartNode`, `EndNode`, `LlmNode`, `BranchNode`, etc.) tied together by control/data edges.
- **Tools/ToolBoxes** – Callable capabilities and aggregations, including MCP integrations.
- **LLM Configs** – Provider-specific models (OCI, OpenAI-compatible, VLLM, Ollama).
- **Remote Agents** – Components referencing externally hosted agents (A2A, OCI Agent).


## Zero-Step Contract (always obey)

1. **Plan tightly** – Outline ≤4 steps, ≤6 words each.
2. **Stay scoped** – Touch only files needed; mirror code changes with matching docs/tests when applicable.
3. **Validate surgically** – Prefer targeted `pytest` (single file or marker). Run broader suites only on request.
4. **No background work** – Avoid long-running processes; ask if information is missing. No speculative refactors or drive-by cleanups.
5. **Report concisely** – Summarize edits (few words) and list follow-up tasks if work remains.


## Project Snapshot

- **Purpose** – Provide the canonical Python SDK for creating, validating, serializing, and converting Agent Spec configurations.
- **Packaging** – Ships to PyPI as `pyagentspec`; library code under `src/pyagentspec/`.
- **Core abstractions** – `Component` hierarchy, `Property`, agentic components (`Agent`, `Flow`, `Swarm`, etc.), LLM configs, tool definitions, serialization plugins.
- **Key capabilities** – Build Agent Spec graphs in Python, infer IO, enforce schema compatibility, version negotiation, adapters for external runtimes.
- **Plugins** – Serialization/deserialization plugins live in `pyagentspec/serialization/`, and are used by `AgentSpecSerializer`/`AgentSpecDeserializer`.

Typical workflows include:

- Defining agents/flows using strongly-typed Pydantic models.
- Serializing/deserializing Agent Spec JSON or YAML via `AgentSpecSerializer` and `AgentSpecDeserializer`.
- Converting between Agent Spec and runtime-specific representations (LangGraph, CrewAI, AutoGen, OpenAI Agents, etc.).
- Validating configurations against version-specific rules and compatibility constraints.


## Repository Map

| Area                     | Location                                                                | Notes                                                                                  |
|--------------------------|-------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| Core components          | `component.py`, `agenticcomponent.py`, `agent.py`, `swarm.py`, `flows/` | Base classes, IO inference, version guards.                                            |
| Properties & schemas     | `property.py`                                                           | JSON Schema-backed IO descriptors, compatibility helpers.                              |
| Tools                    | `tools/`                                                                | Built-in, client, server, remote tool specs and toolboxes.                             |
| LLM configs              | `llms/`                                                                 | Provider-specific configuration models (OCI, OpenAI-compatible, VLLM, Ollama, etc.).   |
| MCP                      | `mcp/`                                                                  | MCP (Model Context Protocol) tooling components                                        |
| Remote agents            | `remoteagent.py`, `a2aagent.py`, `ociagent.py`                          | Describe remote runtimes and A2A connections.                                          |
| Manager-workers & swarms | `managerworkers.py`, `swarm.py`                                         | Multi-agent orchestration components.                                                  |
| Flows                    | `flows/`                                                                | Structured workflow components and helpers.                                            |
| ├─ Nodes                 | `flows/nodes/`                                                          | List of available nodes usable in flows.                                               |
| ├─ Edges                 | `flows/edges/`                                                          | Node connections in flows                                                              |
| └─ Builder               | `flowbuilder.py`                                                        | Chainable flow builder helper.                                                  |
| Serialization            | `serialization/`                                                        | Plugins, registries, JSON schema generation, versioning support.                       |
| Adapters                 | `adapters/`                                                             | Conversion layers for external frameworks (LangGraph, CrewAI, AutoGen, OpenAI Agents). |
| Validation               | `validation_helpers.py`                                                 | Error accumulation helpers and configuration validators.                               |
| Versioning               | `versioning.py`                                                         | Classes and helpers for the Agent Spec versioning system                               |
| Tests                    | `tests/`                                                                | Extensive pytest suite, fuzz tests under `tests_fuzz/`.                                |


## Tooling & Environment

- **Python** – Target 3.10–3.14. Use the `install-dev.sh` for editable installs that include development tools. Use the `install.sh` for simple package usage.
- **Type system** – Type static checks are performed by `mypy`, the configuration is available in the `pyproject.toml` file. Avoid using `type: ignore` statements unless strictly required.
- **Formatting** – `black` (line length 100) and `isort` run via git hooks; keep imports organized accordingly. Do not introduce alternate formatters.
- **Warnings discipline** – Pytest treats warnings as errors. Either eliminate warnings or capture them with `pytest.warns`. Tests might spawn servers: do it in separate thread and make sure to use an available port using the `get_available_port` function you can find in `tests/adapters/utils.py`.


## Coding Guardrails

- **Serialization safety** – Do not execute arbitrary code during (de)serialization. Use safe loaders for YAML, keep JSON the default interchange format.
- **Component registry** – Register new components via `_component_registry.py`; ensure unique names and add to `__all__` if part of the public API.
- **Properties** – Inputs/outputs must be `Property` instances using JSON Schema annotations. Keep schemas consistent across nested components and respect `properties_have_same_type` checks.
- **Inference rules** – Agents infer IO from prompts, flows infer from start/end nodes. Maintain parity between inferred and explicit schemas.
- **Mutable defaults** – Use Pydantic `Field(default_factory=...)` for lists/dicts; never use bare mutable defaults.
- **Logging/prints** – Library code must not use `print`. Use `logging.getLogger(__name__)` when logging is required.
- **Security** – Never embed secrets. Remote configs should expose parameters, not credentials.
- **Classes** - Prefer Pydantic v2 models with `model_config = ConfigDict(extra="forbid")`; respect frozen fields like `Component.id`.


## Coding patterns and guidelines

- **Component implementation** – Subclass `Component`/`ComponentWithIO`, populate Pydantic fields (no bare defaults), implement `_get_inferred_inputs/_outputs`, `_infer_min_agentspec_version_from_configuration`, and register the class in `_component_registry.BUILTIN_CLASS_MAP` plus `__all__` that you can find in `_component_registry.py`.
- **Flow nodes** – Extend `Node`, override `_get_inferred_branches` (and IO helpers) to keep schema/branch names deterministic, and mirror validation patterns from `flows/nodes/*.py`.
- **Serialization plugins** – Prefer subclassing `PydanticComponentSerializationPlugin`/`PydanticComponentDeserializationPlugin`, supply explicit `component_types_and_models`, ensure unique `plugin_name`, and add coverage in `tests/serialization/`.
- **Adapters** – Follow the LangGraph adapter pattern: keep conversions deterministic, reuse `referenced_objects` to preserve references, surface `NotImplementedError` for unsupported constructs, and add round-trip tests in `tests/adapters/<framework>/`.
- **Schema signatures** – Always describe IO via `Property` JSON Schema; use helper utilities (`properties_have_same_type`, `model_validator_with_error_accumulation`) to enforce compatibility; using native property types (e.g., `StringProperty`, `IntegerProperty`) is preferred over using `Property` with a `json_schema`).
- **Validation helpers** – Use `@model_validator_with_error_accumulation` decorator to write validation functions of Components. Do not use the `model_post_init` method for validation.


## Testing Playbook

- Write targeted pytest cases under `tests/`. Mirror new library features with tests in the closest matching module (e.g., `tests/test_component.py` or `tests/adapters/<runtime>/`).
- Use fixtures from `tests/conftest.py` instead of ad-hoc setup. Mark tests requiring external services and guard with environment variables when applicable (`LLAMA_API_URL`, etc.).
- Avoid non-deterministic behaviors in tests (e.g., execution of LLM calls) unless strictly necessary.
- For versioned behavior, add explicit tests covering old vs. new `AgentSpecVersionEnum` scenarios (see `tests/test_versioning.py` and `tests/test_component.py::test_component_serializer_rejects_old_version`).
- New features should add new tests instead of modifying older ones, which should keep working without modifications in most cases.
- New features should include a regression test asserting that older spec versions reject the new capability (e.g., mirroring `tests/test_component.py::test_component_serializer_rejects_old_version`).
- Use patterns from: `tests/serialization` when adding serialization tests; `tests/validation` when adding validation tests; `tests/tracing` when adding Agent Spec Tracing tests;  `tests/adapters` when adding adapters tests.


## Documentation Expectations

- Add a module-level docstring that states the purpose of every new Python module, matching the concise, single-sentence summaries used across `src/pyagentspec/`.
- Give each public class a docstring whose first line summarizes intent, followed by optional paragraphs or `Examples` blocks written as doctests (mirroring `Agent`, `Flow`, and `StartNode`).
- Document public methods/functions with a short summary and, when parameters or returns need clarification, append NumPy-style ``Parameters``/``Returns`` sections as seen in `Property` and `Trace` helpers.
- Attach attribute docstrings to Pydantic model fields using triple-quoted strings immediately after the field definition (e.g., Component IDs, Tool flags) so generated docs stay informative.
- Highlight version requirements inside docstrings whenever behavior depends on `AgentSpecVersionEnum`; prefer concise notes over long narratives.


## Contribution Workflow

- Prefer incremental PRs focused on a single feature or bugfix.
- When adding new components or adapters, include serialization round-trip tests, validation tests, and schema coverage.
- For adapters, ensure conversions preserve metadata and IO definitions; document unsupported fields explicitly.
- Every change should ensure backward compatibility for at least one minor version.
- Clearly document the code; Add docstrings to every class, method, and function you implement, even minimal ones in case they are private APIs; Explaining the semantic of the most important and less clear code blocks with inline comments.


## Quick Reference Commands

- `./install-dev.sh` – install package + dev extras in editable mode.
- `pytest tests/test_component.py` – example targeted test run.


---

Respecting these guardrails keeps the Python SDK aligned with the evolving Agent Spec language while remaining stable for downstream runtimes.
