# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Define LLM configurations abstraction and concrete classes for connecting to vLLM or OCI."""

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
    "VllmConfig",
    "OciGenAiConfig",
    "OllamaConfig",
    "OpenAiCompatibleConfig",
    "OpenAiConfig",
]
