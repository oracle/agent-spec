# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Class to lazily load modules."""

import importlib
import types
from typing import Any, Dict, Optional, Tuple, Type


class LazyLoader:
    """Lazy module Loader.

    This object loads a module only when we fetch attributes from it.
    It can be used to import modules in one files which are not
    present in all the runtime environment where it will be executed.

    For example, optional dependencies (e.g., the ones used for datastores)
    can be lazily loaded so that we can have:

    * All imports neatly organized at the top of the module
    * Obvious distinction between typechecking imports and functional imports for
        optional dependencies.

    Parameters
    ----------
    lib_name :
        Full module path (e.g torch.data.utils)

    callable_name :
        If not ``None``, the Lazy loader only imports a specific
        callable (class or function) from the module

    Examples
    --------
    For example, if ``pandas`` were an optional dependency, we could import from it as follows,
    to lazily load the classes only when the functionality using it is required:
    >>> from typing import TYPE_CHECKING
    >>> from pyagentspec._lazy_loader import LazyLoader
    >>> if TYPE_CHECKING:
    ...     import pandas as pd
    ...     # Add any other type definitions that use pandas here as well
    ... else:
    ...     pd = LazyLoader("pandas")

    When using the optional dependency in type hints, ensure that the
    annotation uses deferred evaluation (type hint is in quotes):

    >>> def transform_dataframe(df: "pd.DataFrame") -> "pd.DataFrame":
    ...     return pd.concat([df, df])  # We only import pandas once this line executes

    """

    def __init__(
        self,
        lib_name: str,
        callable_name: Optional[str] = None,
    ):
        self.lib_name: str = lib_name
        self._mod: Optional[Any] = None
        self.callable_name: Optional[str] = callable_name

    def __load_module(self) -> None:
        if self._mod is None:
            try:
                self._mod = importlib.import_module(self.lib_name)
                if self.callable_name is not None:
                    self._mod = getattr(self._mod, self.callable_name)
            except ModuleNotFoundError as e:
                raise ImportError(
                    f"Package {self.lib_name.split('.')[0]} is not installed. "
                    "Some features require additional dependencies that must be "
                    "installed separately with one of the PyAgentSpec installation options."
                ) from e

    def _load(self) -> Any:
        """Load and return the wrapped module or callable."""
        self.__load_module()
        if self._mod is None:
            raise ImportError(
                f"Something went wrong when lazily loading the module {self.lib_name}"
            )
        return self._mod

    def __getattr__(self, name: str) -> Any:
        """
        Load the module or the callable
        and fetches an attribute from it.

        Parameters
        ----------
        name:
            name of the module attribute to fetch

        Returns
        -------
            The fetched attribute from the loaded module or callable
        """
        self.__load_module()
        return getattr(self._mod, name)

    def __getstate__(self) -> Dict[str, Any]:
        return {"lib_name": self.lib_name, "_mod": None, "callable_name": self.callable_name}

    def __setstate__(self, d: Dict[str, Any]) -> None:
        self.__dict__.update(d)

    def __reduce__(self) -> Tuple[Type["LazyLoader"], Tuple[str, Optional[str]]]:
        return (self.__class__, (self.lib_name, self.callable_name))

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        Call the callable and returns its output
        if a callable is given as argument.

        Parameters
        ----------
        args: List
            Arguments passed to the callable
        kwargs: Dict
            Optional arguments passed to the callable

        Raises
        ------
        TypeError
            when the callable name is not specified.

        Returns
        -------
        Callable result
        """
        self.__load_module()
        if self.callable_name is None:
            raise TypeError(f"Module {self.lib_name} is not callable.")
        if self._mod is None:
            raise ImportError(
                f"Something went wrong when lazily loading the module {self.lib_name}"
            )
        return self._mod(*args, **kwargs)


class _LazyTypeMeta(type):
    """Metaclass for class-like lazy proxies returned by :func:`LazyType`.

    ``LazyLoader`` works well for module aliases, but ``LazyLoader("pkg").Cls``
    imports ``pkg`` immediately because attribute access is the loading trigger.
    ``LazyType`` instead creates a placeholder class whose metaclass loads the
    real class only when code constructs it, reads an attribute from it, or uses
    it in ``isinstance``/``issubclass`` checks.

    The metaclass is what lets the proxy participate in operations that Python
    normally performs on classes rather than instances:

    * ``Proxy(...)`` calls ``_LazyTypeMeta.__call__`` and constructs the real class.
    * ``isinstance(obj, Proxy)`` calls ``_LazyTypeMeta.__instancecheck__``.
    * ``issubclass(cls, Proxy)`` calls ``_LazyTypeMeta.__subclasscheck__``.
    * ``Proxy.some_attr`` calls ``_LazyTypeMeta.__getattr__``.
    * ``class Subclass(Proxy)`` replaces the proxy base with the real class
      when available, or with ``object`` when the optional dependency is absent.

    This keeps adapter ``_types.py`` modules importable when optional runtime
    packages are absent, while preserving the normal class-shaped API once the
    optional dependency is actually used.
    """

    def __new__(
        mcls: Type["_LazyTypeMeta"],
        name: str,
        bases: Tuple[type, ...],
        namespace: Dict[str, Any],
        **kwargs: Any,
    ) -> Type[Any]:
        resolved_bases = []
        for base in bases:
            if isinstance(base, _LazyTypeMeta) and "_lazy_loader" in base.__dict__:
                try:
                    base = base._load_target()
                except ImportError:
                    base = object
            resolved_bases.append(base)
        resolved_bases_tuple = tuple(resolved_bases)
        if resolved_bases_tuple != bases:
            # Subclassing a lazy proxy must create a real subclass of the target
            # class. Otherwise the subclass inherits this metaclass and calling it
            # is redirected to the proxy target's constructor.
            #
            # If the optional dependency is absent, use object as the base so the
            # importing module can still define its class and fail later at the
            # actual optional-dependency use site.
            def exec_body(ns: Dict[str, Any]) -> None:
                ns.update(namespace)

            return types.new_class(name, resolved_bases_tuple, {}, exec_body)

        return super().__new__(mcls, name, bases, namespace, **kwargs)

    def _load_target(cls) -> Any:
        return cls.__dict__["_lazy_loader"]._load()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if "_lazy_loader" in cls.__dict__:
            return cls._load_target()(*args, **kwargs)
        return super().__call__(*args, **kwargs)

    def __getattr__(cls, name: str) -> Any:
        if "_lazy_loader" not in cls.__dict__:
            raise AttributeError(name)
        return getattr(cls._load_target(), name)

    def __instancecheck__(cls, instance: Any) -> bool:
        return isinstance(instance, cls._load_target())

    def __subclasscheck__(cls, subclass: type) -> bool:
        return issubclass(subclass, cls._load_target())

    def __repr__(cls) -> str:
        if "_lazy_loader" not in cls.__dict__:
            return super().__repr__()
        lazy_loader = cls.__dict__["_lazy_loader"]
        return f"<lazy type {lazy_loader.lib_name}.{lazy_loader.callable_name}>"


def _lazy_type_class_getitem(cls: type, item: Any) -> type:
    # Allows annotations like ``StateGraph[Any, Any]`` without importing the
    # optional package at module import time.
    return cls


def LazyType(lib_name: str, type_name: str) -> Type[Any]:
    """Create a lazy class-like proxy for a type from an optional dependency.

    Use this when source code needs to keep an optional dependency class in a
    module-level alias for runtime checks or construction:

    >>> from pyagentspec._lazy_loader import LazyType
    >>> StateGraph = LazyType("langgraph.graph", "StateGraph")

    Unlike ``LazyLoader("langgraph.graph").StateGraph``, creating the alias does
    not import ``langgraph``. Importing happens only when the proxy is used like
    the real class.

    This is intentionally narrower than ``LazyLoader``: it is meant for classes
    that appear in unions, ``isinstance`` checks, constructors, or generic type
    aliases inside adapter modules. For optional dependency modules or functions,
    prefer ``LazyLoader`` directly.
    """
    return _LazyTypeMeta(
        type_name,
        (),
        {
            "__module__": lib_name,
            "_lazy_loader": LazyLoader(lib_name, type_name),
            "__class_getitem__": classmethod(_lazy_type_class_getitem),
        },
    )
