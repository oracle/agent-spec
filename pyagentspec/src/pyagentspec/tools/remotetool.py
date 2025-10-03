# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""This module defines the class for server tools."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import Field

from pyagentspec.templating import get_placeholder_properties_from_string
from pyagentspec.tools.tool import Tool

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
