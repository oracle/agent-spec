# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.llms import LlmConfig
from pyagentspec.tracing.spans.span import Span


class LlmGenerationSpan(Span):
    """
    Span that covers the whole LLM generation process

    - Starts when: the LLM generation request is received and the LLM call is performed
    - Ends when: the LLM output was generated, and it's ready to be processed
    """

    llm_config: LlmConfig
    "The LlmConfig that performs the generation"
