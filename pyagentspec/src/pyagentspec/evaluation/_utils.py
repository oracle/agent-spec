# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Utility helpers shared by evaluation primitives.

The utilities collected here focus on argument binding, exception chaining, and name
mapping. They are intentionally kept lightweight so they can be safely reused across
datasets, metrics, and aggregators without causing circular imports.
"""

import inspect
from collections import Counter
from typing import Any, Callable, Collection, Dict, List, Sequence, TypeVar

T = TypeVar("T")


def _bind_kwargs_to_func(
    f: Callable[..., Any], *args: Any, **kwargs: Any
) -> inspect.BoundArguments:
    """Bind positional and keyword arguments to ``f`` while ignoring extraneous keys.

    Private helpers frequently need to align dataset samples with metric signatures;
    this routine mirrors ``inspect.signature.bind_partial`` but tolerates additional
    keys that are not part of the callable signature. It deliberately refuses
    callables that only implement one of ``*args``/``**kwargs`` because such partial
    variadic signatures make downstream validation ambiguous.
    """
    signature = inspect.signature(f)
    parameters = signature.parameters

    f_accepts_var_pos = any(
        parameter.kind == inspect.Parameter.VAR_POSITIONAL for parameter in parameters.values()
    )
    f_accepts_var_kw = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
    )

    if f_accepts_var_pos and f_accepts_var_kw:
        return signature.bind(*args, **kwargs)

    if f_accepts_var_pos or f_accepts_var_kw:
        raise RuntimeError(
            "Unexpected signature of function for binding argument. "
            "If you want to capture all args, both `*args` and `**kwargs` must be in the signature of the function."
        )

    relevant_kwargs = {
        k: v
        for k, v in kwargs.items()
        if k in parameters
        and parameters[k].kind
        in (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    }

    try:
        bound_args = signature.bind_partial(*args, **relevant_kwargs)
        bound_args.apply_defaults()
        return bound_args
    except TypeError as e:
        raise RuntimeError("Unexpected error in binding args to function.") from e


def _chain_exceptions(exceptions: Sequence[Exception]) -> Exception:
    """Produce a causal chain of exceptions for consolidated error reporting."""
    if not exceptions:
        raise RuntimeError("No Exception to Chain: `chain` is empty.")
    tail = exceptions[0]
    for exc in exceptions[1:]:
        # The latest exception should surface while keeping the earlier attempts as
        # ``__cause__`` so the whole retry history is preserved for debugging.
        exc.__cause__ = tail
        tail = exc
    return tail


def _get_callable_name(fn: Callable[..., Any]) -> str:
    """Return a human-readable name for ``fn`` suitable for logging."""
    if inspect.isfunction(fn) or inspect.ismethod(fn):
        return fn.__name__
    elif inspect.isclass(fn):
        return fn.__name__
    elif hasattr(fn, "__call__"):
        return type(fn).__name__
    else:
        return repr(fn)


def _get_duplicates(values: Collection[T]) -> List[T]:
    """Return the subset of repeated values while preserving the original type."""
    return [item for item, count in Counter(values).items() if count > 1]


def _map_names(input: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
    """Translate keys using ``mapping`` while keeping unmapped entries untouched."""
    return {(mapping[k] if k in mapping else k): v for k, v in input.items()}
