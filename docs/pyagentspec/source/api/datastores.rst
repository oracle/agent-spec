Datastores
==========

This page presents all APIs and classes related to Datastores in PyAgentSpec.

Datastore base classes
----------------------

Datastore
~~~~~~~~~

.. _datastore:
.. autoclass:: pyagentspec.datastores.Datastore
    :exclude-members: model_post_init, model_config

RelationalDatastore
~~~~~~~~~~~~~~~~~~~

.. _relationaldatastore:
.. autoclass:: pyagentspec.datastores.RelationalDatastore
    :exclude-members: model_post_init, model_config

InMemoryCollectionDatastore
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _inmemorycollectiondatastore:
.. autoclass:: pyagentspec.datastores.InMemoryCollectionDatastore
    :exclude-members: model_post_init, model_config

Oracle datastore
----------------

OracleDatabaseDatastore
~~~~~~~~~~~~~~~~~~~~~~~

.. _oracledatabasedatastore:
.. autoclass:: pyagentspec.datastores.OracleDatabaseDatastore
    :exclude-members: model_post_init, model_config

TlsOracleDatabaseConnectionConfig
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _tlsoracledatabaseconnectionconfig:
.. autoclass:: pyagentspec.datastores.TlsOracleDatabaseConnectionConfig
    :exclude-members: model_post_init, model_config

MTlsOracleDatabaseConnectionConfig
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _mtlsoracledatabaseconnectionconfig:
.. autoclass:: pyagentspec.datastores.MTlsOracleDatabaseConnectionConfig
    :exclude-members: model_post_init, model_config

PostgreSQL datastore
--------------------

PostgresDatabaseDatastore
~~~~~~~~~~~~~~~~~~~~~~~~~

.. _postgresdatabasedatastore:
.. autoclass:: pyagentspec.datastores.PostgresDatabaseDatastore
    :exclude-members: model_post_init, model_config

TlsPostgresDatabaseConnectionConfig
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _tlspostgresdatabaseconnectionconfig:
.. autoclass:: pyagentspec.datastores.TlsPostgresDatabaseConnectionConfig
    :exclude-members: model_post_init, model_config
