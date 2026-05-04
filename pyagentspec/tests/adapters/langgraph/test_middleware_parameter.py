# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Dict, List
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage

from pyagentspec.adapters.langgraph import AgentSpecLoader
from pyagentspec.agent import Agent
from pyagentspec.llms import OpenAiCompatibleConfig
from pyagentspec.property import Property
from pyagentspec.tools import ClientTool


def _get_fake_model() -> Any:
    """Minimal chat model that immediately finishes, so we never hit a real LLM."""
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_openai import ChatOpenAI

    class FakeModel(FakeMessagesListChatModel, ChatOpenAI):
        pass

    return FakeModel(responses=[AIMessage(content="Done")])


def _build_agent() -> Agent:
    return Agent(
        name="agent",
        system_prompt="You are a helpful agent.",
        llm_config=OpenAiCompatibleConfig(name="llm", model_id="fake", url="null"),
        tools=[
            ClientTool(
                name="ask_user",
                description="Ask the user something",
                inputs=[Property(title="question", json_schema={"type": "string"})],
                outputs=[Property(title="answer", json_schema={})],
            )
        ],
    )


class _StopCreateAgent(Exception):
    """Raised inside the ``create_agent`` spy to short-circuit graph compilation.

    We only care about the keyword arguments ``create_agent`` receives —
    letting the real call proceed requires valid LangChain middleware
    instances, which these tests deliberately do not construct.
    """


def _spy_create_agent(captured: Dict[str, Any]):
    def spy(**kwargs: Any) -> Any:
        captured.update(kwargs)
        raise _StopCreateAgent()

    return spy


def _capture_create_agent_kwargs(loader_or_converter_factory) -> Dict[str, Any]:
    """Drive a load through ``loader_or_converter_factory()`` and capture kwargs."""
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph._langgraphconverter import (
        AgentSpecToLangGraphConverter,
    )
    from pyagentspec.adapters.langgraph._types import langchain_agents

    captured: Dict[str, Any] = {}
    agent_spec = _build_agent()
    with patch.object(
        AgentSpecToLangGraphConverter,
        "_llm_convert_to_langgraph",
        return_value=_get_fake_model(),
    ), patch.object(
        langchain_agents, "create_agent", side_effect=_spy_create_agent(captured)
    ):
        loader_or_converter = loader_or_converter_factory(MemorySaver())
        with pytest.raises(_StopCreateAgent):
            loader_or_converter.load_component(agent_spec)
    return captured


def test_default_omits_middleware_kwarg() -> None:
    """``AgentSpecLoader()`` without ``middleware`` must not pass ``middleware=``."""
    captured = _capture_create_agent_kwargs(
        lambda cp: AgentSpecLoader(checkpointer=cp)
    )
    assert "middleware" not in captured


def test_empty_list_omits_middleware_kwarg() -> None:
    """Passing an empty list is treated the same as omitting the parameter."""
    captured = _capture_create_agent_kwargs(
        lambda cp: AgentSpecLoader(checkpointer=cp, middleware=[])
    )
    assert "middleware" not in captured


def test_middleware_forwarded_in_order() -> None:
    """A non-empty list reaches ``create_agent`` in the original order."""
    a, b = object(), object()
    captured = _capture_create_agent_kwargs(
        lambda cp: AgentSpecLoader(checkpointer=cp, middleware=[a, b])
    )
    assert captured.get("middleware") == [a, b]


def test_converter_accepts_middleware_directly() -> None:
    """A list passed directly to the converter reaches ``create_agent``."""
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph._langgraphconverter import (
        AgentSpecToLangGraphConverter,
    )
    from pyagentspec.adapters.langgraph._types import langchain_agents

    captured: Dict[str, Any] = {}
    sentinel = object()
    agent_spec = _build_agent()
    with patch.object(
        AgentSpecToLangGraphConverter,
        "_llm_convert_to_langgraph",
        return_value=_get_fake_model(),
    ), patch.object(
        langchain_agents, "create_agent", side_effect=_spy_create_agent(captured)
    ):
        converter = AgentSpecToLangGraphConverter(middleware=[sentinel])
        with pytest.raises(_StopCreateAgent):
            converter.convert(
                agent_spec,
                tool_registry={},
                checkpointer=MemorySaver(),
            )
    assert captured.get("middleware") == [sentinel]


def test_middleware_list_is_copied() -> None:
    """Mutating the caller's list after construction must not leak into conversions."""
    a = object()
    caller_list: List[Any] = [a]

    def make_loader(cp: Any) -> AgentSpecLoader:
        loader = AgentSpecLoader(checkpointer=cp, middleware=caller_list)
        # Post-construction mutation must not affect the loader's behavior.
        caller_list.append(object())
        caller_list[0] = object()
        return loader

    captured = _capture_create_agent_kwargs(make_loader)
    assert captured.get("middleware") == [a]
