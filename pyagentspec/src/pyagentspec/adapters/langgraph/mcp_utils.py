# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import ssl
import warnings
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Any, Awaitable, Callable, Optional, TypeVar

import anyio
import httpx
from anyio import from_thread
from sniffio import AsyncLibraryNotFoundError, current_async_library

T = TypeVar("T")


class _HttpxClientFactory:
    """Build HTTPX async clients for MCP transports with explicit TLS verification."""

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
            ssl_ctx = ssl.create_default_context()
            if ssl_ca_cert:
                ssl_ctx.load_verify_locations(cafile=ssl_ca_cert)

            if key_file or cert_file:
                # Client authentication requires both pieces of certificate material.
                if not (key_file and cert_file):
                    raise ValueError(
                        "When client certificates are provided, both `key_file` and "
                        "`cert_file` must be defined."
                    )
                ssl_ctx.load_cert_chain(certfile=cert_file, keyfile=key_file)
            ssl_ctx.check_hostname = check_hostname
            if not check_hostname:
                warnings.warn(
                    "TLS hostname verification is disabled for this MCP HTTP client.",
                    UserWarning,
                    stacklevel=2,
                )
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
    """
    Return one of:
    - 'sync'         → plain synchronous context (no loop, no worker thread)
    - 'sync_worker'  → synchronous worker thread (spawned by to_thread.run_sync)
    - 'async'        → running inside the event loop
    """
    try:
        current_async_library()
        return AsyncContext.ASYNC
    except AsyncLibraryNotFoundError:
        if _is_anyio_worker_thread():
            # for anyio workers, we can use specific methods to
            # handle back asynchronous code to the main loop
            return AsyncContext.SYNC_WORKER

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
