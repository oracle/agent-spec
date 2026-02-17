# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import asyncio
import random
from copy import deepcopy
from typing import Any, Awaitable, Callable, Dict, List, Literal, Tuple

import pytest

from pyagentspec.evaluation import Dataset
from pyagentspec.evaluation._computers import _AsyncCallablesComputer
from pyagentspec.evaluation.metrics import Metric


class LogRegistry:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._logs: List[Tuple[Literal["begin", "end"], int]] = []

    async def log(self, type: Literal["begin", "end"], id: int) -> None:
        async with self._lock:
            self._logs.append((type, id))

    async def get_logs(self) -> List[Tuple[Literal["begin", "end"], int]]:
        async with self._lock:
            return deepcopy(self._logs)

    async def get_num_runnings_sequence(self) -> List[int]:
        num_runnings = [0]
        async with self._lock:
            for log_type, _ in self._logs:
                if log_type == "begin":
                    num_runnings.append(num_runnings[-1] + 1)
                elif log_type == "end":
                    num_runnings.append(num_runnings[-1] - 1)
                else:
                    raise ValueError(f"Unexpected log_type {log_type}.")
        return num_runnings


class IoIntensiveMetric(Metric[Any]):
    def __init__(
        self,
        log_registry: LogRegistry,
        io_time_lower_bound: int,
        io_time_upper_bound: int,
        scale_factor: float,
    ) -> None:
        super().__init__(
            name="io_intensive_metric",
            input_mapping=None,
            num_retries=0,
            on_failure="raise",
        )
        self.log_registry = log_registry
        self.io_time_lb = io_time_lower_bound
        self.io_time_ub = io_time_upper_bound
        self.scale_factor = scale_factor

    async def _io(self) -> None:
        io_time = random.randint(  # nosec: Not used for cryptography
            self.io_time_lb, self.io_time_ub
        )
        io_time /= self.scale_factor
        await asyncio.sleep(io_time)

    async def compute_metric(self, dummy_arg: int) -> Tuple[Any, Dict[str, Any]]:
        await self.log_registry.log("begin", dummy_arg)
        await self._io()
        await self.log_registry.log("end", dummy_arg)
        return -dummy_arg, {}


@pytest.mark.anyio
async def test_sequential_running() -> None:
    num_samples = 20
    dataset = Dataset.from_dict([{"dummy_arg": i} for i in range(num_samples)])
    log_registry = LogRegistry()
    callables: Dict[str, Callable[..., Awaitable[Any]]] = {
        "dummy_callable": IoIntensiveMetric(log_registry, 1, 10, 1000)
    }
    computer = _AsyncCallablesComputer(
        dataset=dataset,
        callables=callables,
        max_concurrency=1,
    )
    await computer.run()
    logs = await log_registry.get_logs()

    for i in range(num_samples):
        assert logs[2 * i] == ("begin", i)
        assert logs[2 * i + 1] == ("end", i)


@pytest.mark.anyio
async def test_unlimited_concurrency() -> None:
    num_samples = 200
    dataset = Dataset.from_dict([{"dummy_arg": i} for i in range(num_samples)])
    log_registry = LogRegistry()
    callables: Dict[str, Callable[..., Awaitable[Any]]] = {
        "dummy_callable": IoIntensiveMetric(log_registry, 1, 10, 1000)
    }
    computer = _AsyncCallablesComputer(
        dataset=dataset,
        callables=callables,
        max_concurrency=-1,
    )
    await computer.run()
    logs = await log_registry.get_logs()
    num_runnings_sequence = await log_registry.get_num_runnings_sequence()

    for i in range(num_samples):
        assert logs[i] == ("begin", i)

    for i in range(len(dataset) + 1):
        assert num_runnings_sequence[i] == i
        assert num_runnings_sequence[-i - 1] == i


@pytest.mark.anyio
async def test_run_does_not_spawn_one_task_per_item() -> None:
    """
    Ensure ``_AsyncCallablesComputer.run`` does not create O(N) tasks.
    This is a regression test for memory blow-ups when datasets are large.
    """

    class CountingTaskGroup:
        def __init__(self, max_allowed: int) -> None:
            self.max_allowed = max_allowed
            self.started = 0

        async def __aenter__(self) -> "CountingTaskGroup":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        def start_soon(self, func, *args) -> None:
            self.started += 1
            assert self.started <= self.max_allowed

    dataset = Dataset.from_dict([{"dummy_arg": i} for i in range(10000)])
    callables = {"dummy_callable": (lambda **kwargs: asyncio.sleep(0))}
    computer = _AsyncCallablesComputer(
        dataset=dataset,
        callables=callables,
        max_concurrency=10,
    )

    import anyio  # imported here to keep the patch localized to this test

    original = anyio.create_task_group
    try:
        anyio.create_task_group = lambda: CountingTaskGroup(max_allowed=1 + 10)
        await computer.run()
    finally:
        anyio.create_task_group = original


@pytest.mark.anyio
@pytest.mark.parametrize("max_concurrency", [5, 10, 20])
async def test_max_concurrency_is_respected(max_concurrency: int) -> None:
    num_samples = 200

    dataset = Dataset.from_dict([{"dummy_arg": i} for i in range(num_samples)])
    log_registry = LogRegistry()
    callables: Dict[str, Callable[..., Awaitable[Any]]] = {
        "dummy_callable": IoIntensiveMetric(log_registry, 1, 10, 1000)
    }
    computer = _AsyncCallablesComputer(
        dataset=dataset,
        callables=callables,
        max_concurrency=max_concurrency,
    )
    await computer.run()
    num_runnings_sequence = await log_registry.get_num_runnings_sequence()

    assert all(n <= max_concurrency for n in num_runnings_sequence)
