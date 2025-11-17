.. _serialization:

Serialization / Deserialization
===============================

This page presents all APIs and classes related to serialization and deserialization in PyAgentSpec.

Serialization
-------------

.. _serialize:
.. autoclass:: pyagentspec.serialization.serializer.AgentSpecSerializer


Deserialization
---------------

.. _deserialize:
.. autoclass:: pyagentspec.serialization.deserializer.AgentSpecDeserializer


Serialization plugins
---------------------

.. _serializationcontext:
.. autoclass:: pyagentspec.serialization.serializationcontext.SerializationContext

.. _componentserializationplugin:
.. autoclass:: pyagentspec.serialization.serializationplugin.ComponentSerializationPlugin

.. _pydanticcomponentserializationplugin:
.. autoclass:: pyagentspec.serialization.pydanticserializationplugin.PydanticComponentSerializationPlugin


Deserialization plugins
-----------------------

.. _deserializationcontext:
.. autoclass:: pyagentspec.serialization.deserializationcontext.DeserializationContext

.. _componentdeserializationplugin:
.. autoclass:: pyagentspec.serialization.deserializationplugin.ComponentDeserializationPlugin

.. _pydanticcomponentdeserializationplugin:
.. autoclass:: pyagentspec.serialization.pydanticdeserializationplugin.PydanticComponentDeserializationPlugin
