# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# isort:skip_file
# fmt: off
# mypy: ignore-errors

"""How-to guide for Agent Spec Eval."""

# .. start-evaluator:
import asyncio
from pyagentspec.evaluation import Dataset, Evaluator
from pyagentspec.evaluation.metrics.implementations import ExactBinaryMatchMetric

data = [
    {
        "query": "Where is the largest city of CH?",
        "reference": "Zürich",
        "response": "Zurich",
    },
    {
        "query": "Where is the capital of Switzerland?",
        "reference": "Bern",
        "response": "Bern",
    },
    {
        "query": "Where is the UN European HQ?",
        "reference": "Geneva",
        "response": "Genève",
    },
]
dataset = Dataset.from_dict(data)


async def evaluator_example() -> None:
    evaluator = Evaluator(
        metrics=[
            ExactBinaryMatchMetric(name="ExactBinaryMatchStrict"),
            ExactBinaryMatchMetric(name="ExactBinaryMatchRelaxed", ignore_glyph=True),
        ]
    )
    results = await evaluator.evaluate(dataset)

    print("as JSON:")
    print(results.to_dict())

    print("as DF:")
    print(results.to_df())


asyncio.run(evaluator_example())
# .. end-evaluator

# .. start-input-mapping:
mapped_data = [
    {"ground_truth": "Zürich", "answer": "Zurich"},
    {"ground_truth": "Bern", "answer": "Bern"},
    {"ground_truth": "Geneva", "answer": "Genève"},
]
mapped_dataset = Dataset.from_dict(mapped_data)


async def input_mapping_example() -> None:
    evaluator = Evaluator(
        metrics=[
            ExactBinaryMatchMetric(
                name="ExactBinaryMatchStrict",
                reference_feature_name="ground_truth",
                response_feature_name="answer",
            ),
        ]
    )
    results = await evaluator.evaluate(mapped_dataset)
    print(results.to_df())
# .. end-input-mapping


# .. start-llm-metric:
from pyagentspec.evaluation.metrics.implementations import SemanticBinaryMatchMetric
from pyagentspec.llms import OpenAiConfig


async def llm_metric_example() -> None:
    llm_config = OpenAiConfig(name="openai-config", model_id="gpt-5-mini")
    metric = SemanticBinaryMatchMetric(llm_config)
    for reference, response in [("Zeurich", "Zurich"), ("Beijing", "Peking")]:
        value, details = await metric(reference=reference, response=response)
        print((value, details))
# .. end-llm-metric


# .. start-repeat-ensemble:
from pyagentspec.evaluation.aggregators import MeanAggregator
from pyagentspec.evaluation.metrics.wrappers import EnsembleMetric, RepeatMetric


async def repeat_and_ensemble_example() -> None:
    llm_config = OpenAiConfig(name="openai-config", model_id="gpt-5-mini")
    repeat_metric = RepeatMetric(
        metric=SemanticBinaryMatchMetric(llm_config),
        aggregator=MeanAggregator(),
        num_repeats=3,
    )

    ensemble_metric = EnsembleMetric(
        name="SemanticBinaryMatch",
        metrics=[
            SemanticBinaryMatchMetric(name="SemanticBinaryMatch-A", llm_config=llm_config),
            SemanticBinaryMatchMetric(name="SemanticBinaryMatch-B", llm_config=llm_config),
        ],
        aggregator=MeanAggregator(),
    )

    for reference, response in [("Zeurich", "Zurich"), ("Beijing", "Peking")]:
        print("repeat:")
        print(await repeat_metric(reference=reference, response=response))
        print("ensemble:")
        print(await ensemble_metric(reference=reference, response=response))
# .. end-repeat-ensemble
