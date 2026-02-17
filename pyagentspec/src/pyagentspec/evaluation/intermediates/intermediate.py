# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Tuple, TypeVar

from pyagentspec.evaluation._utils import _bind_kwargs_to_func, _map_names

IntermediateValueType = TypeVar("IntermediateValueType")


class Intermediate(ABC, Generic[IntermediateValueType]):
    """Base abstraction for reusable intermediate values shared across metrics.

    Intermediates compute auxiliary artefacts (for example embeddings or
    normalised text) that multiple metrics may depend on. They expose a uniform
    ``compute_value`` coroutine to materialise the result and a ``__call__``
    wrapper that handles keyword binding and input name mapping.
    """

    def __init__(
        self,
        name: str,
        input_mapping: Dict[str, str] | None = None,
    ) -> None:
        """
        Store the intermediate name and optional dataset field mapping.

        Parameters
        ----------
        name
            The name of the intermediate.

        input_mapping
            A mapping from dataset feature names (external) to the names expected by the metric.
            This allows alignment between dataset schemas and metric requirements.
            The mapping can be partial, and extra keys not required by the metric will be ignored.
            Pass ``None`` if no mapping is needed.
        """
        self.name = name
        self.input_mapping = input_mapping

    @abstractmethod
    async def compute_value(
        self, *args: Any, **kwargs: Any
    ) -> Tuple[IntermediateValueType, Dict[str, Any]]:
        """Compute the intermediate value and return it with metadata details."""
        raise NotImplementedError(
            "Method `compute_value` must be implemented for any subclass of `Intermediate`."
        )

    async def __call__(
        self, *args: Any, **kwargs: Any
    ) -> Tuple[IntermediateValueType, Dict[str, Any]]:
        """Execute ``compute_value`` after applying the configured name mapping."""
        if self.input_mapping is not None:
            kwargs = _map_names(kwargs, self.input_mapping)
        bound_args = _bind_kwargs_to_func(self.compute_value, *args, **kwargs)
        return await self.compute_value(*bound_args.args, **bound_args.kwargs)
