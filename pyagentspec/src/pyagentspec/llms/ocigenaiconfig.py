# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""Class to configure a connection to an OCI GenAI hosted model."""
from enum import Enum
from typing import Optional

from pydantic import SerializeAsAny

from pyagentspec.component import SerializeAsEnum
from pyagentspec.llms.llmconfig import LlmConfig
from pyagentspec.llms.ociclientconfig import OciClientConfig


class ServingMode(str, Enum):
    ON_DEMAND = "ON_DEMAND"
    DEDICATED = "DEDICATED"


class ModelProvider(str, Enum):
    """Provider of the model. It is used to ensure the requests to this model respect
    the format expected by the provider."""

    META = "META"
    GROK = "GROK"
    COHERE = "COHERE"
    OTHER = "OTHER"


class OciGenAiConfig(LlmConfig):
    """
    Class to configure a connection to a OCI GenAI hosted model.

    Requires to specify the model id and the client configuration to the OCI GenAI service.
    """

    model_id: str
    """The identifier of the model to use."""
    compartment_id: str
    """The OCI compartment ID where the model is hosted."""
    serving_mode: SerializeAsEnum[ServingMode] = ServingMode.ON_DEMAND
    """The serving mode for the model."""
    provider: Optional[SerializeAsEnum[ModelProvider]] = None
    """The provider of the model. If None, it will be automatically detected by the runtime using the model ID"""
    client_config: SerializeAsAny[OciClientConfig]
    """The client configuration for connecting to OCI GenAI service."""
