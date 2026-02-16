# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Collection

from pyagentspec.evaluation.aggregators.aggregator import Aggregator


class MeanAggregator(Aggregator[bool | float | int, float]):
    """
    Aggregator that computes the arithmetic mean of a collection of numerical values.

    Call an instance of this class with a sequence of numbers (bool, int, or float) to obtain their arithmetic mean.

    .. note::
        Call the aggregator instance directly (e.g., ``aggregator(values)``) rather than calling method ``aggregate`` externally.
    """

    def aggregate(self, values: Collection[bool | float | int]) -> float:
        """Return the arithmetic mean for the provided numeric values.

        Parameters
        ----------
        values : Collection[bool | float | int]
            Finite collection of numeric values. ``bool`` entries are coerced to ``0`` or ``1``
            to match Python's arithmetic semantics.

        Returns
        -------
        float
            Arithmetic mean computed as ``sum(values) / len(values)``.

        Notes
        -----
        Users should not invoke :meth:`aggregate` directly. Call the aggregator instance itself,
        e.g. ``aggregator(values)``.
        """
        if len(values) < 1:
            raise ValueError(
                "Expected at least one numeric value in MeanAggregator, but none was given"
            )
        _values = [float(v) for v in values]
        return sum(_values) / len(_values)
