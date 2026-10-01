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

T = TypeVar("T")


class AsyncContext(Enum):
    ASYNC = "async"
    SYNC = "sync"
    SYNC_WORKER = "sync_worker"


def _is_anyio_worker_thread() -> bool:
    try:
        # AnyIO allows this check only in threads it started for sync work.
        from_thread.check_cancelled()
    except RuntimeError:
        return False
    else:
        return True


def _is_async_context() -> bool:
    try:
        anyio.get_current_task()
    except Exception:
        # Need to catch a generic Exception.
        # AnyIO 4.12.0 raised NoCurrentAsyncBackend here; it does not inherit
        # from RuntimeError like the no-loop exceptions in other supported versions.
        return False
    else:
        return True


def get_execution_context() -> AsyncContext:
    """Check whether this call is running in async code or sync code."""
    if _is_async_context():
        return AsyncContext.ASYNC

    # Sync code may still be running in a thread started by AnyIO.
    if _is_anyio_worker_thread():
        return AsyncContext.SYNC_WORKER

    # No event loop or AnyIO worker: this is an ordinary sync call.
    return AsyncContext.SYNC


def run_async_in_sync(
    async_function: Callable[..., Coroutine[Any, Any, T]], *args: Any, method_name: str = ""
) -> T:
    """Run an asynchronous function from synchronous or asynchronous code."""
    match get_execution_context():
        case AsyncContext.SYNC:
            # A regular sync call needs its own event loop to run the coroutine.
            return anyio.run(async_function, *args)
        case AsyncContext.SYNC_WORKER:
            # Return to the event loop that started this AnyIO worker thread.
            return from_thread.run(async_function, *args)
        case AsyncContext.ASYNC:
            # The current thread already has an event loop, so run the coroutine
            # in a new thread with its own loop instead.
            def thread_target() -> T:
                return anyio.run(async_function, *args)

            future = ThreadPoolExecutor(max_workers=1).submit(thread_target)
            return future.result()
        case unsupported_context:
            raise NotImplementedError(f"Unsupported async context: {unsupported_context}")
