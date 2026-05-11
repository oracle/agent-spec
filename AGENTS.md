# Agent Spec Repository Guide

These instructions apply to the whole repository. More specific nested
`AGENTS.md` files take precedence for their subtrees.

## Working Rules

- Confirm the current branch and working tree before editing. Preserve unrelated
  user changes and untracked files.
- Read the relevant implementation, tests, docs, and nested `AGENTS.md` file
  before choosing an approach.
- Keep changes scoped. Do not mix unrelated cleanup, formatting churn, or
  behavior changes into the same patch.
- Update tests and public docs when behavior is user-visible.
- Prefer targeted validation first. Run broad suites only when the touched
  surface justifies it or the user asks.

## Package Guidance

- For Python SDK work, follow `pyagentspec/AGENTS.md`.
- For evaluation work, also follow
  `pyagentspec/src/pyagentspec/evaluation/AGENTS.md`.
- For TypeScript SDK work, follow `tsagentspec/AGENTS.md`.
- Keep package-specific details in nested `AGENTS.md` files instead of expanding
  this repository-level guide.

## Agent Spec Scope

- Agent Spec is a declarative, framework-neutral configuration language for
  agents and workflows. Treat serialized specs as data, not executable code.
- Runtime adapters may target WayFlow, LangGraph, AutoGen, CrewAI, OpenAI
  Agents, and related frameworks. Preserve semantics where possible and fail
  explicitly when a target cannot represent a construct.
- LLM and tool integrations should stay behind package abstractions so agent
  definitions remain portable across providers and runtimes.

## Security-Sensitive Changes

- For changes involving prompt templates, generated code, remote tools,
  credentials, deserialization, network communication, or adapter execution
  behavior, consult `docs/pyagentspec/source/security.rst`.
- Keep `docs/pyagentspec/source/security.rst` current when a change alters
  user-visible security guidance or secure-use expectations.
- Never embed secrets in specs, docs, examples, or tests. Use parameters,
  environment variables, or documented credential references.
- Treat prompt placeholders, templated URLs, remote tool calls, and generated
  code as trust-boundary surfaces.

## Repository Map

- `pyagentspec/`: Python SDK, adapters, tests, and fuzz tests.
- `tsagentspec/`: TypeScript SDK sources, tests, and examples.
- `docs/pyagentspec/`: Python SDK documentation.
- `examples/`: runnable examples and adapter demonstrations.
- `.github/`: CI and repository automation.
- Top-level install scripts and config files support cross-package development.

## Validation

- Use the closest package-level test command for the files changed.
- Run commands from the package directory when package configuration expects it.
- Avoid tests that require external services unless they are already marked,
  guarded, and relevant to the change.
- Run `git diff --check` before handing off documentation or code changes.

## Handoff

- Summarize the files changed and the reason for each change.
- Report the validation commands run, or state why validation was not run.
- Call out remaining risks, skipped external-service tests, or follow-up work.
