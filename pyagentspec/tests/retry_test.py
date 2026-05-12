# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Retry helpers for tests that depend on external services."""

from __future__ import annotations

import inspect
import logging
import math
import os
import re
import time
import traceback
from dataclasses import dataclass
from datetime import date, datetime
from functools import wraps
from typing import Any, Awaitable, Callable, Optional, TypeVar, cast

logger = logging.getLogger(__name__)

DISABLE_RETRY = "DISABLE_RETRY"
FLAKY_TEST_EVALUATION_MODE = "FLAKY_TEST_EVALUATION_MODE"
FLAKY_TEST_MAX_EXECUTION_TIME_PER_TEST = 20 * 60  # seconds

FLAKY_TEST_DOCSTRING_TEMPLATE = """
    \"\"\"
    Failure rate:          {{ failed_attempts }} out of {{ total_attempts }}
    Observed on:           {{ iso_date }}
    Average success time:  {% if average_success_time %}{{ "%.2f"|format(average_success_time) }} seconds per successful attempt{% else %}No time measurement{% endif %}
    Average failure time:  {% if average_failure_time %}{{ "%.2f"|format(average_failure_time) }} seconds per failed attempt{% else %}No time measurement{% endif %}
    Max attempt:           {{ max_attempts }}
    Justification:         ({{ "%.2f"|format(failure_rate) }} ** {{ max_attempts }}) ~= {{ "%.1f"|format(expected_failure_per_100_000) }} / 100'000
    \"\"\"
"""

FLAKY_TEST_FAILURE_ERROR_MESSAGE_TEMPLATE = """
A flaky test "{test_name}" failed all of the {max_attempts} attempts.

Either:
(1) Your code changes had a bug that made the test fail. In that case, simply
update your changes.
(2) The test error is not due to your code changes. In that case, please
re-evaluate the failure rate of the test with the command:
$ FLAKY_TEST_EVALUATION_MODE=100 pytest {test_file}::{test_name}

Be careful not to use a high number of repetitions when evaluating models
behind APIs in order not to consume too many API credits.

Find below the traceback from the error in the last test attempt:

{error_traceback}
"""

FLAKY_WRONG_DOCSTRING_ERROR_MESSAGE_TEMPLATE = """
The flaky test {test_name} seems to have no docstring or a docstring with an
incorrect format. You can automatically re-evaluate the failure rate of the test
and generate a suggestion for the docstring with the command:
$ FLAKY_TEST_EVALUATION_MODE=100 pytest {test_file}::{test_name}

If the test you are evaluating outputs too much logs, you can make pytest hide
these logs using the option `--show-capture=log --disable-warnings`.
"""

FLAKY_TEST_DOCSTRING_REGEX_PATTERN = (
    r"[\s\S]*Failure rate:.*\n\s*Observed on:.*\n\s*Average success time:.*\n"
    r"\s*Average failure time:.*\n\s*Max attempt:.*\n\s*Justification:.*"
)

T = TypeVar("T")


def _validate_retry_decorator_docstring_format(test_func: Callable[..., Any]) -> None:
    if test_func.__doc__ and re.match(FLAKY_TEST_DOCSTRING_REGEX_PATTERN, test_func.__doc__):
        return
    logger.error(
        "Failed to find a correctly formatted retry information in docstring %s",
        test_func.__doc__,
    )
    raise ValueError(
        FLAKY_WRONG_DOCSTRING_ERROR_MESSAGE_TEMPLATE.format(
            test_name=test_func.__name__,
            test_file=test_func.__globals__["__file__"],
        )
    )


