# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os
from pathlib import Path

import oci
import pytest
from langchain_oci import ChatOCIGenAI

from pyagentspec.adapters.langgraph._langgraphconverter import (
    AgentSpecToLangGraphConverter,
)
from pyagentspec.llms.ociclientconfig import (
    OciClientConfigWithApiKey,
    OciClientConfigWithInstancePrincipal,
    OciClientConfigWithSecurityToken,
)
from pyagentspec.llms.ocigenaiconfig import OciGenAiConfig

OCI_INSTANCE_PRINCIPAL_ENDPOINT_BASE_URL = os.getenv("INSTANCE_PRINCIPAL_ENDPOINT_BASE_URL")
if not OCI_INSTANCE_PRINCIPAL_ENDPOINT_BASE_URL:
    raise Exception("INSTANCE_PRINCIPAL_ENDPOINT_BASE_URL is not set in the environment")

OCI_COMPARTMENT_ID = os.getenv("COMPARTMENT_ID")
if not OCI_COMPARTMENT_ID:
    raise Exception("compartment_id is not set in the environment")

OCI_SERVICE_ENDPOINT = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"


def should_skip_ocigenai_tests():
    return not ("OCI_GENAI_API_KEY_CONFIG" in os.environ and "OCI_GENAI_API_KEY_PEM" in os.environ)


def _oci_user_config_path() -> str:
    return str(Path("~/.oci/config").expanduser())


def auth_profile_contains_security_token(client_config):
    try:
        oci_config = oci.config.from_file(
            file_location=client_config.auth_file_location,
            profile_name=client_config.auth_profile,
        )
        return oci_config.get("security_token_file")
    except Exception:
        # If the config/profile is missing or unreadable, treat as no token
        return False


# Evaluate once at import-time for skip decorator
_SEC_TOKEN_PRESENT = auth_profile_contains_security_token(
    OciClientConfigWithSecurityToken(
        name="with_security_token",
        service_endpoint=OCI_SERVICE_ENDPOINT,
        auth_profile="DEFAULT",
        auth_file_location=_oci_user_config_path(),
    )
)


@pytest.mark.skipif(should_skip_ocigenai_tests(), reason="OCI config not available")
def test_ocigenai_llm_conversion_api_key(default_generation_parameters):
    client_config = OciClientConfigWithApiKey(
        name="with_api_key",
        service_endpoint=OCI_SERVICE_ENDPOINT,
        auth_profile="DEFAULT",
        auth_file_location=_oci_user_config_path(),
    )
    llm_cfg = OciGenAiConfig(
        name="oci",
        model_id="openai.gpt-5",
        compartment_id=OCI_COMPARTMENT_ID,
        default_generation_parameters=default_generation_parameters,
        client_config=client_config,
    )

    model = AgentSpecToLangGraphConverter()._llm_convert_to_langgraph(llm_cfg)
    assert isinstance(model, ChatOCIGenAI)
    assert model.model_id == llm_cfg.model_id
    assert model.model_kwargs["temperature"] == default_generation_parameters.temperature
    assert model.model_kwargs["max_completion_tokens"] == default_generation_parameters.max_tokens
    assert model.model_kwargs["top_p"] == default_generation_parameters.top_p
    # gpt-5 does not support temperature and top_p
    del model.model_kwargs["temperature"]
    del model.model_kwargs["top_p"]
    resp = model.invoke("Explain LangChain in 5 words")
    # empty string if max_tokens is too low, and the model did not yet generate answer tokens, as it only generated reasoning tokens
    assert resp.content or resp.content == ""


