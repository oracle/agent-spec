# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import json

import pytest

from pyagentspec.llms import DbmsVectorChainLlmConfig, LlmGenerationConfig
from pyagentspec.retrypolicy import RetryPolicy
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum


def test_dbms_vector_chain_llm_config_serializes_to_database_wire_shape() -> None:
    config = DbmsVectorChainLlmConfig(
        id="database-llm",
        name="database-openai",
        model="gpt-4o",
        provider="openai",
        url="https://api.openai.com/v1/chat/completions",
        credential_name="MY_OPENAI_CREDENTIAL",
        transfer_timeout=120,
        default_generation_parameters=LlmGenerationConfig(temperature=0.3),
        retry_policy=RetryPolicy(max_attempts=3),
    )

    serialized = json.loads(AgentSpecSerializer().to_json(config))

    assert serialized["component_type"] == "DbmsVectorChainLlmConfig"
    assert serialized["model"] == "gpt-4o"
    assert "model_id" not in serialized
    assert serialized["provider"] == "openai"
    assert serialized["url"] == "https://api.openai.com/v1/chat/completions"
    assert serialized["host"] is None
    assert serialized["credential_name"] == "MY_OPENAI_CREDENTIAL"
    assert serialized["transfer_timeout"] == 120
    assert serialized["default_generation_parameters"]["temperature"] == 0.3
    assert "api_key" not in serialized
    assert "api_provider" not in serialized
    assert "api_type" not in serialized
    assert serialized["retry_policy"]["max_attempts"] == 3


def test_dbms_vector_chain_llm_config_round_trips_with_model_alias() -> None:
    config = DbmsVectorChainLlmConfig(
        id="database-llm",
        name="database-openai",
        model_id="gpt-4o",
        provider="openai",
        url="https://api.openai.com/v1/chat/completions",
        credential_name="MY_OPENAI_CREDENTIAL",
    )
    serializer = AgentSpecSerializer()

    serialized = serializer.to_yaml(config)
    deserialized = AgentSpecDeserializer().from_yaml(serialized)

    assert "model: gpt-4o" in serialized
    assert "model_id:" not in serialized
    assert deserialized == config
    assert deserialized.model_id == "gpt-4o"


def test_dbms_vector_chain_llm_config_deserializes_model_id() -> None:
    serialized = {
        "agentspec_version": AgentSpecVersionEnum.v26_2_0.value,
        "component_type": "DbmsVectorChainLlmConfig",
        "id": "database-llm",
        "name": "database-openai",
        "model_id": "gpt-4o",
        "provider": "openai",
        "url": "https://api.openai.com/v1/chat/completions",
        "credential_name": "MY_OPENAI_CREDENTIAL",
    }

    deserialized = AgentSpecDeserializer().from_dict(serialized)

    assert isinstance(deserialized, DbmsVectorChainLlmConfig)
    assert deserialized.model_id == "gpt-4o"


def test_dbms_vector_chain_llm_config_requires_v26_2() -> None:
    config = DbmsVectorChainLlmConfig(
        id="database-llm",
        name="database-openai",
        model_id="gpt-4o",
        provider="openai",
        url="https://api.openai.com/v1/chat/completions",
        credential_name="MY_OPENAI_CREDENTIAL",
    )

    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        AgentSpecSerializer().to_dict(config, agentspec_version=AgentSpecVersionEnum.v26_1_2)

    dumped = AgentSpecSerializer().to_dict(config)
    dumped["agentspec_version"] = AgentSpecVersionEnum.v26_1_2.value
    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        AgentSpecDeserializer().from_dict(dumped)
