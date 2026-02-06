# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import asyncio

from pyagentspec.evaluation import Dataset, Evaluator
from pyagentspec.evaluation.metrics.implementations import ExactBinaryMatchMetric

# ground_truth instead of reference, answer instead of response
data = [
    {"ground_truth": "Zürich", "answer": "Zurich"},
    {"ground_truth": "Bern", "answer": "Bern"},
    {"ground_truth": "Geneva", "answer": "Genève"},
]
dataset = Dataset.from_dict(data)


async def main() -> None:
    evaluator = Evaluator(
        metrics=[
            ExactBinaryMatchMetric(
                name="ExactBinaryMatchStrict",
                reference_feature_name="ground_truth",
                response_feature_name="answer",
            ),
        ]
    )
    results = await evaluator.evaluate(dataset)
    print(results.to_df())


if __name__ == "__main__":
    asyncio.run(main())
