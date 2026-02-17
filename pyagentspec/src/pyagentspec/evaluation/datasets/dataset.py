# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import TYPE_CHECKING, Any, AsyncIterator, Collection, Dict, Hashable, List, Literal

from pyagentspec._lazy_loader import LazyLoader
from pyagentspec.evaluation.datasets._data_source import _DataSource
from pyagentspec.evaluation.datasets._dict_data_source import _DictDataSource

if TYPE_CHECKING:
    # Important: do not move this import out of the TYPE_CHECKING block so long as pandas is an optional dependency.
    # Otherwise, importing the module when they are not installed would lead to an import error.

    import pandas as pd
else:
    pd = LazyLoader("pandas")


class Dataset(_DataSource):
    """Concrete wrapper around ``_DataSource`` implementations used during evaluation."""

    def __init__(self, _data_source: _DataSource) -> None:
        """
        Initialize the dataset wrapper; prefer factory constructors over direct use.

        .. warning::
            Users should not initialize a dataset directly.
            Instead, you should use loaders (``from_dict``, ``from_df``, etc.).
        """

        super().__init__()
        self._data_source = _data_source

    async def get_sample(self, id: Hashable) -> Dict[str, Any]:
        """
        Asynchronously fetch a data sample given its identifier.

        Parameters
        ----------
        id : Hashable
            Unique identifier for the sample to fetch.

        Returns
        -------
        Dict[str, Any]
            Dictionary containing feature values for the sample.
        """

        return await self._data_source.get_sample(id)

    def features(self) -> Collection[str]:
        """
        Return the sequence of feature names provided by this data source.

        Returns
        -------
        Sequence[str]
            Names of all features available in samples.
        """

        return self._data_source.features()

    def ids(self) -> AsyncIterator[Hashable]:
        """
        Asynchronously yield all available sample identifiers.

        Yields
        ------
        Hashable
            Unique identifier for a sample.
        """

        return self._data_source.ids()

    def __len__(self) -> int:
        """
        Synchronously get the number of available samples.

        Returns
        -------
        int
            Number of samples.
        """

        return len(self._data_source)

    @staticmethod
    def from_dict(
        data: Dict[Hashable, Dict[str, Any]] | List[Dict[str, Any]],
        features_consistency: Literal["strict", "relaxed", "bypass"] = "strict",
    ) -> "Dataset":
        """
        Initialize a dataset with a collection of samples and determine feature consistency.

        Parameters
        ----------
        data : Dict[Hashable, Dict[str, Any]] or List[Dict[str, Any]]
            The dataset. If a dictionary, keys are sample identifiers and values are feature dictionaries.
            If a list, each item is a feature dictionary and sample identifiers are assigned as sequential indices.

        features_consistency : {"strict", "relaxed", "bypass"}, default "strict"
            Policy for validating feature keys consistency across samples:
                - "strict": All samples must have identical feature keys.
                - "relaxed": Uses only the intersection of keys from all samples.
                - "bypass": Uses feature keys from the first sample only.

            .. warning::
                Bypass consistency control is solely for performance optimization.
                If there is an inconsistency in the dataset, it may later resulted into errors during evaluation.
                Use bypass only when you are sure about the consistency of your dataset.

        Raises
        ------
        TypeError
            If the data input is neither a dict nor a sequence of feature dictionaries.

        ValueError
            If samples are missing, feature keys are inconsistent in "strict" mode, or no features are found.

        """

        return Dataset(_DictDataSource(data, features_consistency=features_consistency))

    @staticmethod
    def from_df(df: pd.DataFrame) -> "Dataset":
        """
        Creating a dataset from a pandas dataframe. The dataframe must have a single level header.

        Parameters
        ----------
        df:
            An instance of pandas dataframe.

        Returns
        -------
        A dataset that wraps that dataframe.

        Raises
        ------
        ValueError
            If any of the columns headers is not string
        """

        if not all(isinstance(col, str) for col in df.columns):
            raise ValueError(
                f"All DataFrame column headers must be strings. Found: {list(df.columns)}."
            )

        data = {id_: dict(sample) for id_, sample in df.iterrows()}
        return Dataset(_DictDataSource(data, features_consistency="bypass"))
