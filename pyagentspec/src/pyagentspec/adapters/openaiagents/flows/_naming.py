# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from __future__ import annotations

import binascii


def stable_id(seed: str) -> str:
    """Return a short, deterministic ID from a seed string.

    Uses CRC32 for stability (non-cryptographic), rendered as 8 hex chars.
    """
    crc = binascii.crc32(seed.encode("utf-8")) & 0xFFFFFFFF
    return f"{crc:08x}"


def sanitize_name(name: str) -> str:
    """Sanitize a human-friendly identifier for codegen constants.

    Replace non-alnum with underscores and uppercase.
    """

    out = [ch if ch.isalnum() else "_" for ch in name]
    return "".join(out).upper()
