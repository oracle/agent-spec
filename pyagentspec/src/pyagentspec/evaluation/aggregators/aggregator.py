# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from abc import ABC, abstractmethod
from typing import Collection, Generic, TypeVar

MetricToAggregateValueType = TypeVar("MetricToAggregateValueType")
AggregatedValueType = TypeVar("AggregatedValueType")


class Aggregator(ABC, Generic[MetricToAggregateValueType, AggregatedValueType]):
    """
    Combine a collection of metric values into a single aggregate result.

    Abstract base class for aggregating a collection of values into a single, aggregated value.

    This class provides a callable interface for aggregating values.
    Subclasses must implement the ``aggregate`` method to define the aggregation logic.
    When the instance is called, it invokes the ``aggregate`` method on the provided sequence of values.

    .. note::
        Call the aggregator instance directly (e.g., ``aggregator(values)``) rather than calling method ``aggregate`` externally.
    """

    @abstractmethod
    def aggregate(self, values: Collection[MetricToAggregateValueType]) -> AggregatedValueType:
        """
        Abstract method to aggregate a sequence of input values into a single value.

        .. warning::
            This method is intended for internal use. Users should not call it directly;
            instead, call the aggregator instance (i.e. ``aggregator(values)``).

        Parameters
        ----------
        values : Collection[MetricToAggregateValueType]
            The collection of values to aggregate.
            Subclasses may choose to preprocess these values if needed.

        Returns
        -------
        AggregatedValueType
            The aggregated value resulting from applying the aggregation logic to the inputs.
        """

        raise NotImplementedError(
            "Method `aggregate` is not implemented. "
            "You must implement this method if you are implementing your own aggregator."
        )

    def __call__(self, values: Collection[MetricToAggregateValueType]) -> AggregatedValueType:
        """
        Aggregates the provided sequence of values. This method delegates to the ``aggregate`` method.

        Parameters
        ----------
        values : Collection[MetricToAggregateValueType]
            The collection of values to aggregate.

        Returns
        -------
        AggregatedValueType
            The aggregated value resulting from applying the aggregation logic to the inputs.
        """
        return self.aggregate(values)
