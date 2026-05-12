# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import ssl
from collections.abc import Awaitable
from inspect import isawaitable
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from pyagentspec.retrypolicy import RetryPolicy
from pyagentspec.tools import RemoteTool


class _DummyResponse:
    def __init__(self, obj: Any, status_code: int = 200):
        self._obj = obj
        self._status_code = status_code
        self.headers: dict[str, str] = {}

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def is_success(self) -> bool:
        return 200 <= self._status_code < 300

    @property
    def text(self) -> str:
        return str(self._obj)

    def close(self) -> None:
        pass

    def raise_for_status(self) -> None:
        if not self.is_success:
            raise httpx.HTTPStatusError(
                f"Error response {self._status_code}",
                request=httpx.Request("GET", "https://example.com"),
                response=httpx.Response(self._status_code),
            )

    def json(self) -> Any:
        return self._obj


def _make_remote_tool_for_retry_tests(retry_policy: RetryPolicy | None) -> RemoteTool:
    return RemoteTool(
        name="retry_service",
        description="A remote service with retry policy",
        url="https://example.com/api",
        http_method="GET",
        retry_policy=retry_policy,
    )


def _get_retry_success_side_effects(case_name: str) -> list[Any]:
    request = httpx.Request("GET", "https://example.com/api")
    if case_name == "transport-error":
        return [
            httpx.ConnectError("temporary failure"),
            httpx.ConnectError("temporary failure"),
            _DummyResponse({"result": "ok"}),
        ]
    if case_name == "service-error":
        return [
            httpx.Response(503, request=request, json={"error": "busy"}),
            _DummyResponse({"result": "ok"}),
        ]
    if case_name == "status-text-code":
        return [
            httpx.Response(
                429,
                request=request,
                json={"code": "TooManyRequests", "message": "throttled"},
            ),
            _DummyResponse({"result": "ok"}),
        ]
    raise ValueError(f"Unknown retry success case: {case_name}")


