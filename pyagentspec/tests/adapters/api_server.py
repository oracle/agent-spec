# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import json
import re
from urllib.parse import parse_qs

from fastapi import FastAPI, Request

app = FastAPI()


@app.get("/api/weather/{city}")
async def root(city):
    return {"weather": "sunny"}


async def _make_echo_payload(request: Request):
    """Create a simple echo response from the incoming request.

    - Reads headers, query params, and the request body (JSON, form, or plain text).
    - Combines them into one dict.
    - Adds the request URL, path, and whether JSON was received.
    """
    # Collect query params and headers
    query = dict(request.query_params)
    body_values = {}
    json_received = False

    # Read body (if any)
    raw_body = await request.body()

    content_type = (request.headers.get("content-type") or "").lower()

    def parse_text_payload(text: str) -> dict:
        res = {}
        m_val = re.search(r"value\s*:\s*([^,\]]+)", text)
        if m_val:
            res["value"] = m_val.group(1).strip()
        m_list = re.search(r"listofvalues\s*:\s*\[(.*?)\]", text)
        if m_list:
            items = [s.strip() for s in m_list.group(1).split(",")]
            res["listofvalues"] = items
        return res

    def handle_json_loaded(j):
        # Accept dicts directly; for lists of descriptive strings, parse into a dict
        if isinstance(j, dict):
            return j
        if isinstance(j, list):
            tmp = {}
            for item in j:
                if isinstance(item, str):
                    tmp.update(parse_text_payload(item))
            return tmp
        return {}

    if raw_body:
        if "application/json" in content_type:
            try:
                j = json.loads(raw_body)
                json_received = True
                body_values = handle_json_loaded(j)
            except Exception:
                body_values = {}
        elif "application/x-www-form-urlencoded" in content_type:
            try:
                q = parse_qs(raw_body.decode(errors="replace"), keep_blank_values=True)
                body_values = {k: (v if len(v) > 1 else v[0]) for k, v in q.items()}
            except Exception:
                body_values = {}
        else:
            # Try JSON first as best-effort, then plain-text format
            try:
                j = json.loads(raw_body)
                json_received = True
                body_values = handle_json_loaded(j)
            except Exception:
                try:
                    text = raw_body.decode(errors="replace")
                    body_values = parse_text_payload(text)
                except Exception:
                    body_values = {}

    json_body_message = "JSON received" if json_received else "JSON not received"

    content = {
        "test": "test",
        "__full_path": str(request.url),
        "__parsed_path": request.url.path,
        "json_body_received": json_body_message,
        **dict(request.headers.items()),
        **query,
        **body_values,
    }
    return content


@app.get("/api/echo/{u1}")
async def echo_get(u1: str, request: Request):
    return await _make_echo_payload(request)


@app.post("/api/echo/{u1}")
async def echo_post(u1: str, request: Request):
    return await _make_echo_payload(request)


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
