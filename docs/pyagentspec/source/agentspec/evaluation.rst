.. _agentspec_eval:

=====================================================
Open Agent Specification Evaluation (Agent Spec Eval)
=====================================================

Overview
========

Open Agent Specification Evaluation (in short Agent Spec Eval) is an extension of
Agent Spec that standardizes how agentic systems are evaluated in a framework-agnostic way.
It defines a common semantic and minimal APIs for:

- Datasets: collections of samples to evaluate against.
- Metrics: reusable, composable measurements (LLM-based or deterministic) with retry and exception handling.
- Evaluators: orchestrators that apply metrics to datasets with concurrency control.

Agent Spec Eval emphasizes
- Separation of concerns (dataset vs. metrics vs. orchestration);
- Evaluation transparency (details, timing, tokens, failed attempts);
- Robustness to LLM non-determinism (retries, repetition, ensembles, exception handling);
- Parallelism controls to respect rate limits;
- Portability across runtimes and agent frameworks.

Where appropriate, Agent Spec Eval can interoperate with Agent Spec Tracing to collect traces of LLM/tool activity during evaluation
(see :ref:`agentspec_tracing`).

The objectives of Agent Spec Eval are:
- Provide a canonical set of evaluation components and their interfaces.
- Define lifecycle and attribute schemas for metrics, datasets, and evaluators.
- Identify sensitive fields and how they should be handled (aligning with Agent Spec security guidance).
- Offer a minimal, ergonomic API surface for producers and consumers as part of ``pyagentspec``.
- Remain neutral to storage/transport (files, UIs, notebooks) and to agent runtimes.

Core Concepts
=============

Sample
------

A Sample is a dictionary-like structure containing features used by metrics.
Samples should be identified by an ``id``, and they can contain arbitrary data.
Common keys include:

- ``query``: the user request or task.
- ``response``: the model/agent output to be evaluated.
- ``reference``: a gold/ground-truth reference, when available.
- ``conversation`` (optional): for multi-turn evaluations, the full interaction serialized, e.g., as a list of messages in OpenAI format

.. code-block:: json

    {
      "id": "abc123",
      "query": "What's the weather like in Paris?",
      "reference": "cloudy",
      "conversation": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What's the weather like in Paris?"},
        {"role": "assistant", "content": "The weather in Paris is cloudy today."}
      ]
    }

Dataset
-------

A Dataset is an abstraction over a collection of samples. It supports async access to enable IO-bound sources.

Datasets play a fundamental role in Agent Spec Eval, as they represent the link between the Evaluation extension and the Agent Spec ecosystem.
In particular, a Dataset could be obtained by distilling execution traces produced according to the Agent Spec Tracing specification.

.. code-block:: python

   class Dataset:
     def from_dict(data: list[dict] | dict[str, dict]) -> Dataset: ...
     def from_df(df: pandas.DataFrame) -> Dataset: ...

     async def get_sample(self, id: object) -> dict[str, object]: ...

Datasets should provide convenient converters to load and prepare data for evaluation:

- ``from_dict``: accepts a list[dict] (auto IDs: 0..N-1) or a dict[id, dict] (explicit IDs).
- ``from_df``: accepts a pandas DataFrame (converted internally to a dict-based source).

Moreover, datasets should provide a way to access data samples:

- ``get_sample``: returns the sample data corresponding to the given sample ID.

Metric
------

A Metric measures one property of a sample.
When called, a metric returns its value computed with the given (arbitrary) parameters. In case of failure, an exception can be raised.
Metrics must support proper error handling, allowing retries or other types of recovery.

.. code-block:: python

   class ExceptionHandlingStrategy:
     # custom strategies can be implemented by users
     def __call__(self, failed_attempts: Sequence[EvaluationException]) -> Any:
        """The returned value is used as score for the metric."""

   class Metric(Generic[MetricValueType]]):

     name: str
     num_retries: int = 0
     on_failure: Literal["raise", "set_none", "set_zero"] | ExceptionHandlingStrategy = "raise"

     async def __call__(self, *args: Any, **kwargs: Any) -> Tuple[Optional[MetricValueType], Dict[str, Any]]:
       """
       Orchestrates retries, timing, and exception handling around compute_metric.
       Applies input_mapping (if provided) to map sample feature names to parameter names.
       Returns (value_or_fallback, details).
       """

Return value semantics:

