# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


import pytest

from pyagentspec.serialization.deserializer import AgentSpecDeserializer
from pyagentspec.serialization.serializer import AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum

from .conftest import parametrize_transform_and_datastore


@parametrize_transform_and_datastore
def test_can_serialize_and_deserialize_transform_with_all_datastores(
    transform_factory, datastore, sensitive_fields
):
    transform = transform_factory(datastore)

    serialized_transform = AgentSpecSerializer().to_yaml(transform)
    print(serialized_transform)
    assert len(serialized_transform.strip()) > 0

    deserialized_transform = AgentSpecDeserializer().from_yaml(
        yaml_content=serialized_transform, components_registry=sensitive_fields
    )
    assert deserialized_transform == transform

    serialized_transform = AgentSpecSerializer().to_json(transform)
    assert len(serialized_transform.strip()) > 0
    deserialized_transform = AgentSpecDeserializer().from_yaml(
        yaml_content=serialized_transform, components_registry=sensitive_fields
    )
    assert deserialized_transform == transform


@parametrize_transform_and_datastore
def test_transform_serialization_with_unsupported_version_raises(
    transform_factory, datastore, sensitive_fields
):
    transform = transform_factory(datastore)
    with pytest.raises(
        ValueError, match="Invalid agentspec_version:.*but the minimum allowed version is.*"
    ):
        _ = AgentSpecSerializer().to_json(transform, agentspec_version=AgentSpecVersionEnum.v25_4_1)
