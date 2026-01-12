# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
import argparse
from contextvars import ContextVar
from os import PathLike
from typing import Literal, Optional

from mcp.server.fastmcp import FastMCP as BaseFastMCP
from starlette.applications import Starlette
from typing_extensions import TypedDict

UvicornExtraConfig = TypedDict(
    "UvicornExtraConfig",
    {
        "ssl_keyfile": str | PathLike[str] | None,
        "ssl_certfile": str | PathLike[str] | None,
        "ssl_ca_certs": str | None,
        "ssl_cert_reqs": int,
    },
    total=False,
)

_EXTRA_CONFIG: ContextVar[Optional[UvicornExtraConfig]] = ContextVar("_EXTRA_CONFIG", default=None)


class FastMCP(BaseFastMCP):
    async def _start_server(self, starlette_app: Starlette) -> None:
        import uvicorn

        extra_config = _EXTRA_CONFIG.get()

        config = uvicorn.Config(
            starlette_app,
            host=self.settings.host,
            port=self.settings.port,
            log_level=self.settings.log_level.lower(),
            **extra_config,
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def run_sse_async(self, mount_path: str | None = None) -> None:
        """Run the server using SSE transport."""
        starlette_app = self.sse_app(mount_path)
        await self._start_server(starlette_app)

    async def run_streamable_http_async(self) -> None:
        """Run the server using StreamableHTTP transport."""
        starlette_app = self.streamable_http_app()
        await self._start_server(starlette_app)


def create_server(host: str, port: int):
    """Create and configure the MCP server"""
    server = FastMCP(
        name="Example MCP Server",
        instructions="A MCP Server.",
        host=host,
        port=port,
    )

    @server.tool(
        description="Return the result of the fooza operation between numbers a and b. Do not use for anything else than computing a fooza operation."
    )
    def fooza_tool(a: int, b: int) -> int:
        return a * 2 + b * 3 - 1

    @server.tool(
        description="Return the result of the bwip operation between numbers a and b. Do not use for anything else than computing a bwip operation."
    )
    def bwip_tool(a: int, b: int) -> int:
        return a - b + 1

    @server.tool(
        description="Return the result of the zbuk operation between numbers a and b. Do not use for anything else than computing a zbuk operation."
    )
    def zbuk_tool(a: int, b: int) -> int:
        return a + b * 2

    @server.tool(description="Tool to return a random string")
    def generate_random_string() -> str:

        return "random_string_1234"

    return server


def main(
    host: str,
    port: int,
    mode: Literal["sse", "streamable-http"],
    ssl_keyfile: str | None,
    ssl_certfile: str | None,
    ssl_ca_certs: str | None,
    ssl_cert_reqs: int,
):
    _EXTRA_CONFIG.set(
        dict(
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            ssl_ca_certs=ssl_ca_certs,
            ssl_cert_reqs=ssl_cert_reqs,
        )
    )
    server = create_server(host=host, port=port)
    server.run(transport=mode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process host, port, and mode.")

    parser.add_argument(
        "--host", type=str, help='The host address (e.g., "localhost" or "127.0.0.1")'
    )
    parser.add_argument("--port", type=int, help="The port number (e.g., 8080)")
    parser.add_argument(
        "--mode", type=str, choices=["sse", "streamable-http"], help="The mode for the application"
    )
    parser.add_argument(
        "--ssl_keyfile", type=str, help="Path to the server private key file (PEM format)."
    )
    parser.add_argument(
        "--ssl_certfile", type=str, help="Path to the server certificate chain file (PEM format)."
    )
    parser.add_argument(
        "--ssl_ca_certs", type=str, help="Path to the trusted CA certificate file (PEM format)."
    )
    parser.add_argument(
        "--ssl_cert_reqs", type=int, help="Server certificate verify mode (0=None or 2=Required)."
    )

    args = parser.parse_args()

    main(
        host=args.host,
        port=args.port,
        mode=args.mode,
        ssl_keyfile=args.ssl_keyfile,
        ssl_certfile=args.ssl_certfile,
        ssl_ca_certs=args.ssl_ca_certs,
        ssl_cert_reqs=args.ssl_cert_reqs,
    )
