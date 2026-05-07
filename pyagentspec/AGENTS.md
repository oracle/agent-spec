# PyAgentSpec Coding Guide

These instructions apply to the `pyagentspec/` package. More specific nested
`AGENTS.md` files, such as `src/pyagentspec/evaluation/AGENTS.md`, take
precedence for their subtrees.

## Working Rules

- Confirm the current branch and working tree before editing. Preserve unrelated
  user changes and untracked files.
- Read the neighboring implementation, tests, and docs before choosing an
  approach. Prefer the established local pattern over a new abstraction.
- Keep changes scoped. Do not mix unrelated cleanup, formatting churn, or
  behavior changes into the same patch.
- For code changes, update the closest tests and public docs when the behavior
  is user-visible.
- Use targeted validation first. Run broad suites only when the touched surface
  justifies it.

## Package Map

- `src/pyagentspec/component.py`, `agent.py`, `agenticcomponent.py`: core
  component model.
- `src/pyagentspec/property.py`: JSON Schema-backed IO properties and type
  compatibility.
- `src/pyagentspec/flows/`: flow graph, nodes, edges, and the flow builder.
- `src/pyagentspec/tools/`, `mcp/`, `remoteagent.py`, `a2aagent.py`,
  `ociagent.py`: tool and remote integration specs.
- `src/pyagentspec/llms/`: provider-specific LLM configuration models.
- `src/pyagentspec/serialization/`: serializer/deserializer plugins and schema
  generation.
- `src/pyagentspec/adapters/`: conversions to and from LangGraph, CrewAI,
  AutoGen, Agent Framework, OpenAI Agents, WayFlow, and related runtimes.
- `src/pyagentspec/tracing/`: Agent Spec tracing models and events.
- `tests/`: unit and integration-style coverage. Adapter tests live under
  `tests/adapters/<runtime>/`.

## Core Model Patterns

- Use Pydantic v2 models. Prefer `ConfigDict(extra="forbid")` unless a local
  model intentionally allows provider-specific extras.
- Use `Field(default_factory=...)` for list, dict, and set defaults. Do not use
  bare mutable defaults.
- Describe inputs and outputs with `Property` objects and JSON Schema. Prefer
  typed property helpers such as `StringProperty` or `IntegerProperty` when they
  fit.
- Keep explicit IO, inferred IO, and edge compatibility consistent. Placeholder
  inference uses `{{placeholder}}` names and should remain predictable.
- Add validation through `@model_validator_with_error_accumulation` when a
  component can report multiple configuration errors. Avoid ad hoc
  `model_post_init` validation.
- New built-in components must be registered in `_component_registry.py`, exposed
  through the appropriate `__all__`, and covered by serialization tests.
- Preserve version behavior. If a feature requires a newer Agent Spec version,
  update minimum-version inference and add tests for accepted and rejected
  versions.

## Adapter Patterns

- Conversions should be deterministic and preserve names, metadata, IO schemas,
  component references, and graph topology where the target runtime supports
  them.
- Reuse each adapter's `referenced_objects` or equivalent cache so shared
  components stay shared and cycles are handled consistently.
- Raise `NotImplementedError` for unsupported runtime constructs instead of
  silently dropping behavior.
- Keep runtime execution helpers separate from representation conversion when
  the adapter already has that split.
- For generated source code, use structured rendering helpers, `repr`, or AST-like
  construction rather than raw string interpolation of spec values.
- Add focused adapter tests near the changed runtime, usually under
  `tests/adapters/<runtime>/`. Round-trip tests are expected for new conversion
  behavior.

## Templates, URLs, and Trust Boundaries

- Treat `docs/pyagentspec/source/security.rst` as the canonical secure-use
  guidance. Update it when changing prompt templating, generated code, remote
  calls, credentials, deserialization, or adapter execution behavior.
- Prompt placeholders are a trust-boundary decision. System-prompt placeholders
  should use trusted configuration values only; do not route user, tool, RAG, or
  MCP output into system prompts without deliberate runtime controls.
- When untrusted content must appear in prompts, keep it separate from system
  instructions where possible, delimit it clearly as data, validate or normalize
  it, and apply runtime length limits or filtering.
- Validate templated URL destinations after rendering. Prefer fixed
  developer-controlled scheme and authority, use `url_allow_list` where
  applicable, and avoid templated header names.
- Never embed secrets in Agent Spec. Remote configs should expose references or
  parameters, not credentials.
- Deserialization must not execute code. Use safe YAML/JSON paths and explicit
  component registries.

## Tests and Tooling

- Follow red-green-refactor for behavioral changes: first add or identify a
  focused failing test that demonstrates the desired behavior, then make the
  smallest implementation change that turns it green, then refactor while keeping
  the same focused tests passing.
- Run tests from the `pyagentspec/` working directory so the package test
  configuration and conftest directory checks apply, for example:
  `pytest -q tests/test_component.py`.
- For adapter changes, prefer the closest focused file, for example:
  `pytest -q tests/adapters/langgraph/test_tracing_async.py`.
- Some adapter tests require environment variables such as `LLAMA_API_URL`.
  If a test imports `tests/adapters/conftest.py`, ensure the needed local test
  environment is loaded before running it.
- Pytest treats warnings as errors. Use `pytest.warns` for expected warnings and
  eliminate unexpected ones.
- Keep tests deterministic. Avoid real LLM or network calls unless the existing
  test is explicitly marked and guarded.
- Formatting and static checks follow `pyproject.toml`: Black and isort at line
  length 100, and strict mypy for package code. Run `git diff --check` before
  handing off.

## Documentation Expectations

- Public modules, classes, methods, and functions need concise docstrings that
  match nearby style.
- Pydantic fields that appear in generated docs should have attribute docstrings
  immediately after the field definition.
- User-visible behavior belongs in `docs/pyagentspec/source/`; security-sensitive
  guidance belongs in `docs/pyagentspec/source/security.rst`.
- Keep examples small, deterministic, and aligned with the current public API.

## Commit Hygiene

- Stage only the files needed for the current task.
- Keep commits reviewable and topic-focused.
- Use Conventional Commits for commit messages: `type(scope): summary` when a
  useful scope exists, otherwise `type: summary`. Common types here include
  `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, and `ci`.
- Mention tests or explain why tests were not run in the handoff.
