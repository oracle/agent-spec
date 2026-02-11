# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os
import ssl
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from .encryption import (
    create_client_key_and_csr,
    create_root_ca,
    create_server_key_and_csr,
    issue_client_cert,
    issue_server_cert,
)
from .server_utils import (
    get_available_port,
    register_server_fixture,
    start_uvicorn_server,
    terminate_process_tree,
)

SKIP_LLM_TESTS_ENV_VAR = "SKIP_LLM_TESTS"


@pytest.fixture(autouse=True)
def _disable_openai_api_key():
    """Disable the openai api key environment variable"""
    old_value = os.environ.get("OPENAI_API_KEY", None)
    os.environ["OPENAI_API_KEY"] = "sk-fake-api-key"
    try:
        yield
    finally:
        if old_value is not None:
            os.environ["OPENAI_API_KEY"] = old_value


@pytest.fixture(scope="session")
def json_server_port() -> int:
    return get_available_port()


def should_skip_llm_test() -> bool:
    """Return True if LLM-related tests should be skipped."""
    return os.environ.get(SKIP_LLM_TESTS_ENV_VAR) == "1"


@pytest.fixture(scope="session", autouse=True)
def _seed_llm_env_for_skip():
    """
    When SKIP_LLM_TESTS=1, seed harmless dummy endpoints so imports/deserialization
    never crash on missing env vars.
    """
    if should_skip_llm_test():
        os.environ.setdefault("LLAMA_API_URL", "http://dummy-llm.local")
        os.environ.setdefault("LLAMA70BV33_API_URL", "http://dummy-llm70.local")
    yield


LLM_MOCKED_METHODS = [
    "pyagentspec.llms.vllmconfig.VllmConfig.__init__",
    "pyagentspec.llms.ocigenaiconfig.OciGenAiConfig.__init__",
    "pyagentspec.llms.openaicompatibleconfig.OpenAiCompatibleConfig.__init__",
]


@pytest.fixture(scope="session", autouse=True)
def skip_llm_construction():
    """
    When SKIP_LLM_TESTS=1, any attempt to construct an LLM config triggers a skip.
    """

    def _skip(*_args, **_kwargs):
        pytest.skip("LLM called, skipping test (SKIP_LLM_TESTS=1)")

    patches = []
    if should_skip_llm_test():
        for dotted in LLM_MOCKED_METHODS:
            p = patch(dotted, side_effect=_skip)
            p.start()
            patches.append(p)

    try:
        yield
    finally:
        for p in patches:
            p.stop()


@pytest.fixture(scope="package")
def json_server(json_server_port: int):
    api_server = Path(__file__).parent / "api_server.py"
    process, url = start_uvicorn_server(
        api_server, host="localhost", port=json_server_port, ready_timeout_s=10
    )
    try:
        yield url
    finally:
        terminate_process_tree(process, timeout=5.0)


llama_api_url = os.environ.get("LLAMA_API_URL")
if not llama_api_url:
    if should_skip_llm_test():
        llama_api_url = "http://dummy-llm.local"
    else:
        raise Exception("LLAMA_API_URL is not set in the environment")


llama70bv33_api_url = os.environ.get("LLAMA70BV33_API_URL")
if not llama70bv33_api_url:
    if should_skip_llm_test():
        llama70bv33_api_url = "http://dummy-llm70.local"
    else:
        raise Exception("LLAMA70BV33_API_URL is not set in the environment")


oss_api_url = os.environ.get("OSS_API_URL")
if not oss_api_url:
    if should_skip_llm_test():
        oss_api_url = "http://dummy-llm-oss.local"
    else:
        raise Exception("OSS_API_URL is not set in the environment")


def _replace_config_placeholders(yaml_config: str, json_server_url: str) -> str:
    return (
        yaml_config.replace("[[LLAMA_API_URL]]", llama_api_url)
        .replace("[[LLAMA70BV33_API_URL]]", llama70bv33_api_url)
        .replace("[[OSS_API_URL]]", oss_api_url)
        .replace("[[remote_tools_server]]", json_server_url)
    )


def skip_tests_if_dependency_not_installed(
    module_name: str,
    directory: Path,
    items: Any,
):
    """Skips all the tests from this directory if the given dependency is missing"""
    try:
        __import__(module_name)  # dynamically import by name
        dependency_missing = False
    except ImportError:
        dependency_missing = True

    for item in items:
        if not Path(item.fspath).is_relative_to(directory):
            continue

        if dependency_missing:
            # If the dependency is missing we run only the test to check that the right error is raised
            if item.name != f"test_import_raises_if_{module_name}_not_installed":
                item.add_marker(pytest.mark.skip(reason=f"`{module_name}` is not installed"))
        else:
            # If the dependency is installed we run all the tests except the one that checks the import error
            if item.name == f"test_import_raises_if_{module_name}_not_installed":
                item.add_marker(pytest.mark.skip(reason=f"`{module_name}` is installed"))


