# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Defines the class for configuring how to connect to a OCI GenAI client."""
from typing import Literal

from pyagentspec.component import Component
from pyagentspec.sensitive_field import SensitiveField


class OciClientConfig(Component, abstract=True):
    """Base abstract class for OCI client config."""

    service_endpoint: str
    auth_type: Literal["SECURITY_TOKEN", "INSTANCE_PRINCIPAL", "RESOURCE_PRINCIPAL", "API_KEY"]


class OciClientConfigWithSecurityToken(OciClientConfig):
    """OCI client config class for authentication using SECURITY_TOKEN."""

    auth_profile: str
    auth_file_location: SensitiveField[str]
    auth_type: Literal["SECURITY_TOKEN"] = "SECURITY_TOKEN"


class OciClientConfigWithInstancePrincipal(OciClientConfig):
    """OCI client config class for authentication using INSTANCE_PRINCIPAL."""

    auth_type: Literal["INSTANCE_PRINCIPAL"] = "INSTANCE_PRINCIPAL"


class OciClientConfigWithResourcePrincipal(OciClientConfig):
    """OCI client config class for authentication using RESOURCE_PRINCIPAL."""

    auth_type: Literal["RESOURCE_PRINCIPAL"] = "RESOURCE_PRINCIPAL"


class OciClientConfigWithApiKey(OciClientConfig):
    """OCI client config class for authentication using API_KEY and a config file."""

    auth_profile: str
    auth_file_location: SensitiveField[str]
    auth_type: Literal["API_KEY"] = "API_KEY"
