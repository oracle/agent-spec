# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import warnings

import pytest

from pyagentspec.adapters._url_security import (
    get_url_destination_placeholder_names,
    maybe_warn_about_unrestricted_templated_url,
    validate_url_against_allow_list,
)


@pytest.mark.parametrize(
    ("url", "expected_placeholders"),
    [
        ("https://{{host}}/orders/{{order_id}}?q={{query}}#{{fragment}}", ["host"]),
        ("{{scheme}}://api.example.com/orders/{{order_id}}", ["scheme"]),
        ("https://api.example.com:{{port}}/orders/{{order_id}}", ["port"]),
        ("https://api.example.com/orders/{{order_id}}?q={{query}}", []),
    ],
)
def test_get_url_destination_placeholder_names_only_returns_destination_placeholders(
    url: str, expected_placeholders: list[str]
) -> None:
    assert get_url_destination_placeholder_names(url) == expected_placeholders


def test_maybe_warn_about_unrestricted_templated_url_warns_for_destination_placeholders() -> None:
    with pytest.warns(
        UserWarning, match="ApiNode `orders` uses placeholders in the URL destination"
    ):
        maybe_warn_about_unrestricted_templated_url(
            url="https://{{host}}/orders/{{order_id}}",
            url_allow_list=None,
            component_name="ApiNode `orders`",
        )


@pytest.mark.parametrize(
    ("url", "url_allow_list"),
    [
        ("https://api.example.com/orders/{{order_id}}", None),
        ("https://{{host}}/orders/{{order_id}}", ["https://allowed.example.com/orders/"]),
    ],
)
def test_maybe_warn_about_unrestricted_templated_url_skips_safe_cases(
    url: str, url_allow_list: list[str] | None
) -> None:
    with warnings.catch_warnings(record=True) as recorded_warnings:
        warnings.simplefilter("always")
        maybe_warn_about_unrestricted_templated_url(
            url=url,
            url_allow_list=url_allow_list,
            component_name="RemoteTool `lookup`",
        )

    assert not recorded_warnings


def test_validate_url_against_allow_list_accepts_matching_destination_and_path_prefix() -> None:
    # Should not raise an exception
    validate_url_against_allow_list(
        "https://allowed.example.com/orders/123?expand=items#details",
        ["https://allowed.example.com/orders/"],
    )


def test_validate_url_against_allow_list_rejects_url_outside_allow_list() -> None:
    with pytest.raises(ValueError, match="Requested URL is not in allowed list"):
        validate_url_against_allow_list(
            "https://blocked.example.com/orders/123",
            ["https://allowed.example.com/orders/"],
        )
