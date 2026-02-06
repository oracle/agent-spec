# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import re
import string
import unicodedata
from typing import Any, Dict, Tuple

from pyagentspec.evaluation.metrics.metrics import Metric


class ExactBinaryMatchMetric(Metric[bool]):
    """Evaluate whether the response string exactly matches the reference.

    The comparison can optionally ignore case, glyph accents, leading articles,
    punctuation, and whitespace. By default, the metric uses a strict equality
    check between the ``reference`` and ``response`` features provided in the
    evaluation dataset.
    """

    _REFERENCE = "reference"
    _RESPONSE = "response"

    def __init__(
        self,
        name: str = "ExactBinaryMatch",
        ignore_case: bool = False,
        ignore_glyph: bool = False,
        ignore_article: bool = False,
        ignore_punctuations: bool = False,
        ignore_white_spaces: bool = False,
        reference_feature_name: str = "reference",
        response_feature_name: str = "response",
    ) -> None:
        """Configure the exact match metric.

        Parameters
        ----------
        name
            Display name registered for the metric instance.
        ignore_case
            When ``True``, compare strings in a case-insensitive manner.
        ignore_glyph
            When ``True``, strip accent marks and other combining glyphs prior to comparison.
        ignore_article
            When ``True``, drop leading articles (``a``, ``an``, ``the``) before evaluating equality.
        ignore_punctuations
            When ``True``, remove all ASCII punctuation characters.
        ignore_white_spaces
            When ``True``, collapse and remove whitespace before comparison.
        reference_feature_name
            Dataset feature name mapped to the reference string input.
        response_feature_name
            Dataset feature name mapped to the response string input.
        """
        super().__init__(
            name=name,
            input_mapping={
                reference_feature_name: self._REFERENCE,
                response_feature_name: self._RESPONSE,
            },
            num_retries=0,
            on_failure="raise",
        )
        self.ignore_case = ignore_case
        self.ignore_glyph = ignore_glyph
        self.ignore_article = ignore_article
        self.ignore_punctuations = ignore_punctuations
        self.ignore_white_spaces = ignore_white_spaces

    def _normalize(self, text: str) -> str:
        """Apply the configured normalization rules to ``text``."""
        if self.ignore_glyph:
            text = unicodedata.normalize("NFKD", text)
            text = "".join([c for c in text if not unicodedata.combining(c)])

        if self.ignore_case:
            text = text.lower()

        if self.ignore_article:
            text = re.sub(r"\b(a|an|the)\b", "", text, flags=re.IGNORECASE)

        if self.ignore_punctuations:
            text = text.translate(str.maketrans("", "", string.punctuation))

        if self.ignore_white_spaces:
            text = re.sub(r"\s+", "", text)

        return text.strip()

    async def compute_metric(self, reference: str, response: str) -> Tuple[bool, Dict[str, Any]]:
        """Return a boolean flag indicating whether the normalized inputs match."""
        return self._normalize(reference) == self._normalize(response), {}
