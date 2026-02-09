# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Behavioural coverage for string based metrics."""

import pytest

from pyagentspec.evaluation.metrics.implementations import ExactBinaryMatchMetric


@pytest.mark.anyio
@pytest.mark.parametrize(
    "metric_params,reference,response,expected",
    [
        ({}, "Geneva", "Geneva", True),
        ({}, "Bern", "Berne", False),
        ({"ignore_case": True}, "Zurich", "zURich", True),
        ({"ignore_case": False}, "Zurich", "zURich", False),
        ({"ignore_glyph": True}, "Genève", "Geneve", True),
        ({"ignore_glyph": False}, "Genève", "Geneve", False),
        ({"ignore_article": True}, "The Lake", "Lake", True),
        ({"ignore_article": True}, "The Lake", "lake", False),
        ({"ignore_article": True, "ignore_case": True}, "The Lake", "lake", True),
        ({"ignore_punctuations": True}, "hello, world!", "hello world", True),
        ({"ignore_punctuations": False}, "hello, world!", "hello world", False),
        ({"ignore_white_spaces": True}, "hello, world!", "hello,world!", True),
        ({"ignore_white_spaces": False}, "hello, world!", "hello,world!", False),
    ],
)
async def test_exact_binary_match_metric_normalization(
    metric_params, reference, response, expected
):
    metric = ExactBinaryMatchMetric(**metric_params)
    value, details = await metric(reference=reference, response=response)
    assert value is expected
    assert details["__computation_details"]["status"] == "successful"
    assert details["__failed_attempts"] == []


@pytest.mark.anyio
async def test_exact_binary_match_metric_feature_mapping():
    metric = ExactBinaryMatchMetric(reference_feature_name="ref", response_feature_name="resp")
    value, _ = await metric(ref="Basel", resp="Basel")
    assert value is True
