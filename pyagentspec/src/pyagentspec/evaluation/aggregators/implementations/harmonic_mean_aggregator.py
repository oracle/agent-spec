# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Collection

from pyagentspec.evaluation.aggregators.aggregator import Aggregator


class HarmonicMeanAggregator(Aggregator[bool | float | int, float]):
    """
    Aggregator that computes the harmonic mean of a collection of non-negative numerical values.

    Call an instance of this class with a sequence of non-negative numbers (bool, int, or float) to obtain their harmonic mean.

    If any value is zero, the result is zero.
    Negative values will raise a ValueError.

    .. note::
        Call the aggregator instance directly (e.g., ``aggregator(values)``) rather than calling method ``aggregate`` externally.
    """

    def aggregate(self, values: Collection[bool | float | int]) -> float:
        """Compute the harmonic mean of the provided non-negative values.

        Parameters
        ----------
        values : Collection[bool | float | int]
            Iterable of non-negative numeric values. ``bool`` entries are coerced to ``0`` or ``1``.

        Returns
        -------
        float
            Harmonic mean defined as ``len(values) / sum(1 / v for v in values)``.

        Notes
        -----
        Users should not invoke :meth:`aggregate` directly. Call the instance itself instead
        (e.g. ``aggregator(values)``).
        """
        _values = [float(v) for v in values]

        if len(_values) < 1:
            raise ValueError(
                "Expected at least one numeric value in HarmonicMeanAggregator, but none was given"
            )
        if any(v < 0 for v in _values):
            raise ValueError(
                f"Harmonic mean can only aggregate non-negative values. Found: {_values}."
            )

        if any(v == 0.0 for v in _values):
            return 0.0

        return len(_values) / sum(1 / v for v in _values)
