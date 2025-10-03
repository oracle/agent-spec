# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""This module defines several Agent Spec components."""

from typing import Any, ClassVar, Dict, List, Optional

from pydantic import Field

from pyagentspec.flows.node import Node
from pyagentspec.property import Property
from pyagentspec.templating import get_placeholder_properties_from_string


class ApiNode(Node):
    """
    Make an API call.

    This node is intended to be a part of a Flow.

    - **Inputs**
        Inferred from the json spec retrieved from API Spec URI, if available and reachable.
        Otherwise, users have to manually specify them.
    - **Outputs**
        Inferred from the json spec retrieved from API Spec URI, if available and reachable.
        Otherwise, users have to manually specify them.
    - **Branches**
        One, the default next.


    Examples
    --------
    >>> from pyagentspec.flows.nodes import ApiNode
    >>> from pyagentspec.property import Property
    >>> weather_result_property = Property(
    ...     json_schema={
    ...         "title": "zurich_weather",
    ...         "type": "object",
    ...         "properties": {
    ...             "temperature": {
    ...                 "type": "number",
    ...                 "description": "Temperature in celsius degrees",
    ...             },
    ...             "weather": {"type": "string"}
    ...         },
    ...     }
    ... )
    >>> call_current_weather_step = ApiNode(
    ...     name="Weather API call node",
    ...     url="https://example.com/weather",
    ...     http_method = "GET",
    ...     query_params={
    ...         "location": "zurich",
    ...     },
    ...     outputs=[weather_result_property]
    ... )
    >>>
    >>> item_id_property = Property(
    ...     json_schema={"title": "item_id", "type": "string"}
    ... )
    >>> order_id_property = Property(
    ...     json_schema={"title": "order_id", "type": "string"}
    ... )
    >>> store_id_property = Property(
    ...     json_schema={"title": "store_id", "type": "string"}
    ... )
    >>> session_id_property = Property(
    ...     json_schema={"title": "session_id", "type": "string"}
    ... )
    >>> create_order_step = ApiNode(
    ...     name="Orders api call node",
    ...     url="https://example.com/orders/{{ order_id }}",
    ...     http_method="POST",
    ...     # sending an object which will automatically be transformed into JSON
    ...     data={
    ...         # define a static body parameter
    ...         "topic_id": 12345,
    ...         # define a templated body parameter.
    ...         # The value for {{ item_id }} will be taken from the IO system at runtime
    ...         "item_id": "{{ item_id }}",
    ...     },
    ...     query_params={
    ...         # provide one templated query parameter called "store_id"
    ...         # which will take its value from the IO system from key "store_id"
    ...         "store_id": "{{ store_id }}",
    ...     },
    ...     headers={
    ...         # set header session_id. the value is coming from the IO system
    ...         "session_id": "{{ session_id }}",
    ...     },
    ...     inputs=[item_id_property, order_id_property, store_id_property, session_id_property],
    ... )

    """

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

    DEFAULT_OUTPUT: ClassVar[str] = "response"
    """str: Input key for the name to transition to next."""

    def _get_inferred_inputs(self) -> List[Property]:
        # Extract all the placeholders in the attributes and make them string inputs by default
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

    def _get_inferred_outputs(self) -> List[Property]:
        output_title = self.outputs[0].title if self.outputs else ApiNode.DEFAULT_OUTPUT
        return [Property(json_schema={"title": output_title})]
