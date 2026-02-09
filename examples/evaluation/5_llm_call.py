# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import asyncio
import os

from litellm.llms.custom_httpx.async_client_cleanup import close_litellm_async_clients

from pyagentspec.evaluation._llm.invocation import complete_conversation
from pyagentspec.llms import OciGenAiConfig
from pyagentspec.llms.ociclientconfig import OciClientConfigWithApiKey

model_id = "oci/meta.llama-4-maverick-17b-128e-instruct-fp8"
COMPARTMENT_ID = os.environ["COMPARTMENT_ID"]
SERVICE_ENDPOINT = os.environ["SERVICE_ENDPOINT"]

llm_config = OciGenAiConfig(
    name="llama-config",
    model_id=model_id,
    compartment_id=COMPARTMENT_ID,
    client_config=OciClientConfigWithApiKey(
        name="llama-client-config",
        auth_file_location="~/.oci/config",
        auth_profile="DEFAULT",
        service_endpoint=SERVICE_ENDPOINT,
    ),
)


async def main() -> None:
    response = await complete_conversation(
        [
            {
                "role": "system",
                "content": "provide brief responses.",
            },
            {
                "role": "user",
                "content": "how are you doing?",
            },
        ],
        llm_config,
    )
    await close_litellm_async_clients()  # type: ignore
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
