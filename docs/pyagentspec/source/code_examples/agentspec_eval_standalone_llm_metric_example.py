# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# isort:skip_file
# fmt: off
# mypy: ignore-errors

"""Standalone LLM-based metric example for Agent Spec Eval."""

# .. start-snippet
from pyagentspec.evaluation.metrics.implementations import SemanticBinaryMatchMetric
from pyagentspec.llms import OpenAiConfig


async def main() -> None:
    llm_config = OpenAiConfig(name="gpt-5-mini-config", model_id="gpt-5-mini")
    metric = SemanticBinaryMatchMetric(llm_config)
    for reference, response in [("Zeurich", "Zurich"), ("Beijing", "Peking")]:
        value, details = await metric(reference=reference, response=response)
        print((value, details))


# import asyncio
# asyncio.run(main())
# .. end-snippet
