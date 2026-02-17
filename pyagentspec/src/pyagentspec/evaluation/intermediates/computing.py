# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Sequence

from pyagentspec.evaluation._computers import _AsyncCallablesComputer, _result_to_dict
from pyagentspec.evaluation.datasets import Dataset
from pyagentspec.evaluation.intermediates.intermediate import Intermediate


async def _compute_intermediates(
    dataset: Dataset,
    intermediates: Sequence[Intermediate[Any]],
    max_concurrency: int = -1,
) -> Dataset:
    computer = _AsyncCallablesComputer(
        dataset=dataset,
        callables={intermediate.name: intermediate for intermediate in intermediates},
        max_concurrency=max_concurrency,
    )
    results = await computer.run()
    return Dataset.from_dict(
        data={
            sample_id: {
                intermediate.name: _result_to_dict(results[(sample_id, intermediate.name)])["value"]  # type: ignore
                for intermediate in intermediates
            }
            async for sample_id in dataset.ids()
        }
    )


async def add_intermediates(
    dataset: Dataset,
    intermediates: Sequence[Intermediate[Any]],
    max_concurrency: int = -1,
) -> Dataset:
    """Return a dataset augmented with computed intermediate fields.

    For each sample in ``dataset``, this function computes each provided
    ``Intermediate`` and merges the resulting values into the sample dictionary
    under the intermediate's ``name``.

    Parameters
    ----------
    dataset : Dataset
        Source dataset.

    intermediates : Sequence[Intermediate[Any]]
        Intermediates to compute for each sample.

    max_concurrency : int
        Maximum number of concurrent computations. Use ``-1`` to indicate no explicit limit.

    Returns
    -------
    Dataset
        A new dataset with intermediate results added to each sample.

    """
    intermediates_data = await _compute_intermediates(
        dataset=dataset,
        intermediates=intermediates,
        max_concurrency=max_concurrency,
    )
    return Dataset.from_dict(
        data={
            sample_id: {
                **(await dataset.get_sample(sample_id)),
                **(await intermediates_data.get_sample(sample_id)),
            }
            async for sample_id in dataset.ids()
        }
    )