@dataclass
class FlakyTestStatistics:
    n_success: int
    n_failure: int
    total_time_success: Optional[float] = None
    total_time_failure: Optional[float] = None
    observation_date: Optional[datetime] = None

    @property
    def total_attempts(self) -> int:
        return self.n_failure + self.n_success

    @property
    def estimated_fail_rate(self) -> float:
        # We estimate the failure rate using Laplace Rule of Succession
        # See: https://en.wikipedia.org/wiki/Rule_of_succession
        # This makes the estimation of failure rate more robust. In particular
        # It does not estimate 100% success when we have 5 out of 5 successes
        return (self.n_failure + 1) / (self.n_failure + self.n_success + 2)

    @property
    def suggested_num_attempts(self) -> int:
        # We estimate the suggested number of attempts based on the objective
        # that we want strictly less than 1 in 10'000 expected failure. Thus giving
        # us the formula:
        #
        #     fail_rate ** N < 1/10'000
        #
        #  Which is transformed with a bit of mathematical magic into:
        #
        #     N > - log(10'000) / log(fail_rate)
        return math.ceil(-math.log(10_000) / math.log(self.estimated_fail_rate))

    @property
    def expected_failure_per_100_000(self) -> float:
        return 100_000 * (self.estimated_fail_rate**self.suggested_num_attempts)

    @property
    def average_success_time(self) -> Optional[float]:
        if self.n_success == 0 or self.total_time_success is None:
            return None
        return self.total_time_success / self.n_success

    @property
    def average_failure_time(self) -> Optional[float]:
        if self.n_failure == 0 or self.total_time_failure is None:
            return None
        return self.total_time_failure / self.n_failure


def _get_suggested_flaky_test_docstring(
    n_success: int, n_failure: int, time_success: float, time_failure: float
) -> str:
    """
    Generate a suggestion of docstring for a flaky based on observations obtained when
    running a test multiple times.

    Parameters
    ----------
    n_success:
        the number of successes observed
    n_failed:
        the number of failures observed
    time_success:
        the total time taken by all successful runs
    """
    test_stats = FlakyTestStatistics(n_success, n_failure, time_success, time_failure)
    average_success_time = (
        f"{test_stats.average_success_time:.2f} seconds per successful attempt"
        if test_stats.average_success_time is not None
        else "No time measurement"
    )
    average_failure_time = (
        f"{test_stats.average_failure_time:.2f} seconds per failed attempt"
        if test_stats.average_failure_time is not None
        else "No time measurement"
    )
    return f"""
    \"\"\"
    Failure rate:          {test_stats.n_failure} out of {test_stats.total_attempts}
    Observed on:           {date.today().isoformat()}
    Average success time:  {average_success_time}
    Average failure time:  {average_failure_time}
    Max attempt:           {test_stats.suggested_num_attempts}
    Justification:         ({test_stats.estimated_fail_rate:.2f} ** {test_stats.suggested_num_attempts}) ~= {test_stats.expected_failure_per_100_000:.1f} / 100'000
    \"\"\"
"""


