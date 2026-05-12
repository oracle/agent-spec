# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import inspect
import logging
import math
import os
import re
import time
import traceback
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import wraps
from typing import Any, Callable, NoReturn, Optional

logger = logging.getLogger(__name__)

DISABLE_RETRY = "DISABLE_RETRY"
FLAKY_TEST_EVALUATION_MODE = "FLAKY_TEST_EVALUATION_MODE"
FLAKY_TEST_MAX_EXECUTION_TIME_PER_TEST = 20 * 60  # seconds

_AVERAGE_SUCCESS_TIME_TEMPLATE = (
    '{% if average_success_time %}{{ "%.2f"|format(average_success_time) }} '
    "seconds per successful attempt{% else %}No time measurement{% endif %}"
)
_AVERAGE_FAILURE_TIME_TEMPLATE = (
    '{% if average_failure_time %}{{ "%.2f"|format(average_failure_time) }} '
    "seconds per failed attempt{% else %}No time measurement{% endif %}"
)
_JUSTIFICATION_TEMPLATE = (
    '({{ "%.2f"|format(failure_rate) }} ** {{ max_attempts }}) ~= '
    '{{ "%.1f"|format(expected_failure_per_100_000) }} / 100\'000'
)

FLAKY_TEST_DOCSTRING_TEMPLATE = (
    """
    \"\"\"
    Failure rate:          {{ failed_attempts }} out of {{ total_attempts }}
    Observed on:           {{ iso_date }}
    Average success time:  """
    + _AVERAGE_SUCCESS_TIME_TEMPLATE
    + """
    Average failure time:  """
    + _AVERAGE_FAILURE_TIME_TEMPLATE
    + """
    Max attempt:           {{ max_attempts }}
    Justification:         """
    + _JUSTIFICATION_TEMPLATE
    + """
    \"\"\"
"""
)

FLAKY_TEST_FAILURE_ERROR_MESSAGE_TEMPLATE = """
A flaky test "{{ test_name }}" failed all of the {{ max_attempts }} attempts.

⚠️ Either:
(1) Your code changes had a bug that made the test fail. In that case, simply
update your changes
(2) The test error is not due to your code changes. In that case, please
re-evaluate the failure rate of the test with the command:
$ FLAKY_TEST_EVALUATION_MODE=100 pytest {{test_file}}::{{test_name}}

⚠️ Be careful not to use a high number of repetition when evaluating models
behind APIs (e.g. OpenAI) in order not to consume too many API credits.

Find below the traceback from the error in the last test attempt:

{{ error_traceback }}
"""

FLAKY_WRONG_DOCSTRING_ERROR_MESSAGE_TEMPLATE = """
The flaky test {{test_name}} seems to have no doctstring or a docstring with an
incorrect format. You can automatically re-evaluate the failure rate of the test
and generate a suggestion for the docstring with the command:
$ FLAKY_TEST_EVALUATION_MODE=100 pytest {{test_file}}::{{test_name}}

If the test you are evaluating outputs too much logs, you can make pytest hide
these logs using the option `--show-capture=log --disable-warnings`.
"""

FLAKY_TEST_DOCSTRING_REGEX_PATTERN = (
    r"[\s\S]*Failure rate:.*\n\s*Observed on:.*\n\s*Average success time:.*\n"
    r"\s*Average failure time:.*\n\s*Max attempt:.*\n\s*Justification:.*"
)


class bcolors:
    BOLD = "\033[1m"
    OKBLUE = "\033[94m"
    ENDC = "\033[0m"


def render_template(template: str, inputs: dict[str, Any]) -> str:
    """Render the retry-test templates used by this module."""
    rendered = template
    rendered = rendered.replace(
        _AVERAGE_SUCCESS_TIME_TEMPLATE,
        (
            "{:.2f} seconds per successful attempt".format(inputs["average_success_time"])
            if inputs.get("average_success_time")
            else "No time measurement"
        ),
    )
    rendered = rendered.replace(
        _AVERAGE_FAILURE_TIME_TEMPLATE,
        (
            "{:.2f} seconds per failed attempt".format(inputs["average_failure_time"])
            if inputs.get("average_failure_time")
            else "No time measurement"
        ),
    )
    rendered = re.sub(
        r'{{\s*"%.2f"\|format\(([^}]+)\)\s*}}',
        lambda match: format(inputs[match.group(1).strip()], ".2f"),
        rendered,
    )
    rendered = re.sub(
        r'{{\s*"%.1f"\|format\(([^}]+)\)\s*}}',
        lambda match: format(inputs[match.group(1).strip()], ".1f"),
        rendered,
    )
    return re.sub(
        r"{{\s*([^}]+)\s*}}",
        lambda match: str(inputs.get(match.group(1).strip(), match.group(0))),
        rendered,
    )


