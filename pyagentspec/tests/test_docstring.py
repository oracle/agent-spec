# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import doctest
import glob
import os
from pathlib import Path
from typing import List

import pytest

from pyagentspec.llms import LlmConfig

PYAGENTSPEC_DIR = Path(os.path.dirname(__file__)).parent


def get_all_src_files() -> List[str]:
    return glob.glob(str(PYAGENTSPEC_DIR) + "/src/**/*.py", recursive=True)


ONLY_FILE_VAR = "ONLY_FILE"


@pytest.mark.parametrize("file_path", get_all_src_files())
def test_examples_in_docstrings_can_be_successfully_ran(
    default_llm_config: LlmConfig, file_path: str
) -> None:
    if ONLY_FILE_VAR in os.environ and os.environ[ONLY_FILE_VAR] not in file_path:
        pytest.skip(f"Skipping because we only want to run {os.environ[ONLY_FILE_VAR]}")

    # Check the docs at https://docs.python.org/3/library/doctest.html#doctest.testfile
    # if you want to understand how this test works.
    doctest.testfile(
        filename=file_path,
        module_relative=False,
        globs={
            "llm_config": default_llm_config,
        },
        raise_on_error=True,
        verbose=True,
    )
