# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import asyncio
import ssl
import warnings
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Any, Awaitable, Callable, Optional, TypeVar

import anyio
import httpx
from anyio import from_thread
from sniffio import AsyncLibraryNotFoundError

T = TypeVar("T")


class _HttpxClientFactory:
    def __init__(
        self,
        verify: bool = True,
        key_file: Optional[str] = None,
        cert_file: Optional[str] = None,
        ssl_ca_cert: Optional[str] = None,
        check_hostname: bool = True,
        follow_redirects: bool = True,
    ):
        self.verify: bool | ssl.SSLContext
        if verify:
            # Default behaviour: Client verification
            if not (key_file and cert_file and ssl_ca_cert):
                raise ValueError(
                    "When verify=True, all `key_file`, `cert_file` and `ssl_ca_cert` "
                    "must be defined."
                )
            ssl_ctx = ssl.create_default_context(cafile=ssl_ca_cert)
            ssl_ctx.load_cert_chain(certfile=cert_file, keyfile=key_file)
            ssl_ctx.check_hostname = check_hostname
            self.verify = ssl_ctx
        else:
            # If verify=False the cert/key files should not be specified
            if key_file or cert_file or ssl_ca_cert:
                raise ValueError(
                    "Either specify (`key_file`, `cert_file`, `ssl_ca_cert`) "
                    "or `verify=False`, not both."
                )
            self.verify = verify

        self.follow_redirects = follow_redirects

    def __call__(
        self,
        headers: dict[str, str] | None = None,
        timeout: httpx.Timeout | None = None,
        auth: httpx.Auth | None = None,
    ) -> httpx.AsyncClient:
        # Set MCP defaults
        kwargs: dict[str, Any] = {
            "follow_redirects": self.follow_redirects,
            "verify": self.verify,
        }
        # Handle timeout
        if timeout is None:
            kwargs["timeout"] = httpx.Timeout(30.0)
        else:
            kwargs["timeout"] = timeout
        # Handle headers
        if headers is not None:
            kwargs["headers"] = headers
        # Handle authentication
        if auth is not None:
            kwargs["auth"] = auth
        return httpx.AsyncClient(**kwargs)


class AsyncContext(Enum):
    ASYNC = "async"
    SYNC = "sync"
    SYNC_WORKER = "sync_worker"


def get_execution_context() -> AsyncContext:
    """
    Return one of:
    - 'sync'         → plain synchronous context (no loop, no worker thread)
    - 'sync_worker'  → synchronous worker thread (spawned by to_thread.run_sync)
    - 'async'        → running inside the event loop
    """
    try:
        anyio.get_current_task()
        return AsyncContext.ASYNC
    except AsyncLibraryNotFoundError:
        current_thread = from_thread.current_thread()  # type: ignore
        worker_name = current_thread.name.lower()
        if "worker" in worker_name and "anyio" in worker_name:
            # for anyio workers, we can use specific methods to
            # handle back asynchronous code to the main loop
            return AsyncContext.SYNC_WORKER
        else:
            # otherwise, consider it as a synchronous thread
            return AsyncContext.SYNC


def run_async_in_sync(
    async_function: Callable[..., Awaitable[T]], *args: Any, method_name: str = ""
) -> T:
    """
    Runs an asynchronous function in any context, choosing the most efficient way to do so
    """
    match get_execution_context():
        case AsyncContext.SYNC:
            # case 1: synchronous context
            return anyio.run(async_function, *args)
        case AsyncContext.SYNC_WORKER:
            # case 2: from worker thread get back to existing async event loop
            return from_thread.run(async_function, *args)
        case AsyncContext.ASYNC:
            # case 3: from async main context
            # this is highly discouraged since it synchronises work that could
            # be just run async
            # warnings.warn(
            #     "You are calling an asynchronous method in a synchronous method from an asynchronous context. "
            #     "This is highly discouraged because it can lead to deadlocks. "
            #     f"Please use the asynchronous method equivalent: {method_name}",
            #     UserWarning,
            # )

            # workaround: anyio does not have any API run asynchronous code in a
            # synchronous method that was not started with anyio.to_thread
            # instead, we spawn a thread to execute it in a completely new event loop
            def thread_target() -> T:
                return anyio.run(async_function, *args)

            future = ThreadPoolExecutor(max_workers=1).submit(thread_target)
            return future.result()
        case unsupported_context:
            raise NotImplementedError(f"Unsupported async context: {unsupported_context}")


def _run_async_in_sync_simple(
    async_function: Callable[..., Awaitable[T]], *args: Any, method_name: str = ""
) -> T:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No loop in this thread (e.g., run_in_executor worker): safe to create one
        return asyncio.run(async_function(*args))  # type: ignore
    else:
        # We’re already on an event loop; blocking is dangerous. Warn and offload.
        warnings.warn(
            f"Calling async from sync on a running loop; prefer using {method_name} async.",
            UserWarning,
        )

        def thread_target() -> T:
            return asyncio.run(async_function(*args))  # type: ignore

        with ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(thread_target).result()
