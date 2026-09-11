# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Async helpers for driving metric computations over datasets.

The evaluator orchestrator relies on these utilities to fan out (sample, metric)
pairs, respect concurrency constraints, and collect results in a thread-safe way.
The helpers are considered internal, hence the leading underscore prefixes.
"""

import json
from contextlib import nullcontext
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Hashable,
    Tuple,
    TypeVar,
)

import anyio
from anyio.abc import TaskStatus

from pyagentspec._lazy_loader import LazyLoader
from pyagentspec.evaluation.datasets.dataset import Dataset

if TYPE_CHECKING:
    import numpy as np
else:
    np = LazyLoader("numpy")

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


class _AsyncRegistry(Generic[K, V]):
    """Store key/value pairs while preventing duplicate registrations."""

    def __init__(self) -> None:
        """Initialise the in-memory registry and the coordination lock."""
        self.store: Dict[K, V] = {}
        self._lock = anyio.Lock()

    async def register(self, key: K, value: V) -> None:
        """Insert ``value`` under ``key`` while ensuring uniqueness."""
        async with self._lock:
            if key in self.store:
                raise RuntimeError(f"A value of key {key} is already registered.")
            self.store[key] = value


class _AsyncCallablesComputer(Generic[T]):
    """Evaluate a set of async callables across every sample in a dataset."""

    _QUEUE_BUFFER_FACTOR = 3

    def __init__(
        self,
        dataset: Dataset,
        callables: Dict[str, Callable[..., Awaitable[T]]],
        max_concurrency: int,
    ) -> None:
        """Configure the computer with the dataset, callables, and concurrency cap."""
        self.dataset = dataset
        self.callables = callables
        self.limiter = (
            anyio.CapacityLimiter(max_concurrency) if max_concurrency != -1 else nullcontext()
        )
        self._registry = _AsyncRegistry[Tuple[Any, str], T]()

    async def _compute(
        self,
        sample_id: Any,
        callable_id: str,
        task_status: TaskStatus[None] = anyio.TASK_STATUS_IGNORED,
    ) -> None:
        """Run a single callable against a dataset sample and store the result."""
        async with self.limiter:
            task_status.started()

            # Fetch the sample lazily so IO is naturally parallelised by the caller.
            sample = await self.dataset.get_sample(sample_id)
            result = await self.callables[callable_id](**sample)
            await self._registry.register((sample_id, callable_id), result)

    async def run(self) -> Dict[Tuple[Hashable, str], T]:
        """Kick off all pending computations and return the populated registry."""

        metrics_names = list(self.callables.keys())
        if not metrics_names:
            return {}

        async with anyio.create_task_group() as tg:
            async for sample_id in self.dataset.ids():
                for metric_name in metrics_names:
                    await tg.start(self._compute, sample_id, metric_name)

        return self._registry.store


def _try_to_dict_or_str(value: Any) -> Any:
    """
    Return a serializable object:
    - if it is a base type (int, string, float, bool), return as-is
    - if it is a numpy value (used by pandas), return its `item` call (i.e., the python respective)
    - if it is a list, tuple, or set, return a same type where each element is a serializable object (recursive call)
    - if it is a dict, return a dict where each key and element are serializable objects (recursive call)
    - otherwise, try to json-serialize to string and, if it fails, return the str(object) value
    """
    if isinstance(value, (int, str, float, bool)):
        return value
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (list, tuple, set)):
        return type(value)(_try_to_dict_or_str(v) for v in value)
    if isinstance(value, dict):
        return {_try_to_dict_or_str(k): _try_to_dict_or_str(v) for k, v in value.items()}
    try:
        return json.dumps(value)
    except TypeError:
        return str(value)


def _result_to_dict(result: Tuple[Any, Dict[Hashable, Any]]) -> Dict[str, Any]:
    """Normalise a metric result tuple into a serializable dictionary."""
    value, details = result
    return {
        "value": _try_to_dict_or_str(value),
        "details": _try_to_dict_or_str(details),
    }
