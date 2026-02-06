# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import asyncio
from typing import Any, Dict, Tuple

from pyagentspec.evaluation.metrics import metric


@metric()
async def exact_binary_match(reference: str, response: str) -> Tuple[bool, Dict[str, Any]]:
    return reference == response, {}


samples = [
    ("Zürich", "Zurich"),
    ("Lausanne", "Lausanne"),
    ("Genève", "Geneva"),
]


async def main() -> None:
    for reference, response in samples:
        value, _ = await exact_binary_match(reference, response)
        print(f"Is {response} an exact match of {reference}? {value}.")


if __name__ == "__main__":
    asyncio.run(main())
