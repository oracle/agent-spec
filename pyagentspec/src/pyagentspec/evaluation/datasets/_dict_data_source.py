# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, AsyncIterator, Collection, Dict, Hashable, List, Literal, Set

from pyagentspec.evaluation.datasets._data_source import _DataSource


class _DictDataSource(_DataSource):
    """Data source backed by an in-memory dictionary of sample features."""

    def __init__(
        self,
        data: Dict[Hashable, Dict[str, Any]] | List[Dict[str, Any]],
        features_consistency: Literal["strict", "relaxed", "bypass"] = "strict",
    ) -> None:
        """
        Initialize the data source with a collection of samples and determine feature consistency.

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
                If there is an inconsistency in the dataset, it may later result into errors during evaluation.
                Use bypass only when you are sure about the consistency of your dataset.

        Raises
        ------
        TypeError
            If the data input is neither a dict nor a sequence of feature dictionaries.

        ValueError
            If samples are missing, feature keys are inconsistent in "strict" mode, or no features are found.

        """

        if isinstance(data, dict):
            _data = data
        elif isinstance(data, list):
            _data = {id_: sample for id_, sample in enumerate(data)}
        else:
            raise TypeError(
                "`data` must be a dict of sample_id to feature dict, or a list of feature dicts."
            )

        _features = self._require_features(_data, features_consistency)

        super().__init__()
        self.data = _data
        self.features_consistency = features_consistency
        self._features = _features

    def _require_features(
        self,
        data: Dict[Hashable, Dict[str, Any]],
        features_consistency: Literal["strict", "relaxed", "bypass"],
    ) -> Set[str]:
        try:
            data_iterator = iter(data.items())
            _, first_sample = next(data_iterator)
        except StopIteration:
            raise ValueError("The `DataSource` contains no samples.")

        features = set(first_sample.keys())

        if features_consistency == "strict":
            for id_, sample in data_iterator:
                keys = set(sample.keys())
                if keys != features:
                    raise ValueError(
                        f"Sample {id_} has keys {keys}, "
                        f"which differ from reference keys {features}."
                    )
        elif features_consistency == "relaxed":
            for _, sample in data_iterator:
                features &= set(sample.keys())
        elif features_consistency == "bypass":
            pass
        else:
            raise TypeError(f"Unknown `features_consistency` mode: {features_consistency}.")

        if not features:
            raise ValueError("No features found under the selected consistency policy.")

        return features

    async def get_sample(self, id: Hashable) -> Dict[str, Any]:
        try:
            return self.data[id]
        except KeyError:
            raise KeyError(f"No sample with id {id} found in the dataset.")

    def features(self) -> Collection[str]:
        return self._features

    async def ids(self) -> AsyncIterator[Hashable]:
        for key in self.data:
            yield key

    def __len__(self) -> int:
        return len(self.data)