@pytest.mark.skipif(
    should_skip_ocigenai_tests() or not _SEC_TOKEN_PRESENT,
    reason="OCI config not available or `DEFAULT` auth profile lacks security token; skipping.",
)
def test_ocigenai_llm_conversion_security_token(default_generation_parameters):
    client_config = OciClientConfigWithSecurityToken(
        name="with_security_token",
        service_endpoint=OCI_SERVICE_ENDPOINT,
        auth_profile="DEFAULT",
        auth_file_location=_oci_user_config_path(),
    )
    llm_cfg = OciGenAiConfig(
        name="oci",
        model_id="openai.gpt-4.1",
        compartment_id=OCI_COMPARTMENT_ID,
        default_generation_parameters=default_generation_parameters,
        client_config=client_config,
    )
    model = AgentSpecToLangGraphConverter()._llm_convert_to_langgraph(llm_cfg)
    assert isinstance(model, ChatOCIGenAI)
    assert model.model_id == llm_cfg.model_id
    assert model.model_kwargs["temperature"] == default_generation_parameters.temperature
    assert model.model_kwargs["max_completion_tokens"] == default_generation_parameters.max_tokens
    assert model.model_kwargs["top_p"] == default_generation_parameters.top_p
    try:
        resp = model.invoke("Explain LangChain in 5 words")
        assert resp.content or resp.content == ""
    except oci.exceptions.ServiceError as e:
        # the token expired, need to re-authenticate
        assert (
            "The required information to complete authentication was not provided or was incorrect."
            in str(e)
        )


def test_ocigenai_llm_conversion_instance_principal(default_generation_parameters, monkeypatch):
    # no type hints for monkeypatch https://github.com/pytest-dev/pytest/issues/2712
    model_id = "meta.llama-3.3-70b-instruct"
    for proxy_var_name in ["HTTP_PROXY", "http_proxy"]:
        # Do not raise if var is absent to keep test robust across envs
        monkeypatch.delenv(proxy_var_name, raising=False)
    client_config = OciClientConfigWithInstancePrincipal(
        name="with_instance_prinpical",
        service_endpoint=f"{OCI_INSTANCE_PRINCIPAL_ENDPOINT_BASE_URL}/llama",
    )
    llm_cfg = OciGenAiConfig(
        name="oci",
        model_id=model_id,
        compartment_id=OCI_COMPARTMENT_ID,
        default_generation_parameters=default_generation_parameters,
        client_config=client_config,
    )
    model = AgentSpecToLangGraphConverter()._llm_convert_to_langgraph(llm_cfg, {})
    assert isinstance(model, ChatOCIGenAI)
    assert model.model_id == model_id
    assert model.model_kwargs["max_tokens"] == default_generation_parameters.max_tokens
    # this test passes in an instance principal machine, in which the `ChatOCIGenAI` object can be invoked


