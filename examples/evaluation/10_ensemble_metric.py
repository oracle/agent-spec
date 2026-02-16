# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import asyncio
import os
import pprint

from pyagentspec.evaluation.aggregators import MeanAggregator
from pyagentspec.evaluation.metrics.implementations import SemanticBinaryMatchMetric
from pyagentspec.evaluation.metrics.wrappers import EnsembleMetric
from pyagentspec.llms import LlmConfig, OciGenAiConfig
from pyagentspec.llms.ociclientconfig import OciClientConfigWithApiKey


def get_llm_model(model_id: str) -> LlmConfig:
    COMPARTMENT_ID = os.environ["COMPARTMENT_ID"]
    SERVICE_ENDPOINT = os.environ["SERVICE_ENDPOINT"]
    return OciGenAiConfig(
        name="llama-config",
        model_id=model_id,
        compartment_id=COMPARTMENT_ID,
        client_config=OciClientConfigWithApiKey(
            name="llama-client-config",
            auth_file_location="~/.oci/config",
            auth_profile="DEFAULT",
            service_endpoint=SERVICE_ENDPOINT,
        ),
    )


test_cases = [
    ("Zeurich", "Zurich"),
    ("Beijing", "Peking"),
    ("Knight", "Night"),
    ("Write", "Right"),
]


async def main() -> None:
    llms = {
        "llama_3": "meta.llama-3.3-70b-instruct",
        "llama_scout": "meta.llama-4-scout-17b-16e-instruct",
        "llama_maverick": "meta.llama-4-maverick-17b-128e-instruct-fp8",
    }

    metrics = [
        SemanticBinaryMatchMetric(
            name=f"SemanticBinaryMatch-{model_name}",
            llm_config=get_llm_model(model_id),
        )
        for model_name, model_id in llms.items()
    ]

    metric = EnsembleMetric(
        name="SemanticBinaryMatch",
        metrics=metrics,
        aggregator=MeanAggregator(),
    )

    for reference, response in test_cases:
        result = await metric(reference=reference, response=response)
        pprint.pp(result, width=240)


if __name__ == "__main__":
    asyncio.run(main())
