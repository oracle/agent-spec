# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import ssl
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from secrets import SystemRandom
from typing import Any, Callable, Mapping, Optional

import httpx

from pyagentspec.adapters._url_validation import (
    maybe_warn_about_unrestricted_templated_url,
    validate_url_against_allow_list,
)
from pyagentspec.adapters._utils import render_nested_object_template, render_template
from pyagentspec.retrypolicy import RetryPolicy
from pyagentspec.tools.remotetool import RemoteTool as AgentSpecRemoteTool

_JITTER_RANDOM = SystemRandom()
_DEFAULT_TOTAL_ELAPSED_TIME_SECONDS = 600.0
_MAX_RETRY_AFTER_SECONDS = 30.0


def _create_remote_tool_func(remote_tool: AgentSpecRemoteTool) -> Callable[..., Any]:
    maybe_warn_about_unrestricted_templated_url(
        url=remote_tool.url,
        url_allow_list=remote_tool.url_allow_list,
        component_name=f"RemoteTool `{remote_tool.name}`",
    )

    def _remote_tool(**kwargs: Any) -> Any:
        remote_tool_data = render_nested_object_template(remote_tool.data, kwargs)
        remote_tool_headers = {
            render_template(k, kwargs): render_nested_object_template(v, kwargs)
            for k, v in remote_tool.headers.items()
        }
        remote_tool_query_params = {
            render_template(k, kwargs): render_nested_object_template(v, kwargs)
            for k, v in remote_tool.query_params.items()
        }
        remote_tool_url = render_template(remote_tool.url, kwargs)

        content_type_headers = remote_tool_headers.get("Content-Type") or remote_tool_headers.get(
            "content-type"
        )
        expect_urlencoded_form_data = (
            ("application/x-www-form-urlencoded" in content_type_headers)
            if content_type_headers is not None
            else False
        )
        data = None
        json_data = None
        content = None
        if isinstance(remote_tool_data, dict) and expect_urlencoded_form_data:
            data = remote_tool_data
        elif isinstance(remote_tool_data, (str, bytes)):
            content = remote_tool_data
        else:
            json_data = remote_tool_data

        validate_url_against_allow_list(remote_tool_url, remote_tool.url_allow_list)

        request_kwargs = {
            "method": remote_tool.http_method,
            "url": remote_tool_url,
            "params": remote_tool_query_params,
            "headers": remote_tool_headers,
            "data": data,
            "json": json_data,
            "content": content,
        }
        if (
            remote_tool.retry_policy is not None
            and remote_tool.retry_policy.request_timeout is not None
        ):
            request_kwargs["timeout"] = httpx.Timeout(remote_tool.retry_policy.request_timeout)

        response = _request_with_retry(remote_tool.retry_policy, request_kwargs)
        if remote_tool.retry_policy is not None and not response.is_success:
            response.raise_for_status()
        return response.json()

    return _remote_tool


def _request_with_retry(
    retry_policy: Optional[RetryPolicy], request_kwargs: dict[str, Any]
) -> httpx.Response:
    """Execute an HTTP request with retry-policy handling."""
    if retry_policy is None:
        return httpx.request(**request_kwargs)

    total_attempts = retry_policy.max_attempts + 1
    previous_wait_time_seconds: Optional[float] = None
    time_started = time.monotonic()

    for request_attempt_num in range(total_attempts):
        try:
            response = httpx.request(**request_kwargs)
        except httpx.TransportError as exc:
            if _is_tls_or_cert_error(exc) or request_attempt_num >= total_attempts - 1:
                raise

            wait_time_seconds = _compute_wait_before_next_attempt(
                policy=retry_policy,
                attempt_num=request_attempt_num,
                status_code=None,
                retry_after_value=None,
                previous_wait_seconds=previous_wait_time_seconds,
                time_started=time_started,
                elapsed_time_seconds_fn=time.monotonic,
                total_elapsed_time_seconds=_DEFAULT_TOTAL_ELAPSED_TIME_SECONDS,
            )
            if wait_time_seconds is None:
                raise
            previous_wait_time_seconds = wait_time_seconds
            time.sleep(wait_time_seconds)
            continue

        if response.is_success:
            return response

        response_error_text = _get_response_error_text(response)
        if request_attempt_num >= total_attempts - 1 or not _is_retryable_http_error(
            retry_policy,
            response.status_code,
            response_error_text,
        ):
            return response

        wait_time_seconds = _compute_wait_before_next_attempt(
            policy=retry_policy,
            attempt_num=request_attempt_num,
            status_code=response.status_code,
            retry_after_value=_get_retry_after_value_from_headers(response.headers),
            previous_wait_seconds=previous_wait_time_seconds,
            time_started=time_started,
            elapsed_time_seconds_fn=time.monotonic,
            total_elapsed_time_seconds=_DEFAULT_TOTAL_ELAPSED_TIME_SECONDS,
        )
        if wait_time_seconds is None:
            return response
        previous_wait_time_seconds = wait_time_seconds
        response.close()
        time.sleep(wait_time_seconds)

    raise RuntimeError("Request failed after retry attempts were exhausted.")


