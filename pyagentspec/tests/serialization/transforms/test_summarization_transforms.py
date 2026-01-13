# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


import pytest

from pyagentspec.datastores.datastore import InMemoryCollectionDatastore
from pyagentspec.property import ObjectProperty, StringProperty
from pyagentspec.serialization.deserializer import AgentSpecDeserializer
from pyagentspec.serialization.serializer import AgentSpecSerializer
from pyagentspec.transforms import ConversationSummarizationTransform, MessageSummarizationTransform
from pyagentspec.versioning import AgentSpecVersionEnum

from ..datastores.conftest import TESTING_MESSAGES_COLLECTION
from .conftest import create_test_llm_config, parametrize_transform_and_datastore


@parametrize_transform_and_datastore
def test_can_serialize_and_deserialize_transform_with_all_datastores(
    transform_factory, datastore, sensitive_fields
):
    transform = transform_factory(datastore)

    serialized_transform = AgentSpecSerializer().to_yaml(transform)
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
        _ = AgentSpecSerializer().to_json(transform, agentspec_version=AgentSpecVersionEnum.v26_1_0)


@parametrize_transform_and_datastore
def test_transform_deserialization_with_unsupported_version_raises(
    transform_factory, datastore, sensitive_fields
):
    transform = transform_factory(datastore)
    serialized_transform = AgentSpecSerializer().to_yaml(transform)
    assert "agentspec_version: 26.1.1" in serialized_transform
    serialized_transform = serialized_transform.replace(
        "agentspec_version: 26.1.1", "agentspec_version: 26.1.0"
    )

    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        _ = AgentSpecDeserializer().from_yaml(
            yaml_content=serialized_transform, components_registry=sensitive_fields
        )


@pytest.mark.parametrize(
    "transform",
    [
        MessageSummarizationTransform(id="test", name="test", llm=create_test_llm_config()),
        ConversationSummarizationTransform(id="test", name="test", llm=create_test_llm_config()),
    ],
)
def test_default_inmemory_datastore_created_when_not_specified(transform):
    assert transform.datastore is not None
    assert isinstance(transform.datastore, InMemoryCollectionDatastore)


@pytest.mark.parametrize(
    "transform_cls",
    [MessageSummarizationTransform, ConversationSummarizationTransform],
)
def test_transforms_with_incorrect_schema_raises(transform_cls):
    incorrect_schema = {
        TESTING_MESSAGES_COLLECTION: ObjectProperty(properties={"cache_key": StringProperty()})
    }
    datastore = InMemoryCollectionDatastore(
        name="incorrect_datastore", datastore_schema=incorrect_schema
    )
    with pytest.raises(ValueError):
        transform_cls(id="test", name="test", llm=create_test_llm_config(), datastore=datastore)
