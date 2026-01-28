# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, TypeVar

T = TypeVar("T")


@contextmanager
def retry_attempts(
    max_attempts: int = 3,
    *,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
):
    """
    Context manager that yields a retry helper for flaky agent executions.

    Usage:
        with retry_attempts() as attempt:
            result = attempt(lambda: run_agent(), validate=lambda r: "ok" in r)

    - Runs the callable up to `max_attempts` times.
    - If `validate` is provided, it must return True for success.
    - Retries on raised exceptions in `exceptions` or when validation fails.
    - Raises the last exception (or AssertionError) if all attempts fail.
    """

    def _attempt(fn: Callable[[], T], *, validate: Callable[[T], bool] | None = None) -> T:
        last_exc: BaseException | None = None
        for i in range(1, max_attempts + 1):
            try:
                result = fn()
                if validate is None or validate(result):
                    return result
                last_exc = AssertionError(f"Validation failed on attempt {i}/{max_attempts}")
            except exceptions as e:  # type: ignore[misc]
                last_exc = e
            # try again unless out of attempts
        if last_exc is not None:
            raise last_exc
        raise AssertionError("retry_attempts: all attempts failed without an exception detail")

    yield _attempt