class RemoteToolRetryPolicyCases:
    """Shared RemoteTool retry-policy behavior checks for adapter wrappers."""

    def invoke_remote_tool(self, remote_tool: RemoteTool) -> Any | Awaitable[Any]:
        raise NotImplementedError

    async def _invoke_remote_tool(self, remote_tool: RemoteTool) -> Any:
        result = self.invoke_remote_tool(remote_tool)
        if isawaitable(result):
            return await result
        return result

    @pytest.mark.parametrize(
        "retry_policy, expected_timeout",
        [
            pytest.param(
                RetryPolicy(max_attempts=0, request_timeout=300.0),
                300.0,
                id="retry-policy-timeout",
            ),
            pytest.param(
                RetryPolicy(max_attempts=0),
                None,
                id="retry-policy-without-timeout",
            ),
            pytest.param(None, None, id="no-retry-policy"),
        ],
    )
    @pytest.mark.anyio
    async def test_remote_tool_retry_policy_timeout_configuration(
        self, retry_policy: RetryPolicy | None, expected_timeout: float | None
    ) -> None:
        """Verify RemoteTool retry policy timeout configuration is passed only when set."""
        remote_tool = _make_remote_tool_for_retry_tests(retry_policy)

        with patch("pyagentspec.adapters._tools_common.httpx.request") as mock_request:
            mock_request.return_value = _DummyResponse({"result": "ok"})
            await self._invoke_remote_tool(remote_tool)
            _, called_kwargs = mock_request.call_args

        if expected_timeout is None:
            assert "timeout" not in called_kwargs
        else:
            assert isinstance(called_kwargs["timeout"], httpx.Timeout)
            assert called_kwargs["timeout"].read == expected_timeout

    @pytest.mark.parametrize(
        "case_name, retry_policy, expected_call_count, expected_timeout",
        [
            pytest.param(
                "transport-error",
                RetryPolicy(
                    max_attempts=2,
                    request_timeout=0.5,
                    initial_retry_delay=0,
                    max_retry_delay=0,
                ),
                3,
                0.5,
                id="transport-error",
            ),
            pytest.param(
                "service-error",
                RetryPolicy(
                    max_attempts=1,
                    initial_retry_delay=0,
                    max_retry_delay=0,
                ),
                2,
                None,
                id="default-5xx-service-error",
            ),
            pytest.param(
                "status-text-code",
                RetryPolicy(
                    max_attempts=1,
                    initial_retry_delay=0,
                    max_retry_delay=0,
                    service_error_retry_on_any_5xx=False,
                    recoverable_statuses={"429": ["TooManyRequests"]},
                ),
                2,
                None,
                id="configured-status-text-code",
            ),
        ],
    )
    @pytest.mark.anyio
    async def test_remote_tool_retry_policy_retries_then_succeeds(
        self,
        case_name: str,
        retry_policy: RetryPolicy,
        expected_call_count: int,
        expected_timeout: float | None,
    ) -> None:
        """Verify retry policy succeeds after transient transport or response failures."""
        remote_tool = _make_remote_tool_for_retry_tests(retry_policy)

        with patch("pyagentspec.adapters._tools_common.httpx.request") as mock_request:
            mock_request.side_effect = _get_retry_success_side_effects(case_name)
            assert await self._invoke_remote_tool(remote_tool) == {"result": "ok"}
            assert mock_request.call_count == expected_call_count

        if expected_timeout is not None:
            assert all(
                isinstance(call.kwargs["timeout"], httpx.Timeout)
                and call.kwargs["timeout"].read == expected_timeout
                for call in mock_request.call_args_list
            )
        else:
            assert all("timeout" not in call.kwargs for call in mock_request.call_args_list)

    @pytest.mark.anyio
    async def test_remote_tool_retry_policy_honors_retry_after_header(self) -> None:
        """Verify RemoteTool retry policy prefers bounded Retry-After delays."""
        remote_tool = _make_remote_tool_for_retry_tests(
            RetryPolicy(
                max_attempts=1,
                initial_retry_delay=0,
                max_retry_delay=0,
                recoverable_statuses={"429": []},
            )
        )

        request = httpx.Request("GET", "https://example.com/api")

        with (
            patch("pyagentspec.adapters._tools_common.httpx.request") as mock_request,
            patch("pyagentspec.adapters._tools_common.time.sleep") as mock_sleep,
        ):
            mock_request.side_effect = [
                httpx.Response(
                    429,
                    request=request,
                    headers={"retry-after": "45"},
                    json={"error": "throttled"},
                ),
                _DummyResponse({"result": "ok"}),
            ]
            assert await self._invoke_remote_tool(remote_tool) == {"result": "ok"}
            mock_sleep.assert_called_once_with(30.0)

    @pytest.mark.anyio
    async def test_remote_tool_retry_policy_raises_after_recoverable_status_retries(self) -> None:
        """Verify RemoteTool retry policy raises after recoverable responses are exhausted."""
        remote_tool = _make_remote_tool_for_retry_tests(
            RetryPolicy(
                max_attempts=1,
                initial_retry_delay=0,
                max_retry_delay=0,
            )
        )

        request = httpx.Request("GET", "https://example.com/api")

        with patch("pyagentspec.adapters._tools_common.httpx.request") as mock_request:
            mock_request.side_effect = [
                httpx.Response(503, request=request, json={"error": "busy"}),
                httpx.Response(503, request=request, json={"error": "still busy"}),
            ]
            with pytest.raises(httpx.HTTPStatusError, match="503"):
                await self._invoke_remote_tool(remote_tool)
            assert mock_request.call_count == 2

    @pytest.mark.anyio
    async def test_remote_tool_retry_policy_does_not_retry_tls_errors(self) -> None:
        """Verify RemoteTool retry policy does not retry TLS verification failures."""
        remote_tool = _make_remote_tool_for_retry_tests(
            RetryPolicy(
                max_attempts=2,
                initial_retry_delay=0,
                max_retry_delay=0,
            )
        )

        try:
            raise ssl.SSLCertVerificationError("certificate verify failed")
        except ssl.SSLCertVerificationError as cert_error:
            try:
                raise httpx.ConnectError("TLS handshake failed") from cert_error
            except httpx.ConnectError as tls_error:
                with patch("pyagentspec.adapters._tools_common.httpx.request") as mock_request:
                    mock_request.side_effect = tls_error
                    with pytest.raises(httpx.ConnectError, match="TLS handshake failed"):
                        await self._invoke_remote_tool(remote_tool)
                    assert mock_request.call_count == 1
