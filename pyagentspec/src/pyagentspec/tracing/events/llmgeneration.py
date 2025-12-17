# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import List, Optional

from pydantic import BaseModel

from pyagentspec.llms import LlmConfig, LlmGenerationConfig
from pyagentspec.sensitive_field import SensitiveField
from pyagentspec.tools import Tool
from pyagentspec.tracing.events.event import Event
from pyagentspec.tracing.messages.message import Message


class ToolCall(BaseModel):
    """Model for an LLM tool call."""

    call_id: str
    "Identifier of the tool call"

    tool_name: str
    "The name of the tool that should be called"

    arguments: str
    "The values of the arguments that should be passed to the tool, in JSON format"


class LlmGenerationRequest(Event):
    """An LLM generation request was received. Start of the LlmGenerationSpan."""

    llm_config: LlmConfig
    "The LlmConfig that performs the generation"

    prompt: SensitiveField[List[Message]]
    "The content of the prompt that will be sent to the LLM."

    tools: List[Tool]
    "The list of tools sent as part of the generation request"

    request_id: str
    "Identifier of the generation request"

    llm_generation_config: Optional[LlmGenerationConfig] = None
    "The LLM configuration used for this LLM call"


class LlmGenerationResponse(Event):
    """An LLM response was received. End of an LlmGenerationSpan."""

    llm_config: LlmConfig
    "The LlmConfig that performed the generation"

    content: SensitiveField[Optional[str]]
    "The content of the response received from the LLM"

    tool_calls: SensitiveField[List[ToolCall]] = []
    "The list of tool calls that should be performed, received as part of the generation response"

    request_id: str
    "Identifier of the generation request"

    completion_id: Optional[str] = None
    "The identifier of the completion related to this response"

    input_tokens: Optional[int] = None
    "Number of input tokens"

    output_tokens: Optional[int] = None
    "Number of output tokens"


class LlmGenerationChunkReceived(Event):

    llm_config: LlmConfig
    "The LlmConfig that performs the generation"

    content: SensitiveField[Optional[str]]
    "The content of the chunk received from the LLM"

    request_id: str
    "Identifier of the generation request"

    tool_calls: SensitiveField[List[ToolCall]] = []
    "The list of tool calls that should be performed, received as part of the generation response chunk"

    completion_id: Optional[str] = None
    "The identifier of the completion related to this response chunk"

    output_tokens: Optional[int] = None
    "Number of output tokens for this chunk"