@pytest.fixture
def quickstart_agent_json() -> str:
    from pyagentspec.agent import Agent
    from pyagentspec.llms.openaicompatibleconfig import OpenAiCompatibleConfig
    from pyagentspec.property import FloatProperty
    from pyagentspec.serialization import AgentSpecSerializer
    from pyagentspec.tools import ServerTool

    subtraction_tool = ServerTool(
        name="subtraction-tool",
        description="subtract two numbers together",
        inputs=[FloatProperty(title="a"), FloatProperty(title="b")],
        outputs=[FloatProperty(title="difference")],
    )

    agentspec_llm_config = OpenAiCompatibleConfig(
        name="llama-3.3-70b-instruct",
        model_id="/storage/models/Llama-3.3-70B-Instruct",
        url=os.environ["LLAMA70BV33_API_URL"],
    )

    agent = Agent(
        name="agentspec_tools_test",
        description="agentspec_tools_test",
        llm_config=agentspec_llm_config,
        system_prompt="Perform subtraction with the given tool.",
        tools=[subtraction_tool],
    )

    return AgentSpecSerializer().to_json(agent)


@pytest.fixture(scope="session")
def root_ca(session_tmp_path):
    return create_root_ca(common_name="TestRootCA", days=3650, tmpdir=session_tmp_path)


@pytest.fixture(scope="session")
def ca_key(root_ca):
    return root_ca[0]


@pytest.fixture(scope="session")
def ca_cert(root_ca):
    return root_ca[1]


@pytest.fixture(scope="session")
def ca_cert_path(root_ca) -> str:
    return root_ca[2]


@pytest.fixture(scope="session")
def server_key_and_csr(session_tmp_path):
    return create_server_key_and_csr(cn="localhost", tmpdir=session_tmp_path)


@pytest.fixture(scope="session")
def server_key_path(server_key_and_csr):
    return server_key_and_csr[2]


@pytest.fixture(scope="session")
def server_csr(server_key_and_csr):
    return server_key_and_csr[1]


@pytest.fixture(scope="session")
def server_cert_path(ca_key, ca_cert, server_csr, session_tmp_path) -> str:
    return issue_server_cert(ca_key, ca_cert, server_csr, days=365, tmpdir=session_tmp_path)[1]


@pytest.fixture(scope="session")
def client_key_and_csr(session_tmp_path):
    return create_client_key_and_csr(cn="mtls-client", tmpdir=session_tmp_path)


@pytest.fixture(scope="session")
def client_key_path(client_key_and_csr):
    return client_key_and_csr[2]


@pytest.fixture(scope="session")
def client_csr(client_key_and_csr):
    return client_key_and_csr[1]


@pytest.fixture(scope="session")
def client_cert_path(ca_key, ca_cert, client_csr, session_tmp_path) -> str:
    return issue_client_cert(ca_key, ca_cert, client_csr, days=365, tmpdir=session_tmp_path)[1]


_MCP_SERVER_FIXTURE_DEPS = (
    "server_key_path",
    "server_cert_path",
    "ca_cert_path",
    "client_key_path",
    "client_cert_path",
)

_START_SERVER_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "mcp_start_server.py"
)

sse_mcp_server_http = register_server_fixture(
    name="sse_mcp_server_http",
    url_suffix="sse",
    start_kwargs=dict(
        server_file_path=_START_SERVER_FILE_PATH,
        mode="sse",
        ssl_cert_reqs=0,
    ),
    deps=(),
)

streamablehttp_mcp_server_http = register_server_fixture(
    name="streamablehttp_mcp_server_http",
    url_suffix="mcp",
    start_kwargs=dict(
        server_file_path=_START_SERVER_FILE_PATH,
        mode="streamable-http",
        ssl_cert_reqs=int(ssl.CERT_NONE),
    ),
    deps=(),
)

sse_mcp_server_https = register_server_fixture(
    name="sse_mcp_server_https",
    url_suffix="sse",
    start_kwargs=dict(
        server_file_path=_START_SERVER_FILE_PATH,
        mode="sse",
        ssl_cert_reqs=int(ssl.CERT_NONE),
    ),
    deps=_MCP_SERVER_FIXTURE_DEPS,
)

streamablehttp_mcp_server_https = register_server_fixture(
    name="streamablehttp_mcp_server_https",
    url_suffix="mcp",
    start_kwargs=dict(
        server_file_path=_START_SERVER_FILE_PATH,
        mode="streamable-http",
        ssl_cert_reqs=int(ssl.CERT_NONE),
    ),
    deps=_MCP_SERVER_FIXTURE_DEPS,
)

sse_mcp_server_mtls = register_server_fixture(
    name="sse_mcp_server_mtls",
    url_suffix="sse",
    start_kwargs=dict(
        server_file_path=_START_SERVER_FILE_PATH,
        mode="sse",
        ssl_cert_reqs=int(ssl.CERT_REQUIRED),
    ),
    deps=_MCP_SERVER_FIXTURE_DEPS,
)

streamablehttp_mcp_server_mtls = register_server_fixture(
    name="streamablehttp_mcp_server_mtls",
    url_suffix="mcp",
    start_kwargs=dict(
        server_file_path=_START_SERVER_FILE_PATH,
        mode="streamable-http",
        ssl_cert_reqs=int(ssl.CERT_REQUIRED),
    ),
    deps=_MCP_SERVER_FIXTURE_DEPS,
)
