# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import random
import socket
import subprocess  # nosec, test-only code, args are trusted
import time
from pathlib import Path
from typing import Optional

import pytest


def is_port_busy(port: Optional[int]):
    if port is None:
        return True
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


# We try to find an open port between 8000 and 9000 for 5 times, if we don't we skip remote tests
attempt = 0
while (
    is_port_busy(JSON_SERVER_PORT := random.randint(8000, 9000))  # nosec, not for security/crypto
    and attempt < 5
):
    time.sleep(1)
    attempt += 1

JSON_SERVER_PORT = JSON_SERVER_PORT if attempt < 5 else None
IS_JSON_SERVER_RUNNING = False


def _start_json_server() -> subprocess.Popen:
    api_server = Path(__file__).parent / "api_server.py"
    process = subprocess.Popen(  # nosec, test context and trusted env
        [
            "fastapi",
            "run",
            str(api_server.absolute()),
            f"--port={JSON_SERVER_PORT}",
        ]
    )
    time.sleep(3)
    return process


@pytest.fixture(scope="session")
def json_server():
    global IS_JSON_SERVER_RUNNING
    if JSON_SERVER_PORT is not None:
        IS_JSON_SERVER_RUNNING = True
        process = _start_json_server()
        yield
        process.kill()
        process.wait()
    IS_JSON_SERVER_RUNNING = False
