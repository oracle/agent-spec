# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.serialization.deserializer import AgentSpecDeserializer
from pyagentspec.serialization.serializer import AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum

from .conftest import DATASTORES_AND_THEIR_SENSITIVE_FIELDS


@pytest.mark.parametrize("datastore, sensitive_fields", DATASTORES_AND_THEIR_SENSITIVE_FIELDS)
def test_can_serialize_and_deserialize_datastore(datastore, sensitive_fields) -> None:
    serialized_ds = AgentSpecSerializer().to_yaml(datastore)
    assert len(serialized_ds.strip()) > 0
    deserialized_ds = AgentSpecDeserializer().from_yaml(
        yaml_content=serialized_ds, components_registry=sensitive_fields
    )
    assert deserialized_ds == datastore
    serialized_ds = AgentSpecSerializer().to_json(datastore)
    assert len(serialized_ds.strip()) > 0
    deserialized_ds = AgentSpecDeserializer().from_yaml(
        yaml_content=serialized_ds, components_registry=sensitive_fields
    )
    assert deserialized_ds == datastore


@pytest.mark.parametrize("datastore, sensitive_fields", DATASTORES_AND_THEIR_SENSITIVE_FIELDS)
def test_datastore_serialization_with_unsupported_version_raises(
    datastore, sensitive_fields
) -> None:
    with pytest.raises(
        ValueError, match="Invalid agentspec_version:.*but the minimum allowed version is.*"
    ):
        _ = AgentSpecSerializer().to_json(datastore, agentspec_version=AgentSpecVersionEnum.v26_1_0)


@pytest.mark.parametrize("datastore, sensitive_fields", DATASTORES_AND_THEIR_SENSITIVE_FIELDS)
def test_deserialization_with_unsupported_version_raises(datastore, sensitive_fields) -> None:
    serialized_ds = AgentSpecSerializer().to_yaml(datastore)
    assert "agentspec_version: 26.1.1" in serialized_ds
    serialized_ds = serialized_ds.replace("agentspec_version: 26.1.1", "agentspec_version: 26.1.0")

    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        _ = AgentSpecDeserializer().from_yaml(
            yaml_content=serialized_ds, components_registry=sensitive_fields
        )
