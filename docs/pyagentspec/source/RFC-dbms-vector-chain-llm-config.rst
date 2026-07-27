:orphan:

========================================
RFC: DBMS Vector Chain LLM Configuration
========================================

Summary
-------

Add a built-in ``DbmsVectorChainLlmConfig`` component to PyAgentSpec.

The component will allow the official PyAgentSpec serializer to produce the
LLM configuration accepted by Oracle Database's ``DBMS_AI_AGENT`` executor,
without requiring users to manually edit the serialized Agent Spec or
introduce a private translation layer.

Motivation
----------

PyAgentSpec currently represents LLM configurations using ``LlmConfig`` and
provider-specific subclasses.

The generic configuration uses fields such as:

- ``component_type: LlmConfig``
- ``model_id``
- ``provider``
- ``url``
- an optional sensitive ``api_key`` reference

Oracle Database expects a different concrete configuration:

- ``component_type: DbmsVectorChainLlmConfig``
- ``model`` instead of ``model_id``
- required ``provider`` and ``url``
- ``credential_name`` referencing a database-managed credential
- optional database execution fields such as ``host`` and
  ``transfer_timeout``

Consequently, an Agent Spec produced by the official PyAgentSpec serializer
cannot currently be submitted unchanged to the Oracle Database executor.
The database rejects an unsupported or abstract LLM component before making
a provider request.

Users must currently construct or modify JSON manually, or introduce a
translation layer outside PyAgentSpec. The serialized Agent Spec therefore
differs from the object that was validated in Python.

Oracle Database manages provider secrets through database credential
objects. API-key values must not be embedded in the Agent Spec. The spec
should carry only the name of the database credential.

Proposal
--------

Add the following concrete ``LlmConfig`` subtype:

.. code-block:: python

   class DbmsVectorChainLlmConfig(LlmConfig):
       model: str
       provider: str
       url: str
       host: Optional[str] = None
       credential_name: Optional[str] = None
       transfer_timeout: Optional[int] = None

The class will be publicly available through:

.. code-block:: python

   from pyagentspec.llms import DbmsVectorChainLlmConfig

Example usage:

.. code-block:: python

   llm_config = DbmsVectorChainLlmConfig(
       name="database-openai",
       model="gpt-4o",
       provider="openai",
       url="https://api.openai.com/v1/chat/completions",
       host="public",
       credential_name="MY_OPENAI_CREDENTIAL",
       transfer_timeout=120,
   )

The serialized configuration will have this shape:

.. code-block:: json

   {
     "component_type": "DbmsVectorChainLlmConfig",
     "name": "database-openai",
     "model": "gpt-4o",
     "provider": "openai",
     "url": "https://api.openai.com/v1/chat/completions",
     "host": "public",
     "credential_name": "MY_OPENAI_CREDENTIAL",
     "transfer_timeout": 120
   }

Model field compatibility
~~~~~~~~~~~~~~~~~~~~~~~~~

The existing ``LlmConfig`` Python API and runtime adapters use
``model_id``. The new component's serialized database contract requires
``model``.

The implementation should preserve the internal ``model_id`` attribute where
possible, while accepting and serializing the field under the alias
``model``. This allows existing code that consumes an ``LlmConfig`` to
continue reading ``config.model_id``.

The official serializer must honor this field alias without changing the
serialized representation of existing components.

Credential handling
~~~~~~~~~~~~~~~~~~~

``credential_name`` identifies a credential already managed by Oracle
Database. It is not the credential value and must remain visible in the
serialized configuration.

For external providers, ``credential_name`` is required. It may be omitted
when ``host`` is ``"local"``.

The component must not serialize ``api_key`` or any API-key value. Existing
sensitive-field references are not a replacement for ``credential_name``
because they represent a different runtime resolution mechanism.

Validation
~~~~~~~~~~

The component should validate that:

- ``model``, ``provider``, and ``url`` are present and non-empty.
- ``credential_name`` is present unless ``host`` is ``"local"``.
- ``transfer_timeout``, when provided, is non-negative.
- Unsupported inherited authentication fields are not emitted.

``default_generation_parameters`` should remain available through
``LlmConfig``.

Registration
~~~~~~~~~~~~

``DbmsVectorChainLlmConfig`` should be:

- exported from ``pyagentspec.llms``;
- registered as a built-in component;
- included in generated Agent Spec schemas;
- supported by the standard serializer and deserializer.
