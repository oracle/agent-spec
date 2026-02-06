# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any

import pytest

from pyagentspec.evaluation import Dataset


@pytest.fixture()
def data() -> list[dict[str, Any]]:
    return [
        {"reference": "Zürich", "response": "Zurich"},
        {"reference": "Bern", "response": "Bern"},
        {"reference": "Geneva", "response": "Genève"},
    ]


@pytest.fixture()
def df_dataset(data) -> Dataset:
    import pandas as pd

    return Dataset.from_df(pd.DataFrame(data))


@pytest.fixture()
def dict_dataset(data) -> Dataset:
    return Dataset.from_dict(data)


@pytest.mark.parametrize("dataset_name", ("df_dataset", "dict_dataset"))
@pytest.mark.anyio
async def test_df_loader(
    dataset_name: str, data: list[dict[str, Any]], request: pytest.FixtureRequest
) -> None:
    dataset: Dataset = request.getfixturevalue(dataset_name)

    assert len(dataset) == 3
    assert list(sorted(dataset.features())) == ["reference", "response"]
    assert [_i async for _i in dataset.ids()] == [0, 1, 2]
    async for _i in dataset.ids():
        assert await dataset.get_sample(_i) == data[_i]
