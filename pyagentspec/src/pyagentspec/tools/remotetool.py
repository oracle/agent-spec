# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the class for server tools."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import Field
from typing_extensions import Self

from pyagentspec.sensitive_field import SensitiveField
from pyagentspec.templating import get_placeholder_properties_from_string
from pyagentspec.tools.tool import Tool
from pyagentspec.validation_helpers import model_validator_with_error_accumulation
from pyagentspec.versioning import AgentSpecVersionEnum

if TYPE_CHECKING:
    from pyagentspec import Property


class RemoteTool(Tool):
    """A tool that is run remotely and called through REST."""

    url: str
    """The url of the API to which the call should be forwarded.
       Allows placeholders, which can define inputs"""
    http_method: str
    """The HTTP method to use for the API call (e.g., GET, POST, PUT, ...).
       Allows placeholders, which can define inputs"""
    api_spec_uri: Optional[str] = None
    """The uri of the specification of the API that is going to be called.
       Allows placeholders, which can define inputs"""
    data: Dict[str, Any] = Field(default_factory=dict)
    """The data to send as part of the body of this API call.
       Allows placeholders in dict values, which can define inputs"""
    query_params: Dict[str, Any] = Field(default_factory=dict)
    """Query parameters for the API call.
       Allows placeholders in dict values, which can define inputs"""
    headers: Dict[str, Any] = Field(default_factory=dict)
    """Additional headers for the API call.
       Allows placeholders in dict values, which can define inputs"""
    sensitive_headers: SensitiveField[Dict[str, Any]] = Field(default_factory=dict)
    """Additional headers for the API call.
       These headers are intended to be used for sensitive information such as
       authentication tokens and will be excluded form exported JSON configs."""

    def _get_inferred_inputs(self) -> List["Property"]:
        return (
            get_placeholder_properties_from_string(getattr(self, "url", ""))
            + get_placeholder_properties_from_string(getattr(self, "http_method", ""))
            + get_placeholder_properties_from_string(getattr(self, "api_spec_uri", "") or "")
            + [
                placeholder
                for data_value in getattr(self, "data", {}).values()
                if isinstance(data_value, str)
                for placeholder in get_placeholder_properties_from_string(data_value)
            ]
            + [
                placeholder
                for query_params_value in getattr(self, "query_params", {}).values()
                if isinstance(query_params_value, str)
                for placeholder in get_placeholder_properties_from_string(query_params_value)
            ]
            + [
                placeholder
                for headers_value in getattr(self, "headers", {}).values()
                if isinstance(headers_value, str)
                for placeholder in get_placeholder_properties_from_string(headers_value)
            ]
        )

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = super()._versioned_model_fields_to_exclude(agentspec_version)
        if agentspec_version < AgentSpecVersionEnum.v25_4_2:
            fields_to_exclude.add("sensitive_headers")
        return fields_to_exclude

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        if self.sensitive_headers:
            return AgentSpecVersionEnum.v25_4_2

        return super()._infer_min_agentspec_version_from_configuration()

    @model_validator_with_error_accumulation
    def _validate_sensitive_headers_are_disjoint(self) -> Self:
        repeated_headers = set(self.headers or {}).intersection(set(self.sensitive_headers or {}))
        if repeated_headers:
            raise ValueError(
                f"Found some headers have been specified in both `headers` and "
                f"`sensitive_headers`: {repeated_headers}"
            )
        return self
