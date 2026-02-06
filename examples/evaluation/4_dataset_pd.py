# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import asyncio

import pandas as pd

from pyagentspec.evaluation import Dataset

df = pd.read_csv("./example.csv")
dataset = Dataset.from_df(df)


async def main() -> None:
    async for id in dataset.ids():
        sample = await dataset.get_sample(id)
        print(f"Sample {id}: {sample}")


if __name__ == "__main__":
    asyncio.run(main())
