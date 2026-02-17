# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import asyncio
import pprint

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


async def main() -> None:
    evaluator = Evaluator(
        metrics=[
            ExactBinaryMatchMetric(name="ExactBinaryMatchStrict"),
            ExactBinaryMatchMetric(name="ExactBinaryMatchRelaxed", ignore_glyph=True),
        ]
    )
    results = await evaluator.evaluate(dataset)

    print("as DICT:")
    pprint.pp(results.to_dict())

    print("as DF:")
    print(results.to_df())


if __name__ == "__main__":
    asyncio.run(main())
