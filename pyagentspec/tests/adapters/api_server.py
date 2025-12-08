# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from fastapi import FastAPI

app = FastAPI()


@app.get("/api/weather/{city}")
async def root(city):
    return {"weather": "sunny"}


if __name__ == "__main__":
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="Run FastAPI app with custom host and port.")
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Host address to bind to. Default is localhost",
    )
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to. Default is 8000")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port, reload=False)