def _validate_retry_decorator_docstring_format(test_func: Callable[..., Any]) -> None:
    if not test_func.__doc__ or not re.match(FLAKY_TEST_DOCSTRING_REGEX_PATTERN, test_func.__doc__):
        logger.error(
            "Failed to find a correctly formatted retry information in docstring %s",
            test_func.__doc__,
        )
        raise ValueError(
            render_template(
                template=FLAKY_WRONG_DOCSTRING_ERROR_MESSAGE_TEMPLATE,
                inputs=dict(
                    test_name=test_func.__name__,
                    test_file=test_func.__globals__["__file__"],
                ),
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
    suggested_docstring = render_template(
        template=FLAKY_TEST_DOCSTRING_TEMPLATE,
        inputs=dict(
            failed_attempts=test_stats.n_failure,
            total_attempts=test_stats.total_attempts,
            failure_rate=test_stats.estimated_fail_rate,
            iso_date=date.today().isoformat(),
            average_success_time=test_stats.average_success_time,
            average_failure_time=test_stats.average_failure_time,
            max_attempts=test_stats.suggested_num_attempts,
            expected_failure_per_100_000=test_stats.expected_failure_per_100_000,
        ),
    )
    return suggested_docstring


def _get_suggested_flaky_test_docstring_from_stats(
    test_stats: FlakyTestStatistics,
) -> str:
    return _get_suggested_flaky_test_docstring(
        test_stats.n_success,
        test_stats.n_failure,
        test_stats.total_time_success or 0.0,
        test_stats.total_time_failure or 0.0,
    )


def _get_flaky_evaluation_completion_message(
    repeat_count: int, test_stats: FlakyTestStatistics
) -> str:
    suggested_docstring = _get_suggested_flaky_test_docstring_from_stats(test_stats)
    max_execution_time_minutes = FLAKY_TEST_MAX_EXECUTION_TIME_PER_TEST // 60
    timeout_message = (
        f" (achieved {test_stats.total_attempts} retry due to time limit of "
        f"{format(max_execution_time_minutes, '.2f')} minutes)"
        if repeat_count != test_stats.total_attempts
        else ""
    )
    return (
        "You ran the test with "
        f"FLAKY_TEST_EVALUATION_MODE={repeat_count}{timeout_message}\n"
        "This always fails and is expected to. Nothing wrong about this failure.\n"
        "Find below the recommended docstring and attempt count for your test:\n\n"
        f"{suggested_docstring}"
    )


def _raise_flaky_evaluation_completed(
    repeat_count: int, test_stats: FlakyTestStatistics
) -> NoReturn:
    completion_message = _get_flaky_evaluation_completion_message(repeat_count, test_stats)
    logger.info(bcolors.BOLD + bcolors.OKBLUE + completion_message + bcolors.ENDC)
    raise ValueError(completion_message)


@dataclass
class _FlakyTestEvaluationRun:
    repeat_count: int
    wait_between_tries: int
    test_stats: FlakyTestStatistics = field(
        default_factory=lambda: FlakyTestStatistics(0, 0, 0.0, 0.0)
    )
    loop_start_time: float = field(default_factory=time.time)

    def record_success(self, start_time: float) -> None:
        self.test_stats.total_time_success = (self.test_stats.total_time_success or 0.0) + (
            time.perf_counter() - start_time
        )
        self.test_stats.n_success += 1

    def record_failure(self, start_time: float) -> None:
        self.test_stats.total_time_failure = (self.test_stats.total_time_failure or 0.0) + (
            time.perf_counter() - start_time
        )
        self.test_stats.n_failure += 1

    def wait_before_next_attempt(self) -> None:
        time.sleep(self.wait_between_tries)

    def reached_time_limit(self) -> bool:
        return time.time() - self.loop_start_time > FLAKY_TEST_MAX_EXECUTION_TIME_PER_TEST

    def raise_completed(self) -> NoReturn:
        _raise_flaky_evaluation_completed(self.repeat_count, self.test_stats)


def _log_flaky_evaluation_timeout() -> None:
    logger.warning(
        "Reached maximum execution time of %s minutes",
        FLAKY_TEST_MAX_EXECUTION_TIME_PER_TEST // 60,
    )


def _log_retry_attempt_failure(
    test_name: str,
    exception_error: Exception,
    attempt_count: int,
    max_attempts: int,
    wait_between_tries: int,
) -> None:
    exception_message = exception_error.__str__().split("\n", maxsplit=1)[0]
    logger.warning(
        "Attempt [%s/%s] failed with error: %s.",
        attempt_count,
        max_attempts,
        exception_message,
    )
    logger.info(
        "Retrying %s new execution in %s second(s)",
        test_name,
        wait_between_tries,
    )


def _raise_retry_failure(
    test_func: Callable[..., Any],
    max_attempts: int,
    last_error: Optional[Exception],
    last_error_traceback: Optional[str],
) -> NoReturn:
    raise ValueError(
        render_template(
            template=FLAKY_TEST_FAILURE_ERROR_MESSAGE_TEMPLATE,
            inputs=dict(
                test_name=test_func.__name__,
                test_file=test_func.__globals__["__file__"],
                max_attempts=max_attempts,
                error_traceback=last_error_traceback,
            ),
        )
    ) from last_error


@dataclass
class _RetryTestRun:
    test_func: Callable[..., Any]
    max_attempts: int
    wait_between_tries: int
    attempt_count: int = 0
    last_error: Optional[Exception] = None
    last_error_traceback: Optional[str] = None

    @property
    def has_attempts_remaining(self) -> bool:
        return self.attempt_count < self.max_attempts

    def log_start(self) -> None:
        logger.info(
            "Starting %s attempts for test %s",
            self.max_attempts,
            self.test_func.__name__,
        )

    def record_failure(self, exception_error: Exception) -> None:
        self.attempt_count += 1
        _log_retry_attempt_failure(
            self.test_func.__name__,
            exception_error,
            self.attempt_count,
            self.max_attempts,
            self.wait_between_tries,
        )
        if self.attempt_count == self.max_attempts:
            self.last_error = exception_error
            self.last_error_traceback = "".join(traceback.format_exc())
        else:
            time.sleep(self.wait_between_tries)

    def raise_failure(self) -> NoReturn:
        _raise_retry_failure(
            self.test_func,
            self.max_attempts,
            self.last_error,
            self.last_error_traceback,
        )


def retry_test(
    max_attempts: int = 3, wait_between_tries: int = 0
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorate a test function in order to attempt to run it again when it fails. This is
    particularly useful for tests that tend to be failing a small fraction of the time due to
    involving unreliable LLMs.

    Parameters
    ----------
    max_attempts:
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

        def change_nothing_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

        return change_nothing_decorator

    if os.environ.get(FLAKY_TEST_EVALUATION_MODE, False):
        repeat_count = int(os.environ[FLAKY_TEST_EVALUATION_MODE])

        def repeat_evaluate_and_generate_docstring_decorator(
            test_func: Callable[..., Any],
        ) -> Callable[..., Any]:
            import signal
            from types import FrameType

            def _time_handler(signum: int, frame: Optional[FrameType]) -> None:
                raise TimeoutError("Max time for test execution exceeded.")

            if inspect.iscoroutinefunction(test_func):

                @wraps(test_func)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    signal.signal(signal.SIGALRM, _time_handler)
                    signal.alarm(FLAKY_TEST_MAX_EXECUTION_TIME_PER_TEST)
                    evaluation_run = _FlakyTestEvaluationRun(repeat_count, wait_between_tries)
                    for _ in range(repeat_count):
                        try:
                            start_time = time.perf_counter()
                            await test_func(*args, **kwargs)
                            evaluation_run.record_success(start_time)
                            signal.alarm(0)  # Clear alarm after successful execution
                        except TimeoutError:
                            _log_flaky_evaluation_timeout()
                            signal.alarm(0)
                            break
                        except Exception:
                            evaluation_run.record_failure(start_time)
                            signal.alarm(0)
                            evaluation_run.wait_before_next_attempt()
                        if evaluation_run.reached_time_limit():
                            break

                    evaluation_run.raise_completed()

                return async_wrapper

            @wraps(test_func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                signal.signal(signal.SIGALRM, _time_handler)
                signal.alarm(FLAKY_TEST_MAX_EXECUTION_TIME_PER_TEST)
                evaluation_run = _FlakyTestEvaluationRun(repeat_count, wait_between_tries)
                for _ in range(repeat_count):
                    try:
                        start_time = time.perf_counter()
                        test_func(*args, **kwargs)
                        evaluation_run.record_success(start_time)
                        signal.alarm(0)  # Clear alarm after successful execution
                    except TimeoutError:
                        _log_flaky_evaluation_timeout()
                        signal.alarm(0)
                        break
                    except Exception:
                        evaluation_run.record_failure(start_time)
                        signal.alarm(0)
                        evaluation_run.wait_before_next_attempt()
                    if evaluation_run.reached_time_limit():
                        break

                evaluation_run.raise_completed()

            return wrapper

        return repeat_evaluate_and_generate_docstring_decorator

    def repeat_flaky_test_decorator(test_func: Callable[..., Any]) -> Callable[..., Any]:
        _validate_retry_decorator_docstring_format(test_func)

        if inspect.iscoroutinefunction(test_func):

            @wraps(test_func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                retry_run = _RetryTestRun(test_func, max_attempts, wait_between_tries)
                retry_run.log_start()
                while retry_run.has_attempts_remaining:
                    try:
                        return await test_func(*args, **kwargs)
                    except Exception as exception_error:
                        retry_run.record_failure(exception_error)

                retry_run.raise_failure()

            return async_wrapper

        @wraps(test_func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            retry_run = _RetryTestRun(test_func, max_attempts, wait_between_tries)
            retry_run.log_start()
            while retry_run.has_attempts_remaining:
                try:
                    return test_func(*args, **kwargs)
                except Exception as exception_error:
                    retry_run.record_failure(exception_error)

            retry_run.raise_failure()

        return wrapper

    return repeat_flaky_test_decorator
