# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines several Agent Spec components."""

from typing import Any, ClassVar, Dict, List, Optional, Union

from pydantic import Field
from typing_extensions import Self

from pyagentspec.flows.node import Node
from pyagentspec.property import Property
from pyagentspec.sensitive_field import SensitiveField
from pyagentspec.templating import get_placeholder_properties_from_json_object
from pyagentspec.tools.remotetool import JSONSerializable
from pyagentspec.validation_helpers import model_validator_with_error_accumulation
from pyagentspec.versioning import AgentSpecVersionEnum


class ApiNode(Node):
    """
    Make an API call.

    This node is intended to be a part of a Flow.

    - **Inputs**
        Inferred from the json spec retrieved from API Spec URI, if available and reachable.
        Otherwise, users have to manually specify them.
    - **Outputs**
        Inferred from the json spec retrieved from API Spec URI, if available and reachable.
        Otherwise, users should manually specify them.

        If None is given, ``pyagentspec`` infers a generic property of any type named ``response``.
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
    data: Union[str, bytes, JSONSerializable] = Field(default_factory=lambda: {})
    """The data to send as part of the body of this API call.
       Allows placeholders in dict values, which can define inputs.

       ``data`` as `bytes` and `strings` will be passed to the request body as-is,
       whereas JSONSerializable objects are converted to string with json.dumps before being added into the request's body.

       Note: For AgentSpec version 25.4.1, this field is strictly typed as Dict[str, Any].
       For versions 25.4.2 and above, it is typed as Any."""
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

    DEFAULT_OUTPUT: ClassVar[str] = "response"
    """Default output name"""

    def _get_inferred_inputs(self) -> List[Property]:
        # Extract all the placeholders in the attributes and make them string inputs by default
        return get_placeholder_properties_from_json_object(
            [
                getattr(self, "url", ""),
                getattr(self, "http_method", ""),
                getattr(self, "api_spec_uri", ""),
                getattr(self, "data", {}),
                getattr(self, "query_params", {}),
                getattr(self, "headers", {}),
            ]
        )

    def _get_inferred_outputs(self) -> List[Property]:
        if self.outputs is not None:
            return self.outputs
        return [Property(json_schema={"title": ApiNode.DEFAULT_OUTPUT})]

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = set()
        if agentspec_version < AgentSpecVersionEnum.v25_4_2:
            fields_to_exclude.add("sensitive_headers")
        return fields_to_exclude

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        min_version = super()._infer_min_agentspec_version_from_configuration()
        if not (isinstance(self.data, dict) and all(isinstance(k, str) for k in self.data)):
            min_version = max(min_version, AgentSpecVersionEnum.v25_4_2)
        if self.sensitive_headers:
            min_version = max(min_version, AgentSpecVersionEnum.v25_4_2)
        return min_version

    @model_validator_with_error_accumulation
    def _validate_sensitive_headers_are_disjoint(self) -> Self:
        repeated_headers = set(self.headers or {}).intersection(set(self.sensitive_headers or {}))
        if repeated_headers:
            raise ValueError(
                f"Found some headers have been specified in both `headers` and "
                f"`sensitive_headers`: {repeated_headers}"
            )
        return self
