# Agent Spec Evaluation Subpackage – Contribution Guide

These instructions scope to `pyagentspec/evaluation` and extend the repository-wide guardrails. Follow them when touching evaluation datasets, metrics, aggregators, intermediates, evaluators, computers, or helper utilities.

## Scope & Philosophy
- Keep evaluation code framework-neutral and focused on deterministic orchestration of experiments.
- Preserve asynchronous boundaries: public evaluators may expose sync helpers, but internal metric computation and dataset access remain async-first.
- Never embed runtime-specific business logic (OCI, WayFlow, etc.); provide adapters elsewhere.

## Core Concepts
- **Datasets** – Use `_DataSource` subclasses for storage concerns. High-level `Dataset` should stay a thin wrapper exposing async iteration utilities. Avoid adding new IO methods without matching async support.
- **Metrics** – Base classes (`Metric`, `_FunctionMetric`, `LLMAsAJudgeMetric`, etc.) control retries, exception handling, and logging. New metric types must:
  - Accept `input_mapping`, `num_retries`, and `on_failure` parameters, passing them to `Metric.__init__`.
  - Raise `EvaluationException` for user-facing errors; reserve bare exceptions for programmer bugs.
  - Return `(value, details)` with JSON-serializable payloads; reserve `__`-prefixed keys for framework metadata.
- **Aggregators** – Keep stateless and side-effect free. Favor functional style (no cached mutable state) and ensure `aggregate` tolerates empty input sequences where meaningful (raise explicit errors otherwise).
- **Intermediates / Computers** – Use them to encapsulate reusable evaluation steps. Keep orchestration logic in `_computers` and data containers in `intermediates`.

## Coding Patterns
- Guard public async call paths with lightweight logging via `logging.getLogger(__name__)`; never use `print`.
- Respect retry semantics: use `_bind_kwargs_to_func` and `_map_names` helpers instead of duplicating binding logic.
- Prefer `typing.Literal` for configuration flags exposed in public APIs to keep docs accurate.
- Store shared constants in module-level `ALL_CAPS`; keep per-type defaults on the class.
- Avoid introducing tight coupling between evaluation submodules; cross-import via top-level `pyagentspec.evaluation` if necessary to break cycles.

## Testing Expectations
- Place tests under `tests/evaluation/` mirroring module layout (e.g., `tests/evaluation/test_metrics.py`).
- Use anyio-friendly pytest patterns (`pytest.mark.anyio`) and helper fixtures when interacting with async datasets or metrics.
- Add regression coverage for: retry logic, exception strategies, LLM invocation mocks, and aggregator edge cases (empty inputs, non-numeric data).

## Documentation & Naming
- Provide docstrings for every public class, method, and function; include parameter semantics and return types.
- Highlight async usage in docstrings (e.g., "This coroutine...") for methods returning awaitables.
- Keep module names descriptive (`evaluation_results`, `handling_strategies`). For new directories, add nested `AGENTS.md` if conventions diverge.

## Versioning & API Surface
- Maintain backwards compatibility: new parameters must be optional and default-safe.
- Signal minimum Agent Spec version raises via `AgentSpecVersionEnum` integration only when the evaluation feature requires spec-level changes.
- Update `__all__` exports in `pyagentspec/evaluation/__init__.py` whenever adding public surface area.

Following these rules keeps evaluation features composable, testable, and consistent with the broader Agent Spec ecosystem.
