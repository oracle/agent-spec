# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the class for builtin tools."""

from typing import Any, Dict, List, Optional, Union

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from pyagentspec.tools.tool import Tool
from pyagentspec.versioning import AgentSpecVersionEnum


class BuiltinTool(Tool):
    """A tool that is built into and executed by the orchestrator"""

    tool_type: str
    """The tool type, as defined by the orchestrator implementing the tool."""

    configuration: Optional[Dict[str, Any]] = None
    """The tool configuration, as defined by the orchestrator implementing tool."""

    executor_name: Optional[Union[str, List[str]]] = None
    """The executor providing the built-in tool."""

    tool_version: Optional[str] = None
    """The version of the tool."""

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v25_4_2, init=False, exclude=True
    )
