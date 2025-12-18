Datastores
==========

This page presents all APIs and classes related to Datastores in PyAgentSpec.

Datastore base classes
----------------------

Datastore
~~~~~~~~~

.. _datastore:
.. autoclass:: pyagentspec.datastores.datastore.Datastore
    :exclude-members: model_post_init, model_config

RelationalDatastore
~~~~~~~~~~~~~~~~~~~

.. _relationaldatastore:
.. autoclass:: pyagentspec.datastores.datastore.RelationalDatastore
    :exclude-members: model_post_init, model_config

InMemoryCollectionDatastore
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _inmemorycollectiondatastore:
.. autoclass:: pyagentspec.datastores.datastore.InMemoryCollectionDatastore
    :exclude-members: model_post_init, model_config

Oracle datastore
----------------

OracleDatabaseDatastore
~~~~~~~~~~~~~~~~~~~~~~~

.. _oracledatabasedatastore:
.. autoclass:: pyagentspec.datastores.oracle.OracleDatabaseDatastore
    :exclude-members: model_post_init, model_config

TlsOracleDatabaseConnectionConfig
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _tlsoracledatabaseconnectionconfig:
.. autoclass:: pyagentspec.datastores.oracle.TlsOracleDatabaseConnectionConfig
    :exclude-members: model_post_init, model_config

MTlsOracleDatabaseConnectionConfig
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _mtlsoracledatabaseconnectionconfig:
.. autoclass:: pyagentspec.datastores.oracle.MTlsOracleDatabaseConnectionConfig
    :exclude-members: model_post_init, model_config

PostgreSQL datastore
--------------------

PostgresDatabaseDatastore
~~~~~~~~~~~~~~~~~~~~~~~~~

.. _postgresdatabasedatastore:
.. autoclass:: pyagentspec.datastores.postgres.PostgresDatabaseDatastore
    :exclude-members: model_post_init, model_config

TlsPostgresDatabaseConnectionConfig
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _tlspostgresdatabaseconnectionconfig:
.. autoclass:: pyagentspec.datastores.postgres.TlsPostgresDatabaseConnectionConfig
    :exclude-members: model_post_init, model_config
