# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Any, Callable, Coroutine, TypeVar

import anyio
from anyio import from_thread
from sniffio import AsyncLibraryNotFoundError, current_async_library

T = TypeVar("T")


class AsyncContext(Enum):
    ASYNC = "async"
    SYNC = "sync"
    SYNC_WORKER = "sync_worker"


def _is_anyio_worker_thread() -> bool:
    try:
        # check_cancelled() is a lightweight public API (no I/O, no scheduling)
        # that only succeeds inside an AnyIO worker thread spawned by
        # to_thread.run_sync(). Outside that context it raises RuntimeError.
        from_thread.check_cancelled()
    except RuntimeError:
        return False
    else:
        return True


def get_execution_context() -> AsyncContext:
    """Determine whether the current code is sync, async, or in an AnyIO worker."""
    try:
        current_async_library()
        return AsyncContext.ASYNC
    except AsyncLibraryNotFoundError:
        if _is_anyio_worker_thread():
            return AsyncContext.SYNC_WORKER

        return AsyncContext.SYNC


def run_async_in_sync(
    async_function: Callable[..., Coroutine[Any, Any, T]], *args: Any, method_name: str = ""
) -> T:
    """Run an asynchronous function from synchronous or asynchronous code."""
    match get_execution_context():
        case AsyncContext.SYNC:
            return anyio.run(async_function, *args)
        case AsyncContext.SYNC_WORKER:
            return from_thread.run(async_function, *args)
        case AsyncContext.ASYNC:
            # AnyIO cannot run an async function synchronously from an async context
            # unless the caller is an AnyIO worker, so use a fresh event loop/thread.
            def thread_target() -> T:
                return anyio.run(async_function, *args)

            future = ThreadPoolExecutor(max_workers=1).submit(thread_target)
            return future.result()
        case unsupported_context:
            raise NotImplementedError(f"Unsupported async context: {unsupported_context}")
