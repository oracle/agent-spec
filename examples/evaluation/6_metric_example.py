# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import asyncio
import pprint

from pyagentspec.evaluation.metrics.implementations import SemanticBinaryMatchMetric
from pyagentspec.llms import OpenAiConfig

llm_config = OpenAiConfig(name="openai-config", model_id="gpt-5-mini")

test_cases = [
    ("Zeurich", "Zurich"),
    ("Beijing", "Peking"),
    ("Knight", "Night"),
    ("Write", "Right"),
]


async def main() -> None:
    metric = SemanticBinaryMatchMetric(llm_config)
    for reference, response in test_cases:
        result = await metric(reference=reference, response=response)
        pprint.pp(result)


if __name__ == "__main__":
    asyncio.run(main())
