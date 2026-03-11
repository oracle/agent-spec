# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Define LLM configuration abstractions and provider-specific implementations."""

from .geminiconfig import (
    GeminiAiStudioAuthConfig,
    GeminiConfig,
    GeminiVertexAiAuthConfig,
)
from .llmconfig import LlmConfig
from .llmgenerationconfig import LlmGenerationConfig
from .ocigenaiconfig import OciGenAiConfig
from .ollamaconfig import OllamaConfig
from .openaicompatibleconfig import OpenAiCompatibleConfig
from .openaiconfig import OpenAiConfig
from .vllmconfig import VllmConfig

__all__ = [
    "LlmConfig",
    "LlmGenerationConfig",
    "GeminiAiStudioAuthConfig",
    "GeminiVertexAiAuthConfig",
    "GeminiConfig",
    "VllmConfig",
    "OciGenAiConfig",
    "OllamaConfig",
    "OpenAiCompatibleConfig",
    "OpenAiConfig",
]
