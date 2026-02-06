# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os
import shutil
import stat
import sysconfig
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, List, Union
from unittest.mock import patch

import pytest
from _pytest.fixtures import FixtureRequest

from pyagentspec.llms import VllmConfig

CONFIGS_DIR = Path(os.path.dirname(__file__)) / "agentspec_configs"

SKIP_LLM_TESTS_ENV_VAR = "SKIP_LLM_TESTS"


def should_skip_llm_test() -> bool:
    return SKIP_LLM_TESTS_ENV_VAR in os.environ


LLM_MOCKED_METHODS = [
    "pyagentspec.llms.vllmconfig.VllmConfig.__init__",
    "pyagentspec.llms.ocigenaiconfig.OciGenAiConfig.__init__",
    "pyagentspec.llms.openaicompatibleconfig.OpenAiCompatibleConfig.__init__",
]


@pytest.fixture(scope="session", autouse=True)
def skip_test_fixture():
    """
    When SKIP_LLM_TESTS=1, any attempt to build/use an LLM config will skip the test.
    Identical logic to wayflowcore, adapted for pyagentspec.
    """

    def skip_callable(*args, **kwargs):
        pytest.skip("LLM called, skipping test")

    patches = []
    if should_skip_llm_test():
        for method_name in LLM_MOCKED_METHODS:
            p = patch(method_name, side_effect=skip_callable)
            p.start()
            patches.append(p)

    yield  # run the tests

    for p in patches:
        p.stop()


def read_agentspec_config_file(filename: str) -> str:
    with open(str(CONFIGS_DIR / filename), "r") as file:
        return file.read()


@pytest.fixture
def example_serialized_swarm() -> str:
    return read_agentspec_config_file("example_serialized_swarm.yaml")


@pytest.fixture
def example_serialized_llm_node() -> str:
    return read_agentspec_config_file("example_serialized_llm_node.yaml")


@pytest.fixture
def example_serialized_flow() -> str:
    return read_agentspec_config_file("example_serialized_flow.yaml")


@pytest.fixture
def example_serialized_flow_executing_agent() -> str:
    return read_agentspec_config_file("example_serialized_flow_executing_agent.yaml")


@pytest.fixture
def example_serialized_flow_with_properties() -> str:
    return read_agentspec_config_file("example_serialized_flow_with_properties.yaml")


@pytest.fixture
def default_llm_config() -> VllmConfig:
    llama_endpoint = os.environ.get("LLAMA_API_URL")
    if not llama_endpoint:
        if should_skip_llm_test():
            pytest.skip(
                "Skipping LLM-dependent test: LLAMA_API_URL is not set and SKIP_LLM_TESTS is enabled"
            )
        pytest.fail("LLAMA_API_URL is not set in the environment")
    return VllmConfig(
        name="Llama 3.1 8B instruct",
        url=llama_endpoint,
        model_id="meta-llama/Meta-Llama-3.1-8B-Instruct",
    )


class TestError(Exception):
    """TestError

    The base exception from which all exceptions raised by test
    will inherit.
    """


class TestOSError(OSError, TestError):
    """Exception raised for I/O related error."""


def check_file_permissions(path: Any) -> None:
    """Check that the permissions on a file are rw only for the user,
    and rwx user-only for directories.
    """

    if os.path.isdir(path):
        st_mode = os.stat(path).st_mode
        # Owner has rwx access
        assert st_mode & stat.S_IRWXU
        # everyone else has no access
        assert not (st_mode & (stat.S_IRWXG | stat.S_IRWXO))
    elif os.path.exists(path):
        st_mode = os.stat(path).st_mode
        # Owner has rw access
        assert st_mode & (stat.S_IRUSR | stat.S_IWUSR)
        # everyone else has no access and user does not have x access
        assert not (st_mode & (stat.S_IRWXG | stat.S_IRWXO))


@pytest.fixture(scope="session")
def session_tmp_path(tmp_path_factory):
    """Session-scoped temp path"""
    dirpath = tmp_path_factory.mktemp("tmp")
    yield str(dirpath)
    shutil.rmtree(dirpath)


def get_directory_allowlist_write(tmp_path: str, session_tmp_path: str) -> List[Union[str, Path]]:
    std_paths = sysconfig.get_paths()
    return [
        std_paths.get("purelib"),  # Allow packages to r/w their pycache
        std_paths.get("platlib"),
        tmp_path,
        session_tmp_path,
        "/dev/null",
    ]


def get_directory_allowlist_read(tmp_path: str, session_tmp_path: str) -> List[Union[str, Path]]:
    try:
        # Crew AI sometimes attempts to read in some folders, we need to take that into account
        from crewai.cli.shared.token_manager import TokenManager

        crewai_read_dirs = [
            TokenManager.get_secure_storage_path(),
        ]
    except ImportError:
        crewai_read_dirs = []
    return (
        get_directory_allowlist_write(tmp_path, session_tmp_path)
        + [
            CONFIGS_DIR,
            # Docs path
            Path(os.path.dirname(__file__)).parent.parent / "docs" / "pyagentspec" / "source",
            # Accessed by pandas, dependency of wayflowcore
            Path("/usr/share/zoneinfo/UTC"),
            # Used in docstring tests
            Path(os.path.dirname(__file__)).parent / "src" / "pyagentspec",
            Path("~/.pdbrc").expanduser(),
            Path(os.path.dirname(__file__)).parent / ".pdbrc",
            Path(os.path.dirname(__file__)) / ".pdbrc",
            Path("/etc/os-release"),
            Path("~/.oci/").expanduser(),
        ]
        + crewai_read_dirs
    )