@pytest.mark.filterwarnings(
    "ignore:`config_type` is deprecated and will be removed:DeprecationWarning"
)
def test_reverse_convert_chatocigenai_to_agentspec(monkeypatch):
    try:
        import langchain_oci as lc_oci  # type: ignore
    except Exception:
        pytest.skip("langchain_oci not installed")

    # Replace ChatOCIGenAI with a ChatOpenAI subclass to satisfy Runnable interface
    from langchain_openai import ChatOpenAI
    from pydantic import SecretStr

    class FakeOCIChat(ChatOpenAI):
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            # Initialize minimal ChatOpenAI
            super().__init__(
                model="gpt-4o-mini", base_url="http://dummy/v1", api_key=SecretStr("t")
            )
            # Attach OCI-specific fields consumed by the converter
            object.__setattr__(self, "model_id", kwargs.get("model_id", ""))
            object.__setattr__(self, "compartment_id", kwargs.get("compartment_id", ""))
            object.__setattr__(self, "service_endpoint", kwargs.get("service_endpoint", ""))
            object.__setattr__(self, "auth_type", kwargs.get("auth_type", "API_KEY"))
            object.__setattr__(self, "auth_profile", kwargs.get("auth_profile", "DEFAULT"))
            object.__setattr__(self, "auth_file_location", kwargs.get("auth_file_location", ""))
            object.__setattr__(self, "provider", kwargs.get("provider", None))
            object.__setattr__(self, "model_kwargs", kwargs.get("model_kwargs", {}))

    monkeypatch.setattr(lc_oci, "ChatOCIGenAI", FakeOCIChat, raising=True)

    from langgraph.prebuilt import create_react_agent

    from pyagentspec.adapters.langgraph import AgentSpecExporter
    from pyagentspec.agent import Agent
    from pyagentspec.llms.ociclientconfig import (
        OciClientConfigWithApiKey,
        OciClientConfigWithInstancePrincipal,
        OciClientConfigWithResourcePrincipal,
        OciClientConfigWithSecurityToken,
    )
    from pyagentspec.llms.ocigenaiconfig import OciGenAiConfig

    model = lc_oci.ChatOCIGenAI(
        model_id="openai.gpt-any",
        compartment_id="ocid1.compartment.oc1..dummy",
        service_endpoint="https://example.com",
        auth_type="API_KEY",
        auth_profile="DEFAULT",
        auth_file_location="~/.oci/config",
    )
    cg = create_react_agent(model, tools=[], prompt="You are helpful.", name="OCI Agent")

    component = AgentSpecExporter().to_component(cg)

    assert isinstance(component, Agent)
    assert isinstance(component.llm_config, OciGenAiConfig)
    assert component.llm_config.model_id == "openai.gpt-any"
    assert component.llm_config.compartment_id == "ocid1.compartment.oc1..dummy"
    client_cfg = component.llm_config.client_config
    assert isinstance(
        client_cfg,
        (
            OciClientConfigWithApiKey,
            OciClientConfigWithSecurityToken,
            OciClientConfigWithInstancePrincipal,
            OciClientConfigWithResourcePrincipal,
        ),
    )


@pytest.mark.skipif(should_skip_ocigenai_tests(), reason="OCI config not available")
@pytest.mark.filterwarnings(
    "ignore:`config_type` is deprecated and will be removed:DeprecationWarning"
)
def test_reverse_convert_chatocigenai_to_agentspec_real():
    """Integration-ish test for reverse conversion using the real client.

    This does not invoke the model; it only constructs the agent graph and converts it.
    It requires valid OCI auth on the machine to instantiate ChatOCIGenAI.
    """
    from langchain_oci import ChatOCIGenAI  # type: ignore
    from langgraph.prebuilt import create_react_agent

    from pyagentspec.adapters.langgraph import AgentSpecExporter
    from pyagentspec.agent import Agent
    from pyagentspec.llms.ociclientconfig import (
        OciClientConfigWithApiKey,
        OciClientConfigWithInstancePrincipal,
        OciClientConfigWithResourcePrincipal,
        OciClientConfigWithSecurityToken,
    )
    from pyagentspec.llms.ocigenaiconfig import OciGenAiConfig

    model = ChatOCIGenAI(
        model_id="openai.gpt-5",
        compartment_id=OCI_COMPARTMENT_ID,
        service_endpoint=OCI_SERVICE_ENDPOINT,
        auth_type="API_KEY",
        auth_profile="DEFAULT",
        auth_file_location=_oci_user_config_path(),
    )
    cg = create_react_agent(model, tools=[], prompt="You are helpful.", name="OCI Agent")

    component = AgentSpecExporter().to_component(cg)
    assert isinstance(component, Agent)
    assert isinstance(component.llm_config, OciGenAiConfig)
    assert component.llm_config.model_id == "openai.gpt-5"
    assert component.llm_config.compartment_id == OCI_COMPARTMENT_ID
    client_cfg = component.llm_config.client_config
    assert isinstance(
        client_cfg,
        (
            OciClientConfigWithApiKey,
            OciClientConfigWithSecurityToken,
            OciClientConfigWithInstancePrincipal,
            OciClientConfigWithResourcePrincipal,
        ),
    )
