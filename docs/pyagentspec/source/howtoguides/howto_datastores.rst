===================================
How to Use Datastores
===================================

.. admonition:: Prerequisites

    This guide assumes you are familiar with the following concepts:

    - :ref:`Properties <property>`
    - :ref:`Sensitive Fields <agentspecsensitivefield_nightly>`


Overview
========

Agent Spec supports data storage through **Datastores**, which allow you to store and retrieve data.
Datastores define schemas for collections (similar to database tables) and support different storage options:

- **Oracle Database**: Production-ready relational database with TLS and mutual-TLS support
- **PostgreSQL**: Popular open-source relational database with SSL/TLS support
- **In-Memory**: For development, testing, or when persistent storage is not needed

This guide will walk you through:

1. Defining datastore schemas using entity definitions
2. Configuring relational database datastores (Oracle and PostgreSQL)
3. Using in-memory datastores for development
4. Serializing datastores

Basic implementation
====================

1. Define the datastore schema
------------------------------

Datastores require a schema that defines the structure of data collections.
Each collection maps to an **entity** - an object with defined properties.

.. literalinclude:: ../code_examples/howto_datastores.py
    :language: python
    :start-after: .. define-schema
    :end-before: .. start-oracle-tls

API Reference: :ref:`ObjectProperty <objectproperty>`, :ref:`StringProperty <stringproperty>`

2. Configure datastores
--------------------------------------------

This section covers configuring Oracle and PostgreSQL datastores with TLS/SSL support.

Oracle Database datastores
^^^^^^^^^^^^^^^^^^^^^^^^^^

Oracle Database datastores support both TLS and mutual-TLS authentication.

TLS Connection
^^^^^^^^^^^^^^

For TLS connections, you need to provide connection details including user credentials and DSN.

.. literalinclude:: ../code_examples/howto_datastores.py
    :language: python
    :start-after: .. start-oracle-tls
    :end-before: .. end-oracle-tls

Mutual-TLS Connection
^^^^^^^^^^^^^^^^^^^^^

Mutual-TLS requires additional wallet configuration for client certificate authentication.

.. literalinclude:: ../code_examples/howto_datastores.py
    :language: python
    :start-after: .. start-oracle-mtls
    :end-before: .. end-oracle-mtls

API Reference: :ref:`OracleDatabaseDatastore <oracledatabasedatastore>`, :ref:`TlsOracleDatabaseConnectionConfig <tlsoracledatabaseconnectionconfig>`, :ref:`MTlsOracleDatabaseConnectionConfig <mtlsoracledatabaseconnectionconfig>`

PostgreSQL Database datastores
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

PostgreSQL datastores support SSL/TLS connections with various verification modes.

.. literalinclude:: ../code_examples/howto_datastores.py
    :language: python
    :start-after: .. start-postgres-tls
    :end-before: .. end-postgres-tls

API Reference: :ref:`PostgresDatabaseDatastore <postgresdatabasedatastore>`, :ref:`TlsPostgresDatabaseConnectionConfig <tlspostgresdatabaseconnectionconfig>`

SSL Mode Options
^^^^^^^^^^^^^^^^

The ``sslmode`` parameter controls SSL connection behavior:

- ``disable``: SSL is disabled
- ``allow``: SSL is attempted but not required
- ``prefer``: SSL is preferred but falls back to non-SSL if needed
- ``require``: SSL is required (default)
- ``verify-ca``: SSL is required and server certificate is verified against CA
- ``verify-full``: SSL is required and server certificate is fully verified (hostname check)

3. Use in-memory datastores
---------------------------

For development, testing, or temporary storage, use in-memory datastores.

.. literalinclude:: ../code_examples/howto_datastores.py
    :language: python
    :start-after: .. start-in-memory
    :end-before: .. end-in-memory

API Reference: :ref:`InMemoryCollectionDatastore <inmemorycollectiondatastore>`

4. Serializing datastores
-------------------------

Datastore configurations can be serialized to JSON or YAML for deployment.

.. literalinclude:: ../code_examples/howto_datastores.py
    :language: python
    :start-after: .. start-serialization
    :end-before: .. end-serialization

API Reference: :ref:`AgentSpecSerializer <serialize>`

Here is what the **Oracle Datastore configuration will look like ↓**

.. collapse:: Click here to see the Oracle datastore configuration.

   .. literalinclude:: ../agentspec_config_examples/howto_oracle_datastore.json
      :language: json

.. note::
    Notice that sensitive fields such as ``user``, ``password``, and ``dsn`` are not present in the serialized config because they are replaced with component references (e.g., ``$component_ref: oracle_tls_config_id.user``) for security reasons.

Sensitive data handling
------------------------

Database connection configurations often contain sensitive information like passwords and private keys.
Agent Spec provides SensitiveField types that mask sensitive data in exports.

.. note::
    When serializing datastores with sensitive fields, you must provide a components registry
    that maps field paths to their actual values. Sensitive fields such as ``password``, ``dsn``, ``sslkey``, ``wallet_password`` are replaced with component references (e.g., ``{"$component_ref": "component_id.field"}``) in the serialized configuration.

.. literalinclude:: ../code_examples/howto_datastores.py
    :language: python
    :start-after: .. start-deserialization
    :end-before: .. end-deserialization

See :ref:`AgentSpecDeserializer <deserialize>` for details on deserializing configurations with sensitive fields.

Recap
=====

This guide covered how to define and configure database datastores in Agent Spec.

.. collapse:: Below is the complete code from this guide.

    .. literalinclude:: ../code_examples/howto_datastores.py
        :language: python
        :linenos:
        :start-after: .. define-schema
        :end-before: .. end-serialization
