# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Collection, Dict, Hashable


class _DataSource(ABC):
    """Interface for asynchronous feature stores powering evaluation datasets."""

    @abstractmethod
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

    @abstractmethod
    def features(self) -> Collection[str]:
        """
        Return the sequence of feature names provided by this data source.

        Returns
        -------
        Sequence[str]
            Names of all features available in samples.
        """

    @abstractmethod
    def ids(self) -> AsyncIterator[Hashable]:
        """
        Asynchronously yield all available sample identifiers.

        Yields
        ------
        Hashable
            Unique identifier for a sample.
        """

    @abstractmethod
    def __len__(self) -> int:
        """
        Synchronously get the number of available samples.

        Returns
        -------
        int
            Number of samples.
        """
