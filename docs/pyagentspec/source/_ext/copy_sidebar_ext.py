# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import logging
from pathlib import Path

from sphinx.application import Sphinx

logger = logging.getLogger(__name__)

INDEX_NAME = "index.html"  # DO NOT CHANGE
SOURCE_INDEX_NAME = "_pyagentspec_navigation.html"  # DO NOT CHANGE


def copy_sidebar_at_build_time(app: Sphinx, exception):
    if exception is not None or app.builder.name != "html":
        return

    build_dir = Path(app.outdir)
    index_path = build_dir / INDEX_NAME
    source_index_path = build_dir / SOURCE_INDEX_NAME

    if not index_path.exists() or not source_index_path.exists():
        logger.warning("Could not find %s or %s", INDEX_NAME, SOURCE_INDEX_NAME)
        return

    with open(index_path, "r", encoding="utf-8") as f:
        target_lines = f.readlines()

    with open(source_index_path, "r", encoding="utf-8") as f:
        source_lines = f.readlines()

    source_start_idx = None
    source_end_idx = None
    for i, line in enumerate(source_lines):
        if '<dialog id="pst-primary-sidebar-modal"></dialog>' in line:
            source_start_idx = i + 1
        if '<div id="searchbox"></div>' in line:
            source_end_idx = i - 2
            break

    # Find where to insert in the target file
    target_start_idx = None
    target_end_idx = None
    for i, line in enumerate(target_lines):
        if '<dialog id="pst-primary-sidebar-modal"></dialog>' in line:
            target_start_idx = i + 1
        if '<div id="searchbox"></div>' in line:
            target_end_idx = i - 2
            break

    # Check if we found all necessary markers
    if None in (source_start_idx, source_end_idx, target_start_idx, target_end_idx):
        logger.warning(
            "Could not find all markers in HTML files.\nSource markers: %s, %s\nTarget markers: %s, %s",
            source_start_idx,
            source_end_idx,
            target_start_idx,
            target_end_idx,
        )
        return

    # Extract the sidebar content from source and replace target content
    sidebar_content = source_lines[source_start_idx : source_end_idx + 1]
    modified_lines = target_lines[:target_start_idx]
    modified_lines.extend(sidebar_content)
    modified_lines.extend(target_lines[target_end_idx + 1 :])

    # Remove the hide-on-wide class if present
    for i, line in enumerate(modified_lines):
        if 'id="pst-primary-sidebar"' in line and "hide-on-wide" in line:
            modified_lines[i] = line.replace("hide-on-wide", "")

    with open(index_path, "w", encoding="utf-8") as f:
        f.writelines(modified_lines)

    logger.info("Successfully copied sidebar from %s to %s", SOURCE_INDEX_NAME, INDEX_NAME)
    logger.info("Copied lines %s to %s from source", source_start_idx, source_end_idx)
    logger.info("Replaced lines %s to %s in target", target_start_idx, target_end_idx)


def setup(app: Sphinx):
    app.connect("build-finished", copy_sidebar_at_build_time)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
