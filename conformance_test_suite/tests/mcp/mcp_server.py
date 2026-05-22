# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from mcp.server.fastmcp import FastMCP

PAYSLIPS = [
    {
        "Amount": 7612,
        "Currency": "USD",
        "PeriodStartDate": "2025/05/15",
        "PeriodEndDate": "2025/06/15",
        "PaymentDate": "",
        "DocumentId": 2,
        "PersonId": 2,
    },
    {
        "Amount": 5000,
        "Currency": "CHF",
        "PeriodStartDate": "2024/05/01",
        "PeriodEndDate": "2024/06/01",
        "PaymentDate": "2024/05/15",
        "DocumentId": 1,
        "PersonId": 1,
    },
    {
        "Amount": 10000,
        "Currency": "EUR",
        "PeriodStartDate": "2025/06/15",
        "PeriodEndDate": "2025/10/15",
        "PaymentDate": "",
        "DocumentsId": 3,
        "PersonId": 3,
    },
]

server = FastMCP(
    name="Example MCP Server",
    instructions="A MCP Server.",
)


@server.tool(description="Return session details for the current user")
def get_user_session():
    return {
        "PersonId": "1",
        "Username": "Bob.b",
        "DisplayName": "Bob B",
    }


@server.tool(description="Return payslip details for a given PersonId")
def get_payslips(PersonId: int):
    return [payslip for payslip in PAYSLIPS if payslip["PersonId"] == int(PersonId)]


app = server.streamable_http_app()
