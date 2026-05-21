====================================
How to evaluate with Agent Spec Eval
====================================

.. admonition:: Prerequisites

    This guide assumes you are familiar with the following concepts:

    - :doc:`Agents <howto_agents>`

    Additionally, you need to have **Python 3.10+** installed.

Overview
========

Agent Spec Eval is the evaluation extension of Agent Spec.
It standardizes a minimal, framework-agnostic API for evaluating agentic systems with:

- **Datasets**: collections of samples.
- **Metrics**: reusable measurements (deterministic or LLM-based).
- **Evaluators**: orchestrators that run metrics over datasets, with optional concurrency control.

For the formal specification and background, see
:doc:`Open Agent Specification Evaluation (Agent Spec Eval) <../agentspec/evaluation>`.


Run an end-to-end evaluation
============================

Create a dataset from in-memory samples, configure one or more metrics, and run them
with an ``Evaluator``.

.. literalinclude:: ../code_examples/howto_evaluation.py
   :language: python
   :start-after: # .. start-evaluator:
   :end-before: # .. end-evaluator

The returned ``EvaluationResults`` can be exported as:

- Dictionary via ``results.to_dict()`` (includes the metric ``value`` and its ``details``)
- a pandas DataFrame via ``results.to_df()`` (only the main metric values)


Use different dataset field names (input mapping)
=================================================

In practice, your dataset may use different keys than the defaults expected by a metric.
For example, you may have ``ground_truth`` instead of ``reference`` and ``answer`` instead of ``response``.

Many metrics in ``pyagentspec.evaluation.metrics.implementations`` support mapping the
dataset feature names to the metric's expected parameters.

.. literalinclude:: ../code_examples/howto_evaluation.py
   :language: python
   :start-after: # .. start-input-mapping:
   :end-before: # .. end-input-mapping


Use an LLM-based metric
=======================

Some metrics call an LLM to judge semantic equivalence (or other rubric-based criteria).
These metrics take an Agent Spec LLM configuration.

.. literalinclude:: ../code_examples/howto_evaluation.py
   :language: python
   :start-after: # .. start-llm-metric:
   :end-before: # .. end-llm-metric


Reduce LLM non-determinism with repeats and ensembles
=====================================================

LLM-based metrics can be noisy.
Agent Spec Eval supports wrappers that run a metric multiple times (repeat) or run multiple
semantically-equivalent metrics (ensemble), then aggregate the values.

.. literalinclude:: ../code_examples/howto_evaluation.py
   :language: python
   :start-after: # .. start-repeat-ensemble:
   :end-before: # .. end-repeat-ensemble


Recap
=====

This guide covered how to:

- Build a :class:`pyagentspec.evaluation.datasets.dataset.Dataset` from in-memory samples.
- Evaluate samples with deterministic and LLM-based metrics.
- Export results to JSON or pandas DataFrame.
- Map dataset feature names to metric inputs.
- Use repeat/ensemble wrappers to improve robustness.


Next steps
==========

- Check the Tracing specification of Agent Spec: :doc:`Open Agent Specification Tracing <../agentspec/tracing>`.
