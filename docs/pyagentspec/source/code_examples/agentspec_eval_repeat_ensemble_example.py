# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# isort:skip_file
# fmt: off
# mypy: ignore-errors

"""Repeat and ensemble wrappers example for Agent Spec Eval."""

# .. start-snippet
from pyagentspec.evaluation.aggregators import MeanAggregator
from pyagentspec.evaluation.metrics.implementations import SemanticBinaryMatchMetric
from pyagentspec.evaluation.metrics.wrappers import EnsembleMetric, RepeatMetric
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
        metric=SemanticBinaryMatchMetric(
            get_llm_model("oci/meta.llama-4-maverick-17b-128e-instruct-fp8")
        ),
        aggregator=MeanAggregator(),
        num_repeats=3,
    )

    llms = {
        "llama_3": "meta.llama-3.3-70b-instruct",
        "llama_scout": "meta.llama-4-scout-17b-16e-instruct",
        "llama_maverick": "meta.llama-4-maverick-17b-128e-instruct-fp8",
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


# import asyncio
# asyncio.run(main())
# .. end-snippet
