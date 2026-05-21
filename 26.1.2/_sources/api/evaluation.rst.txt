Evaluation
==========

Open Agent Specification Evaluation (short: Agent Spec Eval) is an extension of
Agent Spec that standardizes how agentic systems are evaluated in a framework-agnostic way.

Evaluation
----------

.. _evaluation_dataset:
.. autoclass:: pyagentspec.evaluation.Dataset

.. _evaluation_evaluator:
.. autoclass:: pyagentspec.evaluation.Evaluator

.. _evaluation_evaluation_results:
.. autoclass:: pyagentspec.evaluation.EvaluationResults

Aggregators
-----------

.. _evaluation_aggregator:
.. autoclass:: pyagentspec.evaluation.aggregators.Aggregator

.. _evaluation_harmonic_mean_aggregator:
.. autoclass:: pyagentspec.evaluation.aggregators.HarmonicMeanAggregator

.. _evaluation_mean_aggregator:
.. autoclass:: pyagentspec.evaluation.aggregators.MeanAggregator

Intermediates
-------------

.. _evaluation_intermediate:
.. autoclass:: pyagentspec.evaluation.intermediates.Intermediate

Metrics
-------

.. _evaluation_metric:
.. autoclass:: pyagentspec.evaluation.metrics.Metric

.. _evaluation_llm_based_metric:
.. autoclass:: pyagentspec.evaluation.metrics.LlmBasedMetric

.. _evaluation_llm_as_judge_metric:
.. autoclass:: pyagentspec.evaluation.metrics.LlmAsAJudgeMetric
