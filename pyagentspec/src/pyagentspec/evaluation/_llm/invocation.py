# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import TYPE_CHECKING, Any, Dict, List
from urllib.parse import urlparse, urlunparse

from pyagentspec._lazy_loader import LazyLoader
from pyagentspec.llms import (
    LlmConfig,
    OciGenAiConfig,
    OpenAiCompatibleConfig,
    OpenAiConfig,
)
from pyagentspec.llms.ociclientconfig import (
    OciClientConfig,
    OciClientConfigWithApiKey,
    OciClientConfigWithSecurityToken,
)

if TYPE_CHECKING:
    # Important: do not move this import out of the TYPE_CHECKING block so long as oci and litellm are optional dependencies.
    # Otherwise, importing the modules when they are not installed would lead to an import error.
    import oci  # type: ignore
    from litellm import acompletion
    from litellm.types.utils import ModelResponse
else:
    oci = LazyLoader("oci")
    acompletion = LazyLoader("litellm").acompletion
    ModelResponse = LazyLoader("litellm.types.utils").ModelResponse


def _prepare_openai_compatible_url(url: str) -> str:
    """Normalize an OpenAI-compatible server URL.

    This ensures:
    - a scheme (defaults to http)
    - a canonical ``/v1`` base path, regardless of any existing path
    """

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    parsed = urlparse(url)
    normalized = parsed._replace(path="/v1", params="", query="", fragment="")
    return str(urlunparse(normalized))


def _get_oci_client_config(client_config: OciClientConfig) -> Dict[str, Any]:
    """Translate an OCI client configuration into ``litellm`` keyword arguments."""
    if isinstance(client_config, (OciClientConfigWithApiKey, OciClientConfigWithSecurityToken)):
        config_file = oci.config.from_file(
            client_config.auth_file_location, client_config.auth_profile
        )
        return {
            "oci_endpoint_id": client_config.service_endpoint,
            "oci_region": config_file["region"],
            "oci_signer": oci.signer.Signer(
                tenancy=config_file["tenancy"],
                user=config_file["user"],
                fingerprint=config_file["fingerprint"],
                private_key_file_location=config_file["key_file"],
                pass_phrase=config_file.get("pass_phrase"),
            ),
        }

    raise NotImplementedError(f"OciClientConfig type not supported: {type(client_config)}")


def _get_llm_config_as_litellm_dict(llm: LlmConfig) -> Dict[str, Any]:
    """Convert an ``LlmConfig`` instance into provider-specific invocation kwargs."""
    if isinstance(llm, OciGenAiConfig):
        return {
            "model": "oci/" + llm.model_id,
            "oci_compartment_id": llm.compartment_id,
            "oci_serving_mode": llm.serving_mode,
            **_get_oci_client_config(llm.client_config),
        }
    if isinstance(llm, OpenAiConfig):
        return {"model": llm.model_id}
    if isinstance(llm, OpenAiCompatibleConfig):
        return {
            "model": "openai/" + llm.model_id,
            "api_base": _prepare_openai_compatible_url(llm.url),
        }
    raise NotImplementedError(
        f"LlmConfig type not supported: {type(llm)}. Supported types are "
        "OciGenAiConfig, OpenAiConfig, and OpenAiCompatibleConfig."
    )


async def complete_conversation(
    conversation: str | List[Dict[str, str]],
    llm_config: LlmConfig,
) -> Dict[str, Any]:
    """Execute a chat completion request and surface the provider response as a dict."""
    if isinstance(conversation, str):
        messages = [{"role": "user", "content": conversation}]
    else:
        messages = conversation

    response = await acompletion(
        messages=messages,
        **_get_llm_config_as_litellm_dict(llm_config),
    )

    if not isinstance(response, ModelResponse):
        raise RuntimeError("Unexpected response from the LLM provider.")

    return response.to_dict()
