# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any

import pytest
from pydantic import ValidationError

from pyagentspec.datastores.oracle import TlsOracleDatabaseConnectionConfig
from pyagentspec.llms import DbmsVectorChainLlmConfig


def valid_config_kwargs() -> dict[str, Any]:
    return {
        "name": "database-openai",
        "model_id": "gpt-4o",
        "provider": "openai",
        "url": "https://api.openai.com/v1/chat/completions",
        "credential_name": "MY_OPENAI_CREDENTIAL",
    }


@pytest.mark.parametrize(
    "field_name",
    ["model_id", "provider", "url"],
)
def test_dbms_vector_chain_llm_config_rejects_empty_required_fields(field_name: str) -> None:
    kwargs = valid_config_kwargs()
    kwargs[field_name] = ""

    with pytest.raises(ValidationError, match=field_name):
        DbmsVectorChainLlmConfig(**kwargs)


def test_dbms_vector_chain_llm_config_rejects_model_alias() -> None:
    kwargs = valid_config_kwargs()
    kwargs["model"] = kwargs.pop("model_id")

    with pytest.raises(ValidationError, match="model_id"):
        DbmsVectorChainLlmConfig(**kwargs)


def test_dbms_vector_chain_llm_config_requires_credential_without_host() -> None:
    kwargs = valid_config_kwargs()
    kwargs.pop("credential_name")

    with pytest.raises(ValidationError, match="credential_name"):
        DbmsVectorChainLlmConfig(**kwargs)


@pytest.mark.parametrize("provider", ["openai", "ollama"])
def test_dbms_vector_chain_llm_config_allows_local_host_without_credential(
    provider: str,
) -> None:
    kwargs = valid_config_kwargs()
    kwargs["provider"] = provider
    kwargs["host"] = "local"
    kwargs.pop("credential_name")

    config = DbmsVectorChainLlmConfig(**kwargs)

    assert config.credential_name is None


def test_dbms_vector_chain_llm_config_rejects_host_with_credential() -> None:
    kwargs = valid_config_kwargs()
    kwargs["host"] = "local"

    with pytest.raises(ValidationError, match="host.*credential_name"):
        DbmsVectorChainLlmConfig(**kwargs)


def test_dbms_vector_chain_llm_config_rejects_nonlocal_host() -> None:
    kwargs = valid_config_kwargs()
    kwargs.pop("credential_name")
    kwargs["host"] = "public"

    with pytest.raises(ValidationError, match="host"):
        DbmsVectorChainLlmConfig(**kwargs)


def test_dbms_vector_chain_llm_config_rejects_local_host_for_unsupported_provider() -> None:
    kwargs = valid_config_kwargs()
    kwargs["provider"] = "cohere"
    kwargs["host"] = "local"
    kwargs.pop("credential_name")

    with pytest.raises(ValidationError, match="openai.*ollama"):
        DbmsVectorChainLlmConfig(**kwargs)


def test_dbms_vector_chain_llm_config_rejects_negative_transfer_timeout() -> None:
    kwargs = valid_config_kwargs()
    kwargs["transfer_timeout"] = -1

    with pytest.raises(ValidationError, match="transfer_timeout"):
        DbmsVectorChainLlmConfig(**kwargs)


def test_dbms_vector_chain_llm_config_accepts_optional_connection_config() -> None:
    kwargs = valid_config_kwargs()
    connection_config = TlsOracleDatabaseConnectionConfig(
        name="database-connection",
        user="test-user",
        password="test-password",  # nosec B106
        dsn="test-dsn",
    )
    kwargs["connection_config"] = connection_config

    config = DbmsVectorChainLlmConfig(**kwargs)

    assert config.connection_config is connection_config


@pytest.mark.parametrize(
    "field_name,value",
    [
        ("api_provider", "openai"),
        ("api_type", "chat_completions"),
        ("api_key", "not-a-real-key"),
    ],
)
def test_dbms_vector_chain_llm_config_rejects_unsupported_inherited_fields(
    field_name: str, value: Any
) -> None:
    kwargs = valid_config_kwargs()
    kwargs[field_name] = value

    with pytest.raises(ValidationError, match=field_name):
        DbmsVectorChainLlmConfig(**kwargs)
