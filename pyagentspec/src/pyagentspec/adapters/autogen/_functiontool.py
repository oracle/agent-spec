# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import inspect
from typing import Any, Callable, Optional, Sequence, Type, Union

from pydantic import BaseModel

from pyagentspec.adapters.autogen._types import (
    AutogenFunctionTool,
    AutogenImport,
)


def signature_from_pydantic_model(model_cls: type[BaseModel]) -> inspect.Signature:
    params = []
    for name, field in model_cls.model_fields.items():
        # Determine default
        if not field.is_required():
            default = field.default
        else:
            default = inspect.Parameter.empty
        # Build parameter
        param = inspect.Parameter(
            name=name,
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=field.annotation,
            default=default,
        )
        params.append(param)
    return inspect.Signature(params)


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
        global_imports: Optional[Sequence[AutogenImport]] = None,
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
            self._signature = signature_from_pydantic_model(args_model)
