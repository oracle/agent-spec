# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Class to lazily load modules."""

import importlib
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