- If the Metric call returns a value, it is considered a valid measurement (no retry triggered).
- If an attempt fails, raise an exception; the wrapper will retry up to ``num_retries``.
- If all attempts fail, ``on_failure`` decides the fallback:
  - ``"raise"``: propagate the exception,
  - ``"set_none"``: return ``(None, details)``,
  - ``"set_zero"``: return ``(0, details)``,
  - Custom strategy: user-defined behavior.

Llm-based metrics
^^^^^^^^^^^^^^^^^

LLM-based metrics depend on Agent Spec LLM configs (see :ref:`agentspecspec`).
They support standardized prompts and extraction patterns.
They use an ``LlmConfig`` as per Agent Spec definition.

.. code-block:: python

   from pyagentspec.llms import LlmConfig

   class LlmBasedMetric(Metric[MetricValueType]):
     llm_config: LlmConfig

Evaluators
----------

An Evaluator applies one or more metrics to each sample in a dataset. Each (sample, metric)
pair is a task that can run concurrently, and it is subject to concurrency controls.

.. code-block:: python

   class Evaluator:
     metrics: Sequence[Metric[Any]]
     max_concurrency: int = -1

     async def evaluate(self, dataset: Dataset) -> EvaluationResults: ...

- ``max_concurrency`` controls how many metric computations run at once.
  - ``-1`` means "auto" (no explicit limiter by the Evaluator).
  - Use a positive integer to avoid rate-limit errors with LLM backends.

EvaluationResults
-----------------

Aggregates per-sample, per-metric values and details, and supports conversions to standard formats.

.. code-block:: python

   class EvaluationResults:
     def to_json(self) -> Dict[str, Any]: ...
     def to_df(self) -> pandas.DataFrame: ...

Aggregators
-----------

Aggregators combine multiple Metric values into a single summary (used by repeat/ensemble wrappers).

.. code-block:: python

   class Aggregator(Generic[MetricValueType, AggregationType]):
     def __call__(self, values: Collection[MetricValueType]) -> AggregationType:

Examples include: mean, harmonic mean, pass@k, user-defined strategies.

Repeat and Ensemble wrappers
----------------------------

Metrics can make use of Aggregators to combine values of multiple runs.

Repeat: recompute a metric multiple times and aggregate. Useful for noisy LLM-based metrics.

.. code-block:: python

   class RepeatMetric(Metric[AggregationType]):
     metric: Metric[RepeatMetric]
     aggregator: Aggregator[MetricValueType, AggregationType]
     num_repeats: int

Ensemble: run semantically equivalent metrics and aggregate. Useful to sue different LLMs or prompts for the same metric.

.. code-block:: python

   class EnsembleMetric(Metric[AggregationType]):
     metrics: Sequence[Metric[T]]
     aggregator: Aggregator[MetricValueType, AggregationType]

Intermediates
-------------

Some metrics depend on shared intermediate values (e.g., a list of facts extracted from a response).
Intermediates enable:

- Decomposition of complex metrics into simpler steps (Single Responsibility Principle).
- Caching and reuse across metrics and repetitions to reduce token and compute usage.

Caching of intermediates is recommended.

Concurrency Control
-------------------

Uncontrolled concurrent evaluation can overwhelm LLM endpoints. Agent Spec Eval specifies:

- Evaluator-level concurrency limiter via ``max_concurrency``.
- Concurrency is applied at the level of metric computations.
- This provides a runtime-agnostic upper bound on effective LLM request concurrency,
  while remaining simple to configure and reason about.

Design Notes:

- When ``max_concurrency`` is small, throughput is bounded but safer (fewer rate-limit errors).
- When ``-1``, concurrency is unconstrained by the Evaluator (relying on backend libraries or runtime limits).

Examples
========

End-to-end evaluation
---------------------

.. code-block:: python

   import asyncio
   from pyagentspec.evaluation import Dataset, Evaluator
   from pyagentspec.evaluation.metrics.implementations import ExactBinaryMatchMetric

   data = [
     {"query": "Where is the largest city of CH?", "reference": "Zürich", "response": "Zurich"},
     {"query": "Where is the capital of Switzerland?", "reference": "Bern", "response": "Bern"},
     {"query": "Where is the UN European HQ?", "reference": "Geneva", "response": "Genève"},
   ]
   dataset = Dataset.from_dict(data)

   async def main() -> None:
     evaluator = Evaluator(
       metrics=[
         ExactBinaryMatchMetric(name="ExactBinaryMatchStrict"),
         ExactBinaryMatchMetric(name="ExactBinaryMatchRelaxed", ignore_glyth=True),
       ]
     )
     results = await evaluator.evaluate(dataset)
     print(results.to_df())

   asyncio.run(main())