def check_allowed_filewrite(
    path: Union[str, Path], tmp_path: str, session_tmp_path: str, mode: str
) -> None:
    path = os.path.abspath(path)
    if mode == "r" or mode == "rb":
        assert any(
            [
                Path(dir) in Path(path).parents or Path(dir) == Path(path)
                for dir in get_directory_allowlist_read(
                    tmp_path=tmp_path, session_tmp_path=session_tmp_path
                )
            ]
        ), f"Reading outside of allowed directories! {path}"
    else:
        assert any(
            [
                Path(dir) in Path(path).parents or Path(dir) == Path(path)
                for dir in get_directory_allowlist_write(
                    tmp_path=tmp_path, session_tmp_path=session_tmp_path
                )
            ]
        ), f"Writing outside of allowed directories! {path}"


@contextmanager
def limit_filewrites(
    monkeypatch: Any, tmp_path: str, session_tmp_path: str, allowed_access_enabled: bool = True
) -> Iterator[bool]:
    import builtins

    _open = builtins.open

    def patched_open(name, *args, **kwargs):
        if not allowed_access_enabled:
            raise IOError("File is being accessed when it shouldn't have")
        # Sometimes, a process might write in a local path named with a number
        # For instance:
        # /proc/stat/8274921/ <--- correct
        # /proc/stat/8103810/ <--- correct
        # 8                   <--- incorrect
        # /proc/stat/6183016/ <--- correct
        # not sure why this happens, but it will fail test_selection in test_cache_writes
        if not isinstance(name, int):
            # Mode can be either in *args or **kwargs, if it's not, the default is "r"
            mode = "w" if "w" in args else "r"
            mode = kwargs.get("mode", mode)
            check_allowed_filewrite(
                name, tmp_path=tmp_path, session_tmp_path=session_tmp_path, mode=mode
            )
        return _open(name, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(builtins, "open", patched_open)
        yield True


@pytest.fixture(scope="function", autouse=True)
def guard_filewrites(
    request: FixtureRequest, monkeypatch: Any, tmp_path: str, session_tmp_path: str
) -> Iterator[bool]:
    """Fixture which raises an exception if the filesystem is accessed
    outside of a limited set of allowed directories (pycache, automlx
    cache dir, ...)
    """
    if request.node.get_closest_marker("skip_guard_filewrites"):
        yield True
    else:
        with limit_filewrites(
            monkeypatch,
            tmp_path=tmp_path,
            session_tmp_path=session_tmp_path,
            allowed_access_enabled=True,
        ) as x:
            yield x


@pytest.fixture(scope="function")
def guard_all_filewrites(monkeypatch: Any, tmp_path: str, session_tmp_path: str) -> Iterator[bool]:
    """Fixture which raises an exception if the filesystem is accessed."""
    with limit_filewrites(
        monkeypatch,
        tmp_path=tmp_path,
        session_tmp_path=session_tmp_path,
        allowed_access_enabled=False,
    ) as x:
        yield x


@contextmanager
def suppress_network(
    monkeypatch: Any, tmp_path: str, allowed_access_enabled: bool = True
) -> Iterator[bool]:
    """
    Context manager which raises an exception if network connection is requested.

    This is useful for detecting unit tests that inadvertently make network calls.
    We however allow localhost/filedescriptor sockets as they are needed by libraries
    to escape the Python Global Interpreter Lock.

    Parameters
    ----------
    monkeypatch : Any
        The monkeypatch
    tmp_path : str
        The path of the tmp directory used by pytest
    allowed_access_enabled : bool, default=True
        If true, will check that network access is on one of the allowed
        files. If false, all network access is suppressed
    """
    import socket

    orig_fn = socket.socket.connect

    def guard_connect(*args: Any) -> Any:
        """
        Mock the connect function of the socket module.

        The arguments are self (socket) and the address. The address can be a
        tuple (ip, port) or a filedescriptor string. We allow any filedescriptor
        and only the localhost socket.
        """
        assert allowed_access_enabled, "Code is accessing network when it shouldn't have"
        addr = args[1]
        if isinstance(addr, str) or addr[0] == "127.0.0.1":
            check_allowed_filewrite(addr, tmp_path=tmp_path, mode="w")
            return orig_fn(*args)
        # We must raise OSError (not Exception) similar to that raised
        # by socket.connect to support libraries that rely on this
        # behavior (e.g. Ray) for exception handling
        raise TestOSError(f"Network is being accessed at address {addr} of type {type(addr)}")

    with monkeypatch.context() as m:
        m.setattr(socket.socket, "connect", guard_connect)
        yield True


@pytest.fixture(scope="function")
def guard_network(monkeypatch: Any, tmp_path: str) -> Iterator[bool]:
    """
    Fixture which raises an exception if the network is accessed. It
    will not raise an exception for localhost, use guard_all_network_access
    to catch all network access

    Unit tests should not touch the network so this fixture helps guard
    against accidental network use.
    """
    with suppress_network(monkeypatch, tmp_path=tmp_path, allowed_access_enabled=True) as x:
        yield x


@pytest.fixture(scope="function")
def guard_all_network_access(monkeypatch: Any, tmp_path: str) -> Iterator[bool]:
    """Fixture which raises an exception if the network is accessed.

    Unit tests should not touch the network so this fixture helps guard
    against accidental network use.
    """
    with suppress_network(monkeypatch, tmp_path=tmp_path, allowed_access_enabled=False) as x:
        yield x
