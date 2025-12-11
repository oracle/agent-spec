=======================================
How to Use Disaggregated Configurations
=======================================

Disaggregated configurations enable you to separate out certain components or values from the main Agent Spec configuration JSON/YAML, referencing them externally rather than serializing them inline.
This pattern is commonly used to manage agent or application setups that require modularity and environment specific customization.

Disaggregated configurations improve security and maintainability by allowing sensitive or frequently changing components, such as LLM Configurations, URLs, or other runtime parameters, to be stored separately from the main configuration.
This separation makes it easier to securely manage environment specific settings, reuse shared components across multiple agents, and update or swap components without altering the core configuration, reducing duplication and risk of accidental data exposure.

This guide will show you how to:

- Create disaggregated components for agents and tools and use them effectively.
- Save your main spec and disaggregated components into separate files.
- Load the main spec with different versions of the disaggregated components.

Basic Implementation
====================

Let's demonstrate by creating a weather agent that uses a client tool to fetch weather data. This example will show how disaggregation works in a simple scenario.

.. literalinclude:: ../code_examples/howto_disaggregated_config.py
    :language: python
    :start-after: # .. start-define-components:
    :end-before: # .. end-define-components:

Serialization/Deserialization
=============================

Consider an LLM config, which often varies between development and production environments. Disaggregating this component enables you to load the appropriate version dynamically.
Similarly, client tools may be mocked during development but swapped with real ones, such as database tools, in production. Storing these separately safeguards them while ensuring they remain accessible to the relevant agents.
These are just a few examples, many other components can benefit from this modular approach.

.. literalinclude:: ../code_examples/howto_disaggregated_config.py
    :language: python
    :start-after: # .. start-export-serialization:
    :end-before: # .. end-export-serialization:

Now, in deserialization time, you can change the disaggregated components as shown:

.. literalinclude:: ../code_examples/howto_disaggregated_config.py
    :language: python
    :start-after: # .. start-export-deserialization:
    :end-before: # .. end-export-deserialization:

This approach of dynamically defining components is the preferred way for handling sensitive information, as it ensures that such data is never unnecessarily exposed or stored, maintaining a higher level of security.

Now you can run the spec using any supported framework. For more information, see :doc:`AgentSpec with Wayflow <howto_execute_agentspec_with_wayflow>` and :doc:`AgentSpec across Frameworks <howto_execute_agentspec_across_frameworks>`.

Here is what the **Agent Spec representation will look like: ↓** (first one is the main spec and second one is the disaggregated components)

.. collapse:: Click here to see the assistant configuration.

   .. tabs::

      .. tab:: JSON

         .. literalinclude:: ../agentspec_config_examples/howto_disaggregated_main_config.json
            :language: json

         .. literalinclude:: ../agentspec_config_examples/howto_disaggregated_component_config.json
            :language: json

      .. tab:: YAML

         .. literalinclude:: ../agentspec_config_examples/howto_disaggregated_main_config.yaml
            :language: yaml
        
         .. literalinclude:: ../agentspec_config_examples/howto_disaggregated_component_config.yaml
            :language: yaml

Recap
=====

In this guide, you've learned to split your agent setups into manageable, secure pieces using disaggregated configurations in Agent Spec.

.. collapse:: Below is the complete code from this guide.

    .. literalinclude:: ../code_examples/howto_disaggregated_config.py
        :language: python
        :start-after: # .. start-complete:
        :end-before: # .. end-complete:

Next Steps
==========

Now that you understand disaggregated configurations, explore more with:

- :doc:`How to Specify the Generation Configuration when Using LLMs <howto_generation_config>`
