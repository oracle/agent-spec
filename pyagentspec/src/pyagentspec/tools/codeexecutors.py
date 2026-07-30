# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (https://oss.oracle.com/licenses/upl), at your option.

"""Code execution backend configuration components."""

from typing import Dict, Optional

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from pyagentspec.component import Component
from pyagentspec.retrypolicy import RetryPolicy
from pyagentspec.sensitive_field import SensitiveField
from pyagentspec.versioning import AgentSpecVersionEnum

__all__ = [
    "CodeExecutor",
    "SubProcessCodeExecutor",
    "LocalContainerCodeExecutor",
    "EndpointCodeExecutor",
]


class CodeExecutor(Component, abstract=True):
    """Base component for code execution backends."""

    timeout_seconds: float = Field(default=30.0, gt=0)
    """Maximum wall-clock seconds allowed for one execution."""

    max_code_chars: int = Field(default=50_000, gt=0)
    """Maximum accepted source length in characters."""

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v26_3_0,
        init=False,
        exclude=True,
    )


class SubProcessCodeExecutor(CodeExecutor):
    """Code executor that declares local process execution.

    Note: The subprocess executor is intended for prototyping only and must
    not be used in production deployments.
    """


class LocalContainerCodeExecutor(CodeExecutor):
    """Code executor that declares local container execution."""

    image: str
    """Local container image used by the runtime for code execution."""


class EndpointCodeExecutor(CodeExecutor):
    """Code executor that sends execution requests to an endpoint."""

    url: str
    """Code execution endpoint URL."""

    headers: Optional[Dict[str, str]] = None
    """Non-sensitive headers sent to the endpoint."""

    sensitive_headers: SensitiveField[Optional[Dict[str, str]]] = None
    """Sensitive headers sent to the endpoint."""

    retry_policy: Optional[RetryPolicy] = None
    """Optional retry configuration for requests sent to the endpoint."""
