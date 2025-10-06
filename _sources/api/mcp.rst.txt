Model Context Protocol (MCP)
============================

This page presents all APIs and classes related to Model Context Protocol (MCP).


Client Transports
-----------------

.. _sessionparameters:
.. autoclass:: pyagentspec.mcp.clienttransport.SessionParameters
    :exclude-members: model_post_init, model_config

.. _stdiotransport:
.. autoclass:: pyagentspec.mcp.clienttransport.StdioTransport
    :exclude-members: model_post_init, model_config

.. _ssetransport:
.. autoclass:: pyagentspec.mcp.clienttransport.SSETransport
    :exclude-members: model_post_init, model_config

.. _ssemtlstransport:
.. autoclass:: pyagentspec.mcp.clienttransport.SSEmTLSTransport
    :exclude-members: model_post_init, model_config

.. _streamablehttptransport:
.. autoclass:: pyagentspec.mcp.clienttransport.StreamableHTTPTransport
    :exclude-members: model_post_init, model_config

.. _streamablehttpmtlstransport:
.. autoclass:: pyagentspec.mcp.clienttransport.StreamableHTTPmTLSTransport
    :exclude-members: model_post_init, model_config


Tools
-----

See :ref:`MCP Tool <mcptool>`