Standalone LLM-based metric
---------------------------

.. code-block:: python

   import asyncio, os
   from pyagentspec.evaluation.metrics.implementations import SemanticBinaryMatchMetric
   from pyagentspec.llms import OpenAiConfig
   from pyagentspec.llms.ociclientconfig import OciClientConfigWithApiKey

   llm_config = OpenAiConfig(name="gpt-5-mini-config", model_id="gpt-5-mini")

   async def main() -> None:
     metric = SemanticBinaryMatchMetric(llm_config)
     for reference, response in [("Zeurich", "Zurich"), ("Beijing", "Peking")]:
       value, details = await metric(reference=reference, response=response)
       print((value, details))

   asyncio.run(main())

Repeating and ensembles
-----------------------

.. code-block:: python

   import asyncio, os
   from pyagentspec.evaluation.aggregators import MeanAggregator
   from pyagentspec.evaluation.metrics.implementations import SemanticBinaryMatchMetric
   from pyagentspec.evaluation.metrics.wrappers import RepeatMetric, EnsembleMetric
   from pyagentspec.llms import LlmConfig, OciGenAiConfig
   from pyagentspec.llms.ociclientconfig import OciClientConfigWithApiKey

   def get_llm_model(model_id: str) -> LlmConfig:
     return OciGenAiConfig(
       name="llama-config",
       model_id=model_id,
       compartment_id="COMPARTMENT-ID",
       client_config=OciClientConfigWithApiKey(
         name="llama-client-config",
         auth_file_location="~/.oci/config",
         auth_profile="DEFAULT",
         service_endpoint="service-endpoint",
       ),
     )

   async def main() -> None:
     repeat_metric = RepeatMetric(
       metric=SemanticBinaryMatchMetric(get_llm_model("oci/meta.llama-4-maverick-17b-128e-instruct-fp8")),
       aggregator=MeanAggregator(),
       num_repeats=3,
     )

     llms = {
       "llama_3": "oci/meta.llama-3.3-70b-instruct",
       "llama_scout": "oci/meta.llama-4-scout-17b-16e-instruct",
       "llama_maverick": "oci/meta.llama-4-maverick-17b-128e-instruct-fp8",
     }
     metrics = [
       SemanticBinaryMatchMetric(name=f"SemanticBinaryMatch-{k}", llm_config=get_llm_model(v))
       for k, v in llms.items()
     ]
     ensemble_metric = EnsembleMetric(
       name="SemanticBinaryMatch",
       metrics=metrics,
       aggregator=MeanAggregator(),
     )

     for reference, response in [("Zeurich", "Zurich"), ("Beijing", "Peking")]:
       print("repeat:")
       print(await repeat_metric(reference=reference, response=response))
       print("ensemble:")
       print(await ensemble_metric(reference=reference, response=response))

   asyncio.run(main())

Security Considerations
=======================

Agent Spec Eval inherits all security requirements from Agent Spec (see :ref:`securityconsiderations`).
Evaluation frequently might include sensitive information (PII), including, but not limited to:

- Dataset contents (queries, references, conversations, responses);
- LLM prompts, completions, and tool I/O;
- Sensitive error messages.

Guidelines:

- Treat dataset and metric details as sensitive; mask or omit by default in exports where appropriate.
- Avoid logging prompts and completions unless explicitly configured for trusted environments.
- When integrating with :ref:`agentspec_tracing`, respect its Sensitive Field handling.
- Do not embed secrets in configurations. Use Agent Spec Sensitive Field references where applicable.

Design Notes and Best Practices
===============================

- Keep metrics small and composable; use Intermediates to share computed context.
- Prefer deterministic metrics when possible; for LLM-based metrics, use repetition/ensembles for robustness.
- Control concurrency to respect LLM endpoint rate limits and prevent cascading failures.
- Preserve transparency by returning details (timings, retries, token counts, justifications) in results.
- Keep the separation between Dataset, Metric, and Evaluator to maximize portability and testability.

References and Cross-links
==========================

- Agent Spec language specification: :ref:`agentspecspec`
- Agent Spec Tracing specification: :ref:`agentspec_tracing`