def retry_test(
    max_attempts: int = 3, wait_between_tries: int = 0
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorate a test function in order to attempt to run it again when it fails. This is
    particularly useful for tests that tend to be failing a small fraction of the time due to
    involving unreliable LLMs.

    Parameters
    ----------
    max_attempt:
        The maximum number of attempts the test will be attempted. Note than in average the test
        will be attempted `1/(1-failure_rate)` times (e.g. 1.1 times for a 10% failure rate)
    wait_between_tries:
        The number of seconds to wait after a failed attempt of the test. This can be useful for
        example for tests which make requests to remote APIs which may be rate limited.

    Examples
    --------
    You can decorate your test
    ```python
    @retry_test(max_attempts=10)
    def test_random_number_is_above_two_third():
        \"\"\"
        Failure rate:  63 out of 100
        Observed on:   2024-09-30
        Average success time:  0.00 seconds per successful attempt
        Average failure time:  0.00 seconds per failed attempt
        Max attempt:   20
        Justification: (0.63 ** 20) ~= 8.9 / 100'000
        \"\"\"
        assert random.random() > 2/3
    ```

    Notes
    -----
    The decorator can be used in combination with two environment variables:

    (1) Reevaluate the failure rate for a given test and generate a suggestion for max_attempts
    and the explanation docstring.
    Usage:
    ```bash
    $ FLAKY_TEST_EVALUATION_MODE=<repeat_count> pytest tests/<test_file>::<test_name>
    ```
    In that command, you should specify the repeat_count, test_file and test_name. Note that
    repeat_count should be large enough to get some statistical significance. In practice, a value
    of 20, 50 or 100 would be good to use. The value passed for repeat_count must be a number.

    (2) Disable all retries and run all tests
    ```bash
    $ DISABLE_RETRY=true pytest tests/
    ```
    """
    if max_attempts > 16:
        # The number 16 is chosen, because it is the number of attempts needed
        # when a test has roughly 50% failure rate, which is already quite a
        # for us to want that test in our test-suite.
        raise ValueError(
            "You are trying to set a number of attempt more than the maximum "
            "limit of 16. This is a sign that your test has a very high "
            "failure rate, and we encourage you to make the test more robust "
            "before adding it to the test suite."
        )

    if os.environ.get(DISABLE_RETRY, False):
        change_nothing_decorator = lambda func: func
        return change_nothing_decorator

    if os.environ.get(FLAKY_TEST_EVALUATION_MODE, False):
        repeat_count = int(os.environ[FLAKY_TEST_EVALUATION_MODE])

        def repeat_evaluate_and_generate_docstring_decorator(
            test_func: Callable[..., T],
        ) -> Callable[..., T]:
            if inspect.iscoroutinefunction(test_func):

                @wraps(test_func)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    suggested_docstring, num_total_attempts = await _evaluate_async_flakiness(
                        cast(Callable[..., Awaitable[Any]], test_func),
                        repeat_count=repeat_count,
                        wait_between_tries=wait_between_tries,
                        args=args,
                        kwargs=kwargs,
                    )
                    raise ValueError(
                        _format_flaky_evaluation_completion_message(
                            repeat_count,
                            num_total_attempts,
                            suggested_docstring,
                        )
                    )

                return cast(Callable[..., T], async_wrapper)

            @wraps(test_func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                suggested_docstring, num_total_attempts = _evaluate_sync_flakiness(
                    test_func,
                    repeat_count=repeat_count,
                    wait_between_tries=wait_between_tries,
                    args=args,
                    kwargs=kwargs,
                )
                raise ValueError(
                    _format_flaky_evaluation_completion_message(
                        repeat_count,
                        num_total_attempts,
                        suggested_docstring,
                    )
                )

            return cast(Callable[..., T], wrapper)

        return repeat_evaluate_and_generate_docstring_decorator

    def repeat_flaky_test_decorator(test_func: Callable[..., T]) -> Callable[..., T]:
        _validate_retry_decorator_docstring_format(test_func)

        if inspect.iscoroutinefunction(test_func):

            @wraps(test_func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await _run_async_attempts(
                    cast(Callable[..., Awaitable[Any]], test_func),
                    max_attempts=max_attempts,
                    wait_between_tries=wait_between_tries,
                    args=args,
                    kwargs=kwargs,
                )

            return cast(Callable[..., T], async_wrapper)

        @wraps(test_func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return _run_sync_attempts(
                test_func,
                max_attempts=max_attempts,
                wait_between_tries=wait_between_tries,
                args=args,
                kwargs=kwargs,
            )

        return cast(Callable[..., T], wrapper)

    return repeat_flaky_test_decorator


def _evaluate_sync_flakiness(
    test_func: Callable[..., T],
    *,
    repeat_count: int,
    wait_between_tries: int,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> tuple[str, int]:
    success_count = 0
    failed_count = 0
    total_time_of_successful_runs = 0.0
    total_time_of_failed_runs = 0.0
    loop_start_time = time.time()
    for _ in range(repeat_count):
        start_time = time.perf_counter()
        try:
            test_func(*args, **kwargs)
            total_time_of_successful_runs += time.perf_counter() - start_time
            success_count += 1
        except Exception:
            failed_count += 1
            total_time_of_failed_runs += time.perf_counter() - start_time
            time.sleep(wait_between_tries)
        if time.time() - loop_start_time > FLAKY_TEST_MAX_EXECUTION_TIME_PER_TEST:
            break

    num_total_attempts = success_count + failed_count
    suggested_docstring = _get_suggested_flaky_test_docstring(
        success_count,
        failed_count,
        total_time_of_successful_runs,
        total_time_of_failed_runs,
    )
    return suggested_docstring, num_total_attempts


async def _evaluate_async_flakiness(
    test_func: Callable[..., Awaitable[T]],
    *,
    repeat_count: int,
    wait_between_tries: int,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> tuple[str, int]:
    success_count = 0
    failed_count = 0
    total_time_of_successful_runs = 0.0
    total_time_of_failed_runs = 0.0
    loop_start_time = time.time()
    for _ in range(repeat_count):
        start_time = time.perf_counter()
        try:
            await test_func(*args, **kwargs)
            total_time_of_successful_runs += time.perf_counter() - start_time
            success_count += 1
        except Exception:
            failed_count += 1
            total_time_of_failed_runs += time.perf_counter() - start_time
            time.sleep(wait_between_tries)
        if time.time() - loop_start_time > FLAKY_TEST_MAX_EXECUTION_TIME_PER_TEST:
            break

    num_total_attempts = success_count + failed_count
    suggested_docstring = _get_suggested_flaky_test_docstring(
        success_count,
        failed_count,
        total_time_of_successful_runs,
        total_time_of_failed_runs,
    )
    return suggested_docstring, num_total_attempts


def _format_flaky_evaluation_completion_message(
    repeat_count: int,
    num_total_attempts: int,
    suggested_docstring: str,
) -> str:
    timeout_message = (
        " (achieved "
        f"{num_total_attempts} retry due to time limit of "
        f"{FLAKY_TEST_MAX_EXECUTION_TIME_PER_TEST // 60:.2f} minutes)"
        if repeat_count != num_total_attempts
        else ""
    )
    return (
        f"You ran the test with FLAKY_TEST_EVALUATION_MODE={repeat_count}{timeout_message}\n"
        f"This always fails and is expected to. Nothing wrong about this failure.\n"
        f"Find below the recommended docstring and attempt count for your test:\n\n"
        f"{suggested_docstring}"
    )


def _run_sync_attempts(
    test_func: Callable[..., T],
    *,
    max_attempts: int,
    wait_between_tries: int,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> T:
    attempt_count = 0
    last_error, last_error_traceback = None, None
    logger.info("Starting %s attempts for test %s", max_attempts, test_func.__name__)
    while attempt_count < max_attempts:
        try:
            return test_func(*args, **kwargs)
        except Exception as exception_error:
            exception_message = exception_error.__str__().split("\n", maxsplit=1)[0]
            attempt_count += 1
            logger.warning(
                "Attempt [%s/%s] failed with error: %s.",
                attempt_count,
                max_attempts,
                exception_message,
            )
            logger.info(
                "Retrying %s new execution in %s second(s)",
                test_func.__name__,
                wait_between_tries,
            )
            if attempt_count == max_attempts:
                last_error = exception_error
                last_error_traceback = "".join(traceback.format_exc())
            else:
                time.sleep(wait_between_tries)

    raise ValueError(
        FLAKY_TEST_FAILURE_ERROR_MESSAGE_TEMPLATE.format(
            test_name=test_func.__name__,
            test_file=test_func.__globals__["__file__"],
            max_attempts=max_attempts,
            error_traceback=last_error_traceback,
        )
    ) from last_error


async def _run_async_attempts(
    test_func: Callable[..., Awaitable[T]],
    *,
    max_attempts: int,
    wait_between_tries: int,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> T:
    attempt_count = 0
    last_error, last_error_traceback = None, None
    logger.info("Starting %s attempts for test %s", max_attempts, test_func.__name__)
    while attempt_count < max_attempts:
        try:
            return await test_func(*args, **kwargs)
        except Exception as exception_error:
            exception_message = exception_error.__str__().split("\n", maxsplit=1)[0]
            attempt_count += 1
            logger.warning(
                "Attempt [%s/%s] failed with error: %s.",
                attempt_count,
                max_attempts,
                exception_message,
            )
            logger.info(
                "Retrying %s new execution in %s second(s)",
                test_func.__name__,
                wait_between_tries,
            )
            if attempt_count == max_attempts:
                last_error = exception_error
                last_error_traceback = "".join(traceback.format_exc())
            else:
                time.sleep(wait_between_tries)

    raise ValueError(
        FLAKY_TEST_FAILURE_ERROR_MESSAGE_TEMPLATE.format(
            test_name=test_func.__name__,
            test_file=test_func.__globals__["__file__"],
            max_attempts=max_attempts,
            error_traceback=last_error_traceback,
        )
    ) from last_error
