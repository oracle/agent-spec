# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os
import signal
import socket
import ssl
import subprocess  # nosec B404
import sys
import threading
import time
from collections import deque
from contextlib import closing
from typing import Optional, Tuple

import httpx
import pytest


class LogTee:
    def __init__(self, stream, prefix: str, max_lines: int = 400):
        self.stream = stream
        self.prefix = prefix
        self.lines = deque(maxlen=max_lines)
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self._stop.set()
        self.thread.join(timeout=2)

    def _run(self):
        for line in iter(self.stream.readline, ""):
            if self._stop.is_set():
                break
            line = line.rstrip("\n")
            self.lines.append(line)
            # forward to CI log immediately
            print(f"{self.prefix}{line}", file=sys.stdout, flush=True)

    def dump(self) -> str:
        return "\n".join(self.lines)


def terminate_process_tree(process: subprocess.Popen, timeout: float = 5.0) -> None:
    """Best-effort, cross-platform termination with escalation and stdout close."""
    try:
        if process.poll() is not None:
            return  # already exited

        if os.name == "posix":
            # Prefer group termination on POSIX if we started a new session
            try:
                pgid = os.getpgid(process.pid)
                try:
                    os.killpg(pgid, signal.SIGTERM)
                except OSError:
                    # Fall back to terminating the single process
                    try:
                        process.terminate()
                    except OSError:
                        pass
            except OSError:
                # If we can't get pgid, try terminating the single process
                try:
                    process.terminate()
                except OSError:
                    pass
        else:
            # Windows or other: terminate the single process
            try:
                process.terminate()
            except OSError:
                pass

        # Give it a moment to exit cleanly
        try:
            process.wait(timeout=timeout)
            return
        except subprocess.TimeoutExpired:
            pass

        # Forceful: SIGKILL the group (POSIX), otherwise kill the process
        if os.name == "posix":
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except OSError:
                try:
                    process.kill()
                except OSError:
                    pass
        else:
            try:
                process.kill()
            except OSError:
                pass

        # Ensure it is gone
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass
    finally:
        # Close stdout to avoid ResourceWarning if we used a PIPE
        try:
            if getattr(process, "stdout", None) and not process.stdout.closed:
                process.stdout.close()
        except (OSError, ValueError):
            pass


def _check_server_is_up(
    url: str,
    client_key_path: Optional[str] = None,
    client_cert_path: Optional[str] = None,
    ca_cert_path: Optional[str] = None,
    timeout_s: float = 5.0,
) -> bool:
    verify: ssl.SSLContext | bool = False
    if client_key_path and client_cert_path and ca_cert_path:
        ssl_ctx = ssl.create_default_context(cafile=ca_cert_path)
        ssl_ctx.load_cert_chain(certfile=client_cert_path, keyfile=client_key_path)
        verify = ssl_ctx

    last_exc: Optional[Exception] = None
    deadline = time.time() + timeout_s
    with httpx.Client(verify=verify, timeout=1.0) as client:
        while time.time() < deadline:
            try:
                resp = client.get(url)
                if resp.status_code < 500:
                    return True
            except Exception as e:
                last_exc = e
            time.sleep(0.2)
    if last_exc:
        print(
            f"Server not ready after {timeout_s}s. Last error: {last_exc}",
            file=sys.stderr,
            flush=True,
        )
    return False


def start_uvicorn_server(
    server_file_path: str,
    host: str = "localhost",
    port: Optional[int] = None,
    mode: Optional[str] = None,
    server_key_path: Optional[str] = None,
    server_cert_path: Optional[str] = None,
    ca_cert_path: Optional[str] = None,
    ssl_cert_reqs: Optional[int] = None,  # ssl.CERT_NONE
    client_key_path: Optional[str] = None,
    client_cert_path: Optional[str] = None,
    ready_timeout_s: float = 10.0,
) -> Tuple[subprocess.Popen, str]:
    port = port or get_available_port()
    process_args = [
        "python",
        "-u",  # unbuffered output
        server_file_path,
        "--host",
        host,
        "--port",
        str(port),
    ]
    if mode is not None:
        process_args += ["--mode", mode]
    if ssl_cert_reqs is not None:
        process_args += ["--ssl_cert_reqs", str(ssl_cert_reqs)]
    if server_key_path and server_cert_path and ca_cert_path:  # using https
        process_args.extend(
            [
                "--ssl_keyfile",
                server_key_path,
                "--ssl_certfile",
                server_cert_path,
                "--ssl_ca_certs",
                ca_cert_path,
            ]
        )
        url = f"https://{host}:{port}"
    else:
        url = f"http://{host}:{port}"

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    # Start process with pipes and its own process group so we can kill children
    process = subprocess.Popen(  # nosec B603: controlled args; shell=False;
        process_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # line-buffered
        env=env,
        shell=False,
        start_new_session=True,
    )

    # Tee logs to CI and keep a ring buffer
    if process.stdout is None:
        raise RuntimeError("Failed to capture server stdout")
    tee = LogTee(process.stdout, prefix="[uvicorn] ")
    tee.start()

    try:
        # Poll for readiness or early exit
        start = time.time()
        while time.time() - start < ready_timeout_s:
            rc = process.poll()
            if rc is not None:
                raise RuntimeError(f"Uvicorn exited early with code {rc}.\nLogs:\n{tee.dump()}")

            if _check_server_is_up(
                url, client_key_path, client_cert_path, ca_cert_path, timeout_s=0.5
            ):
                print("Server is up.", flush=True)
                return process, url
            time.sleep(0.2)

        # Timed out
        raise RuntimeError(
            f"Uvicorn server did not start in time ({ready_timeout_s}s).\nLogs so far:\n{tee.dump()}"
        )

    except Exception as e:
        terminate_process_tree(process, timeout=5.0)
        raise e
    finally:
        tee.stop()


def register_server_fixture(
    name: str, url_suffix: str, start_kwargs: dict, deps: tuple[str, ...] = ()
):
    def _fixture(request):
        # Resolve any dependent fixtures by name and merge into kwargs
        resolved = {name: request.getfixturevalue(name) for name in deps}
        kwargs = {**start_kwargs, **resolved}

        process, url = start_uvicorn_server(**kwargs)
        try:
            yield f"{url}/{url_suffix.strip('/')}"
        finally:
            terminate_process_tree(process, timeout=5.0)

    return pytest.fixture(scope="session", name=name)(_fixture)


def get_available_port():
    """Finds an available port to run a server"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]
