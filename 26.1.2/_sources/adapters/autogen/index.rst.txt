.. _autogenadapter:

=============================
Agent Spec Adapters - AutoGen
=============================


.. figure:: ../../_static/icons/autogen-adapter.jpg
    :align: center
    :scale: 20%
    :alt: Agent Spec adapter for AutoGen

    ↑ With the **Agent Spec adapter for AutoGen**, you can easily import agents from external frameworks using Agent Spec and run them with AutoGen.


*Microsoft AutoGen supports the development of multi-agent conversational systems,
allowing agents to communicate and collaborate to solve tasks.*


Get started
===========

To get started, set up your Python environment (Python 3.10 to 3.12 required),
and then install the PyAgentSpec package with the AutoGen extension.


.. code-block:: bash

    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install "pyagentspec[autogen]"


Usage Examples
==============

You are now ready to use the adapter to:

.. toctree::
   :maxdepth: 1

   Run Agent Spec configurations with AutoGen <spec_to_autogen>
   Convert AutoGen agents to Agent Spec <autogen_to_spec>
