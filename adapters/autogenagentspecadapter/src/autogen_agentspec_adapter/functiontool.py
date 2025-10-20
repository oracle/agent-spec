# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Callable, Optional, Sequence, Type, Union

from autogen_core.code_executor._func_with_reqs import Import
from autogen_core.tools import FunctionTool as AutogenFunctionTool
from pydantic import BaseModel


class FunctionTool(AutogenFunctionTool):
    """
    This is based on the implementation of FunctionTool from AutoGen
    (see: https://microsoft.github.io/autogen/stable/_modules/autogen_core/tools/_function_tool.html#FunctionTool).
    The main difference in our version is that we explicitly pass the args_model value to the FunctionTool.
    """

    def __init__(
        self,
        func: Callable[..., Any],
        description: str,
        args_model: Union[Type[BaseModel], None] = None,
        name: Optional[str] = None,
        global_imports: Optional[Sequence[Import]] = None,
        strict: bool = False,
    ) -> None:
        super().__init__(
            func=func,
            description=description,
            name=name,
            global_imports=global_imports or [],
            strict=strict,
        )
        # We overwrite the args if they are given
        if args_model is not None:
            self._args_type = args_model
