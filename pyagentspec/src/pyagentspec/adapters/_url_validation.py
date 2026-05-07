# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Helpers for URL validation and optional allow-list handling in HTTP-based components."""

import warnings
from typing import List, Optional, Tuple
from urllib.parse import urlsplit

from pydantic import AnyUrl

from pyagentspec.templating import get_placeholders_from_string


def _get_url_match_parts(url: str) -> Tuple[str, str, str]:
    """Return the URL parts used for allow-list matching.

    Matching intentionally considers only scheme, authority, and path.
    Query parameters, URL params, and fragments are ignored.
    """
    normalized_url = str(AnyUrl(url))
    parsed_url = urlsplit(normalized_url)
    return parsed_url.scheme, parsed_url.netloc, parsed_url.path or "/"


def _matches_allow_list_entry(url: str, pattern: str) -> bool:
    """Check whether a URL matches one allow-list entry."""
    url_scheme, url_netloc, url_path = _get_url_match_parts(url)
    pattern_scheme, pattern_netloc, pattern_path = _get_url_match_parts(pattern)
    return (
        url_scheme == pattern_scheme
        and url_netloc == pattern_netloc
        and url_path.startswith(pattern_path)
    )


def get_url_destination_placeholder_names(url: str) -> List[str]:
    """Return placeholders used in the URL destination part.

    The destination is limited to the scheme, host, and port. Placeholders
    appearing only in path, query, or fragment are ignored.
    """
    scheme_separator = url.find("://")
    if scheme_separator != -1:
        scheme_part = url[:scheme_separator]
        remainder = url[scheme_separator + 3 :]
    else:
        scheme_part = ""
        remainder = url

    authority_end_positions = [
        pos for pos in (remainder.find("/"), remainder.find("?"), remainder.find("#")) if pos != -1
    ]
    authority_end = min(authority_end_positions) if authority_end_positions else len(remainder)
    authority = remainder[:authority_end]
    hostport = authority.rsplit("@", 1)[1] if "@" in authority else authority
    return sorted(
        set(get_placeholders_from_string(scheme_part) + get_placeholders_from_string(hostport))
    )


def maybe_warn_about_unrestricted_templated_url(
    url: str,
    url_allow_list: Optional[List[str]],
    component_name: str,
) -> None:
    """Warn when a templated URL destination is used without an allow list."""
    if url_allow_list is not None:
        return

    placeholder_names = get_url_destination_placeholder_names(url)
    if not placeholder_names:
        return

    variable_list = ", ".join(f"`{name}`" for name in placeholder_names)
    warnings.warn(
        f"{component_name} uses placeholders in the URL destination ({variable_list}) "
        "but no `url_allow_list` is configured. Keep the base URL developer-controlled and "
        "template only path, query, or body values when possible.",
        UserWarning,
        stacklevel=2,
    )


def validate_url_against_allow_list(url: str, url_allow_list: Optional[List[str]]) -> None:
    """Validate a URL against an optional allow list."""
    if url_allow_list is None:
        return

    if any(_matches_allow_list_entry(url, pattern) for pattern in url_allow_list):
        return

    raise ValueError(
        "Requested URL is not in allowed list. "
        "Please contact the application administrator to help adding your URL to the list."
    )