def _is_tls_or_cert_error(exc: BaseException) -> bool:
    """Return whether an exception chain represents TLS/certificate validation failure."""
    current: Optional[BaseException] = exc
    while current is not None:
        if isinstance(current, ssl.SSLCertVerificationError):
            return True
        message = str(current)
        if any(
            pattern in message
            for pattern in (
                "CERTIFICATE_VERIFY_FAILED",
                "certificate verify failed",
                "hostname",
                "self signed certificate",
            )
        ):
            return True
        current = current.__cause__
    return False


def _is_retryable_http_error(
    retry_policy: RetryPolicy, status_code: int, response_error_text: str
) -> bool:
    """Return whether an HTTP error response should be retried."""
    if status_code in {400, 401, 403, 422}:
        return False
    if status_code == 501:
        return False

    retry_codes = retry_policy.recoverable_statuses.get(str(status_code))
    if retry_codes is not None:
        if not retry_codes:
            return True
        lowered_response_text = response_error_text.lower()
        return any(code.lower() in lowered_response_text for code in retry_codes)

    if retry_policy.service_error_retry_on_any_5xx and 500 <= status_code < 600:
        return True
    return False


def _get_retry_after_value_from_headers(headers: Optional[Mapping[str, Any]]) -> Optional[str]:
    """Return the Retry-After header value, if present."""
    if headers is None:
        return None
    retry_after = headers.get("retry-after")
    if retry_after is None:
        return None
    return str(retry_after)


def _get_retry_after_seconds(
    retry_after_value: Optional[str],
    *,
    now: Optional[datetime] = None,
) -> Optional[float]:
    """Parse and cap a Retry-After header value."""
    if retry_after_value is None:
        return None
    try:
        return min(float(retry_after_value), _MAX_RETRY_AFTER_SECONDS)
    except ValueError:
        pass

    try:
        retry_after_datetime = parsedate_to_datetime(retry_after_value)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None

    if retry_after_datetime.tzinfo is None:
        retry_after_datetime = retry_after_datetime.replace(tzinfo=timezone.utc)

    current_datetime = now or datetime.now(timezone.utc)
    return min(
        max(0.0, (retry_after_datetime - current_datetime).total_seconds()),
        _MAX_RETRY_AFTER_SECONDS,
    )


def _compute_wait_before_next_attempt(
    *,
    policy: RetryPolicy,
    attempt_num: int,
    status_code: Optional[int],
    retry_after_value: Optional[str],
    previous_wait_seconds: Optional[float],
    time_started: float,
    elapsed_time_seconds_fn: Callable[[], float],
    total_elapsed_time_seconds: Optional[float],
) -> Optional[float]:
    """Compute the bounded delay before the next retry attempt."""
    del previous_wait_seconds

    wait_time_seconds = _get_retry_after_seconds(retry_after_value)
    if wait_time_seconds is None:
        wait_time_seconds = _compute_wait_seconds(policy, attempt_num, status_code)

    if total_elapsed_time_seconds is None:
        return wait_time_seconds

    remaining = total_elapsed_time_seconds - (elapsed_time_seconds_fn() - time_started)
    if remaining <= 0:
        return None
    return min(wait_time_seconds, remaining)


def _compute_wait_seconds(
    retry_policy: RetryPolicy, attempt_num: int, status_code: Optional[int]
) -> float:
    """Compute exponential backoff with the configured jitter strategy."""
    base = min(
        float(retry_policy.initial_retry_delay)
        * (float(retry_policy.backoff_factor) ** attempt_num),
        float(retry_policy.max_retry_delay),
    )

    jitter = retry_policy.jitter
    if jitter is None:
        return base
    if retry_policy.jitter == "equal":
        return base / 2.0 + _JITTER_RANDOM.random() * (base / 2.0)
    if jitter == "full":
        return _JITTER_RANDOM.random() * base
    if (
        jitter == "full_and_equal_for_throttle"
        and status_code is not None
        and 400 <= status_code < 500
    ):
        return base / 2.0 + _JITTER_RANDOM.random() * (base / 2.0)
    if jitter == "full_and_equal_for_throttle":
        return _JITTER_RANDOM.random() * base
    if jitter == "decorrelated":
        return min(base + _JITTER_RANDOM.random(), float(retry_policy.max_retry_delay))
    return base


def _get_response_error_text(response: httpx.Response) -> str:
    """Return a response body string suitable for retry-code matching."""
    try:
        return response.text
    except Exception:
        try:
            return response.content.decode(errors="replace")
        except Exception:
            return ""
