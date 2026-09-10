================================
How to Use AG-UI with Agent Spec
================================


`AG-UI <https://docs.ag-ui.com/>`_ is an open, event-based protocol and set of clients that connect agent backends to user interfaces for real-time, stateful, tool-aware experiences.

With the Agent Spec x AG-UI integration, you can take a portable Agent Spec configuration (JSON) and interact with it in AG-UI frontends, while keeping your choice of runtime (LangGraph, WayFlow).
The adapter bridges Agent Spec Tracing and AG-UI events so frontends receive standardized messages, tool activity, and UI state without bespoke wiring.

In this guide, you will:

- Configure an Agent Spec agent with a tool suitable for UI rendering
- Expose AG-UI endpoints with FastAPI using the Agent Spec adapter
- Run locally and connect an AG-UI client to any available runtime

.. seealso::

   See the starter template project building AI agents using Agent Spec and CopilotKit.

   https://github.com/copilotkit/with-agent-spec


.. image:: ../_static/howto/ag_ui_integration.jpg
   :align: center
   :scale: 20%
   :alt: Agent Spec enables developers to switch between runtime frameworks when using AG-UI



Prerequisites
=============

- Python 3.10 to 3.13

Install the AG-UI Agent Spec integration from source:

.. code-block:: bash

    git clone git@github.com:ag-ui-protocol/ag-ui.git
    cd ag-ui/integrations/agent-spec/python
    pip install -e .

This will install pyagentspec will the corresponding adapters for the different frameworks (LangGraph, WayFlow).


Step 1. Configure your Agent
============================

Create an agent with a tool that the UI can render and confirm.
The example includes a weather tool and enables human-in-the-loop
so the UI can request approvals before executing tools.

.. literalinclude:: ../code_examples/howto_ag_ui.py
   :language: python
   :start-after: .. start-##_Creating_the_agent
   :end-before: .. end-##_Creating_the_agent

This agent definition is exported to Agent Spec JSON and kept runtime-agnostic.
The adapter will load it for any supported runtime.


Here is what the **Agent Spec representation will look like ↓**

.. collapse:: Click here to see the assistant configuration.

   .. tabs::

      .. tab:: JSON

         .. literalinclude:: ../agentspec_config_examples/howto_ag_ui.json
            :language: json

      .. tab:: YAML

         .. literalinclude:: ../agentspec_config_examples/howto_ag_ui.yaml
            :language: yaml



Step 2: Configure a FastAPI endpoint
====================================

Expose AG-UI endpoints with the Agent Spec adapter. The example auto-detects installed runtimes and mounts one endpoint per runtime:

- ``/langgraph/backend_tool_rendering`` when ``langgraph`` is installed
- ``/wayflow/backend_tool_rendering`` when ``wayflowcore`` is installed

.. literalinclude:: ../code_examples/howto_ag_ui.py
   :language: python
   :start-after: .. start-##_Creating_the_app
   :end-before: .. end-##_Creating_the_app

Run locally with Uvicorn (development only):

.. code-block:: bash

    # If the app is in a module named "howto_ag_ui.py"
    uvicorn howto_ag_ui:app --reload --port 8000


.. important::

    This setup is intended for prototyping. Do not expose these endpoints publicly without proper authentication, rate limiting, and CORS controls.


Once the development server is running, navigate to your local AG-UI hosted website and
you should see your Agent Spec + AG-UI + CopilotKit agents up and running.


.. image:: ../_static/howto/ag_ui_screenshot.png
   :align: center
   :scale: 30%
   :alt: Agent Spec with AG-UI Screenshot


.. note::
   The adapter maps Agent Spec Tracing spans/events to AG-UI events so frontends receive standardized messages and tool activity without extra glue code.


Recap
=====

In this guide you:

- Defined an Agent Spec agent with a UI-renderable tool and HITL enabled
- Exposed AG-UI endpoints via FastAPI for all available runtimes
- Ran the server locally and prepared to connect an AG-UI client


Next steps
==========

Having learned how to connect Agent Spec agents to AG-UI, you may now proceed to:

- :doc:`Specify the Generation Configuration when Using LLMs <howto_generation_config>`
- :doc:`How to Develop an Agent with Remote Tools <howto_agent_with_remote_tools>`
- :doc:`How to Execute Agent Spec Configuration with WayFlow <howto_execute_agentspec_with_wayflow>`
- :doc:`How to Execute Agent Spec Across Frameworks <howto_execute_agentspec_across_frameworks>`
