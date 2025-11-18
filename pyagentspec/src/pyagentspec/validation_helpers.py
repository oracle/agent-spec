# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines error types and decorator for validators used in pyagentspec."""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar, Union

from pydantic import BaseModel, Field, ValidationError, model_validator
from pydantic_core import InitErrorDetails

logger = logging.getLogger(__name__)


class PyAgentSpecErrorDetails(BaseModel):
    """Describe a validation error for an Agent Spec Component."""

    type: str
    msg: str
    loc: Tuple[Union[str, int], ...] = Field(default_factory=tuple)


BaseModelSelf = TypeVar("BaseModelSelf", bound="BaseModel")


def model_validator_with_error_accumulation(
    validation_func: Callable[[BaseModelSelf], BaseModelSelf],
) -> Any:
    """
    Turn a BaseModel validation method into a model validator which accumulates errors.

    Pydantic would stop validation as soon as one model validator fails and return a single
    validation error. This decorator changes this behaviour by collecting and extending the list
    of errors in order to return all of them.

    Context: https://github.com/pydantic/pydantic/discussions/7470

    It is recommended to use this decorator for all custom validations added on all Components.
    """

    def inner_validation_func(
        cls: Type[BaseModelSelf],
        data: Dict[str, Any],
        handler: Any,
    ) -> BaseModelSelf:
        """Wrap `validation_func` and accumulate errors."""
        validation_errors: List[InitErrorDetails] = []
        validated_self: Optional[BaseModelSelf] = None
        try:
            validated_self = handler(data)
        except ValidationError as e:
            validation_errors.extend(e.errors())  # type: ignore

        self_to_validate = validated_self or validation_errors[-1].get("input")
        if isinstance(self_to_validate, cls):
            try:
                validated_self = validation_func(self_to_validate)
            except ValueError as e:
                validation_errors.append(
                    InitErrorDetails(
                        type="value_error",
                        loc=tuple(),
                        ctx={"error": e},
                        input=self_to_validate,
                    )
                )
        else:
            logger.debug(
                "Skipping validation '%s' of '%s' due to earlier unrecoverable errors",
                validation_func.__name__,
                cls.__name__,
            )

        if validation_errors:
            raise ValidationError.from_exception_data(
                title=cls.__name__,
                line_errors=validation_errors,
            )

        if validated_self is None:
            raise RuntimeError(
                "Internal error. No validation errors found, but validated component is None"
            )
        return validated_self

    return model_validator(mode="wrap")(inner_validation_func)
