# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
"""LlmNode structured outputs through the LangGraph adapter (oracle/agent-spec#232).

LangChain / adapter modules are imported inside the tests so this module collects
in environments without the ``langgraph`` extra, like the other adapter tests.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyagentspec.flows.nodes import LlmNode
from pyagentspec.llms import LlmConfig
from pyagentspec.property import Property

NESTED_OUTPUT = Property(
    json_schema={
        "title": "result",
        "type": "object",
        "required": ["name", "profile"],
        "properties": {
            "name": {"type": "string"},
            "profile": {
                "type": "object",
                "required": ["score", "active", "tags"],
                "properties": {
                    "score": {"type": "number"},
                    "active": {"type": "boolean"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    }
)


def _structured_node() -> LlmNode:
    return LlmNode(
        name="structured_llm_node",
        prompt_template="Describe {{topic}}",
        llm_config=LlmConfig(name="test-llm", model_id="gpt-4o", api_provider="openai"),
        outputs=[NESTED_OUTPUT],
    )


def _legacy_provider_chat_model() -> Any:
    """Chat model behaving like langchain-oci<0.3.0: dict schemas are rejected."""
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult

    class _LegacyProviderChatModel(BaseChatModel):
        def _generate(
            self, messages: Any, stop: Any = None, run_manager: Any = None, **kwargs: Any
        ) -> ChatResult:
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=""))])

        @property
        def _llm_type(self) -> str:
            return "legacy-test-model"

        def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
            raise ValueError(
                f"Unsupported tool type {type(schema)}. Tool must be passed in as a BaseTool "
                "instance, TypedDict class, or BaseModel type."
            )

    return _LegacyProviderChatModel()


def test_provider_rejecting_dict_schema_gives_actionable_error() -> None:
    from pyagentspec.adapters.langgraph._node_execution import LlmNodeExecutor

    with pytest.raises(ValueError) as excinfo:
        LlmNodeExecutor(_structured_node(), _legacy_provider_chat_model())

    message = str(excinfo.value)
    assert "structured_llm_node" in message
    assert "_LegacyProviderChatModel" in message
    assert "langchain-oci>=0.3.0" in message
    assert "single string output" in message
    assert isinstance(excinfo.value.__cause__, ValueError)
    assert "Unsupported tool type" in str(excinfo.value.__cause__)


def test_oci_genai_accepts_nested_json_schema_output(monkeypatch: pytest.MonkeyPatch) -> None:
    import platform

    from langchain_core.messages import HumanMessage

    from pyagentspec.adapters.langgraph._node_execution import LlmNodeExecutor

    # Importing the OCI SDK evaluates platform.platform() for its user agent,
    # which reads OS files outside the test sandbox's allowlist on some hosts.
    monkeypatch.setattr(platform, "platform", lambda *args, **kwargs: "test-platform")
    monkeypatch.setattr(platform, "mac_ver", lambda *args, **kwargs: ("", ("", "", ""), ""))
    langchain_oci = pytest.importorskip("langchain_oci")

    llm = langchain_oci.ChatOCIGenAI(model_id="meta.llama-3.3-70b-instruct", client=MagicMock())
    executor = LlmNodeExecutor(_structured_node(), llm)

    assert executor.requires_structured_generation is True
    assert executor.structured_llm is not None

    # The structured runnable binds one function whose parameters carry the
    # nested Agent Spec schema; build the OCI request without any network call.
    bound = executor.structured_llm.first
    request = bound.bound._prepare_request(
        [HumanMessage(content="hi")], stop=None, stream=False, **bound.kwargs
    )
    (tool,) = request.chat_request.tools
    assert tool.name == "structured_output"
    profile = tool.parameters["properties"]["result"]["properties"]["profile"]
    assert set(profile["required"]) == {"score", "active", "tags"}


def test_langchain_oci_version_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.metadata as metadata

    from pyagentspec.adapters.langgraph import _langgraphconverter

    def old_version(name: str) -> str:
        assert name == "langchain-oci"
        return "0.2.7"

    monkeypatch.setattr(metadata, "version", old_version)
    with pytest.raises(ImportError, match=r"langchain-oci>=0\.3\.0 \(found 0\.2\.7\)"):
        _langgraphconverter._check_langchain_oci_version()

    monkeypatch.setattr(metadata, "version", lambda name: "0.3.2")
    _langgraphconverter._check_langchain_oci_version()  # no error

    monkeypatch.setattr(metadata, "version", lambda name: "1.0.0rc1")
    _langgraphconverter._check_langchain_oci_version()  # pre-release tokens tolerated
