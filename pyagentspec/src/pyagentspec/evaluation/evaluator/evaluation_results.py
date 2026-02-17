# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import TYPE_CHECKING, Any, Dict, Hashable, List, Tuple

from pyagentspec._lazy_loader import LazyLoader
from pyagentspec.evaluation._computers import _result_to_dict

if TYPE_CHECKING:
    # Important: do not move this import out of the TYPE_CHECKING block so long as pandas is an optional dependency.
    # Otherwise, importing the module when they are not installed would lead to an import error.

    import pandas as pd
else:
    pd = LazyLoader("pandas")


class EvaluationResults:
    """
    Container for storing and accessing evaluation metric results for multiple samples and metrics.

    This class provides utilities to work with evaluation results that are organized as a mapping between
    (sample_id, metric_name) pairs and their corresponding result values and details. It enables exporting
    the results to common formats such as JSON and pandas DataFrame for further analysis or reporting.

    Attributes
    ----------
    results : Dict[Tuple[Hashable, str], Tuple[Any, Dict[str, Any]]]
        Dictionary mapping (sample_id, metric_name) pairs to their metric result and related details.

    sample_ids : List[Hashable]
        List of sample identifiers present in the results.

    metric_names : List[str]
        List of metric names present in the results.

    """

    def __init__(
        self,
        results: Dict[Tuple[Hashable, str], Tuple[Any, Dict[Hashable, Any]]],
        sample_ids: List[Hashable] | None = None,
        metric_names: List[str] | None = None,
    ) -> None:
        """
        Initialize an EvaluationResults instance.

        Parameters
        ----------
        results : Dict[Tuple[Hashable, str], Tuple[Any, Dict[Hashable, Any]]]
            Dictionary mapping (sample_id, metric_name) pairs to result tuples,
            where each tuple consists of a primary value and a details dictionary.

        sample_ids : List[Hashable], optional
            List of sample identifiers. If not provided, inferred from the sample IDs present in the results dictionary.

        metric_names : List[str], optional
            List of metric names. If not provided, inferred from the metric names present in the results dictionary.

        """

        self.results = results
        self.sample_ids = sample_ids or list({sample_id for sample_id, _ in self.results.keys()})
        self.metric_names = metric_names or list({m_name for _, m_name in self.results.keys()})

    def to_dict(self) -> Dict[Hashable, Dict[str, Dict[str, Any]]]:
        """Return the results keyed by sample and metric in dictionary form.

        Returns
        -------
        Dict[Hashable, Dict[str, Dict[str, Any]]]
            Nested mapping of the form {sample_id: {metric_name: result_dict, ...}, ...},
            where each result_dict has keys 'value' and 'details'.
        """

        return {
            sample_id: {
                metric_name: _result_to_dict(self.results[(sample_id, metric_name)])
                for metric_name in self.metric_names
            }
            for sample_id in self.sample_ids
        }

    def to_df(self) -> pd.DataFrame:
        """Return the results as a :class:`pandas.DataFrame` indexed by sample id.

        Returns
        -------
        pandas.DataFrame
            DataFrame indexed by sample_id with columns as metric names.
            Each cell contains the main result value for the corresponding (sample_id, metric_name) pair
        """

        return pd.DataFrame(
            {
                metric_name: [
                    self.results[(sample_id, metric_name)][0] for sample_id in self.sample_ids
                ]
                for metric_name in self.metric_names
            },
            index=pd.Series(self.sample_ids),
        )
