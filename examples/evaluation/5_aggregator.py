# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Collection

from pyagentspec.evaluation.aggregators import Aggregator


class MyMeanAboveThresholdAggregator(Aggregator[Any, bool]):

    def __init__(self, threshold: float) -> None:
        super().__init__()
        self.threshold = threshold

    def aggregate(self, values: Collection[Any]) -> bool:
        return bool((sum(values) / len(values)) >= self.threshold)


if __name__ == "__main__":
    aggregator = MyMeanAboveThresholdAggregator(threshold=0.5)
    examples = [
        (0.0, 0.2, 1.0),
        (0.0, 0.8, 1.0),
        (True, True, False),
        (True, False, False),
    ]

    for example in examples:
        aggregated_value = aggregator(example)
        print(f"Value of {example} are aggregated into {aggregated_value}.")
