.. :orphan:

.. :no-search:

.. tabs::

    .. tab:: OpenAI Compatible Model

        .. code-block:: python

            from pyagentspec.llms import OpenAiCompatibleConfig

            llm_config = OpenAiCompatibleConfig(
                name="Llama 3.1 8B instruct",
                url="VLLM_URL",
                model_id="model-id",
            )

    .. tab:: DBMS Vector Chain

        .. code-block:: python

            from pyagentspec.llms import DbmsVectorChainLlmConfig

            llm_config = DbmsVectorChainLlmConfig(
                name="Database OpenAI",
                model_id="gpt-4o",
                provider="openai",
                url="https://api.openai.com/v1/chat/completions",
                credential_name="MY_OPENAI_CREDENTIAL",
            )

    .. tab:: OCI GenAI

        .. code-block:: python

            from pyagentspec.llms import OciGenAiConfig
            from pyagentspec.llms.ociclientconfig import OciClientConfigWithApiKey

            client_config = OciClientConfigWithApiKey(
                name="Oci Client Config",
                service_endpoint="https://url-to-service-endpoint.com",
                auth_profile="DEFAULT",
                auth_file_location="~/.oci/config"
            )

            llm_config = OciGenAiConfig(
                name="Oci GenAI Config",
                model_id="provider.model-id",
                compartment_id="compartment-id",
                client_config=client_config,
            )

    .. tab:: Gemini

        .. code-block:: python

            from pyagentspec.llms import GeminiConfig
            from pyagentspec.llms.geminiauthconfig import GeminiAIStudioAuthConfig

            llm_config = GeminiConfig(
                name="Gemini Flash",
                model_id="gemini-2.5-flash",
                # The runtime can read GEMINI_API_KEY from the environment.
                auth=GeminiAIStudioAuthConfig(name="gemini-aistudio-auth"),
            )

    .. tab:: vLLM

        .. code-block:: python

            from pyagentspec.llms import VllmConfig

            llm_config = VllmConfig(
                name="Llama 3.1 8B instruct",
                url="VLLM_URL",
                model_id="model-id",
            )


    .. tab:: Ollama

        .. code-block:: python

            from pyagentspec.llms import OllamaConfig

            llm_config = OllamaConfig(
                name="Ollama Config",
                model_id="model-id",
            )
