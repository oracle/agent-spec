# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the class for specifying LLM generation parameters."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class LlmGenerationConfig(BaseModel):
    """
    A configuration object defining LLM generation parameters.

    Parameters include number of tokens, sampling parameters, etc.
    """

    max_tokens: Optional[int] = None
    """Maximum number of token that should be generated"""
    temperature: Optional[float] = None
    """Value of the temperature parameter to be used for generation"""
    top_p: Optional[float] = None
    """Value of the top_p parameter to be used for generation"""
    # This allows arbitrary attributes to be accepted and appear in the serialization
    model_config = {"extra": "allow"}

    def model_dump(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        # By default, we exclude from the serialization all the values that are not set
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)

    def model_dump_json(self, *args: Any, **kwargs: Any) -> str:
        # By default, we exclude from the serialization all the values that are not set
        kwargs.setdefault("exclude_none", True)
        return super().model_dump_json(*args, **kwargs)
