# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
"""This module defines the base, relational and in-memory datastore component."""
from typing import Annotated, Dict

from pydantic import AfterValidator, Field
from pydantic.json_schema import SkipJsonSchema

from pyagentspec.component import Component
from pyagentspec.property import Property
from pyagentspec.versioning import AgentSpecVersionEnum


def is_object_property(value: Property) -> Property:
    schema = value.json_schema
    if schema.get("type") == "object" and "properties" in schema:
        return value
    raise ValueError(
        "Property is not a valid entity property. Entity properties must be objects with properties."
    )


Entity = Annotated[Property, AfterValidator(is_object_property)]


class Datastore(Component, abstract=True):
    """Base class for Datastores. Datastores configure how to store and retrieve data."""

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v26_1_1, init=False, exclude=True
    )


class RelationalDatastore(Datastore, abstract=True):
    """A relational data store that supports querying data using SQL-like queries.
    As a consequence, it has a fixed schema.
    """

    datastore_schema: Dict[str, Entity]
    """Mapping of collection names to entity definitions used by this datastore."""


class InMemoryCollectionDatastore(Datastore):
    """In-memory datastore for testing and development purposes."""

    datastore_schema: Dict[str, Entity]
    """Mapping of collection names to entity definitions used by this datastore."""
