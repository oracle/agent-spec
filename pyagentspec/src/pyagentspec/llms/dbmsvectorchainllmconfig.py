# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Define the LLM configuration used by Oracle Database DBMS_VECTOR_CHAIN."""

from typing import Literal, Optional

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema
from typing_extensions import Self

from pyagentspec.datastores.oracle import OracleDatabaseConnectionConfig
from pyagentspec.llms.llmconfig import LlmConfig
from pyagentspec.sensitive_field import SensitiveField
from pyagentspec.validation_helpers import model_validator_with_error_accumulation
from pyagentspec.versioning import AgentSpecVersionEnum


class DbmsVectorChainLlmConfig(LlmConfig):
    """Configure an LLM executed by Oracle Database through DBMS_VECTOR_CHAIN."""

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v26_2_0,
        init=False,
        exclude=True,
    )

    model_id: str = Field(min_length=1)
    """Model identifier used by Oracle Database for the provider request."""

    provider: str = Field(min_length=1)
    """Provider of the model, such as ``openai`` or ``cohere``."""

    url: str = Field(min_length=1)
    """Provider API endpoint used by Oracle Database."""

    host: Optional[Literal["local"]] = None
    """Set to ``local`` for a local OpenAI or Ollama provider without a database credential."""

    credential_name: Optional[str] = Field(default=None, min_length=1)
    """Name of a credential managed by Oracle Database."""

    transfer_timeout: Optional[int] = Field(default=None, ge=0)
    """Maximum transfer time in seconds for the provider request."""

    connection_config: Optional[OracleDatabaseConnectionConfig] = None
    """Optional Oracle Database connection configuration."""

    # Authentication is configured through the database credential referenced by
    # ``credential_name``.
    api_provider: SkipJsonSchema[Optional[str]] = Field(default=None, exclude=True)
    api_type: SkipJsonSchema[Optional[str]] = Field(default=None, exclude=True)
    api_key: SkipJsonSchema[SensitiveField[Optional[str]]] = Field(default=None, exclude=True)

    @model_validator_with_error_accumulation
    def _validate_credential_name(self) -> Self:
        if self.host is not None and self.credential_name is not None:
            raise ValueError("`host` and `credential_name` cannot both be specified.")
        if self.host is None and self.credential_name is None:
            raise ValueError("`credential_name` is required unless `host` is 'local'.")
        if self.host is not None and self.provider not in {"openai", "ollama"}:
            raise ValueError("`host` is supported only for the `openai` and `ollama` providers.")
        return self

    @model_validator_with_error_accumulation
    def _validate_unsupported_inherited_fields(self) -> Self:
        unsupported_fields = {
            "api_provider": self.api_provider,
            "api_type": self.api_type,
            "api_key": self.api_key,
        }
        configured_fields = [
            field_name for field_name, value in unsupported_fields.items() if value is not None
        ]
        if configured_fields:
            raise ValueError(
                "DbmsVectorChainLlmConfig does not support inherited field(s): "
                + ", ".join(configured_fields)
            )
        return self

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = super()._versioned_model_fields_to_exclude(agentspec_version)
        fields_to_exclude.update({"api_provider", "api_type", "api_key"})
        return fields_to_exclude
