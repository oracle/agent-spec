# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os
import random
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from pythonfuzz.main import PythonFuzz

from pyagentspec import Component, Property
from pyagentspec.agent import Agent
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.node import Node
from pyagentspec.flows.nodes import (
    AgentNode,
    ApiNode,
    BranchingNode,
    EndNode,
    FlowNode,
    LlmNode,
    MapNode,
    StartNode,
    ToolNode,
)
from pyagentspec.llms import LlmConfig, LlmGenerationConfig, OciGenAiConfig, VllmConfig
from pyagentspec.llms.ociclientconfig import (
    OciClientConfig,
    OciClientConfigWithApiKey,
    OciClientConfigWithInstancePrincipal,
    OciClientConfigWithResourcePrincipal,
    OciClientConfigWithSecurityToken,
)
from pyagentspec.property import (
    BooleanProperty,
    DictProperty,
    FloatProperty,
    IntegerProperty,
    ListProperty,
    NullProperty,
    StringProperty,
    UnionProperty,
)
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.tools import BuiltinTool, ClientTool, RemoteTool, ServerTool, Tool

fuzz_output_filename = "pyagentspec.result.fuzz.txt"
fuzz_exceptions_output_filename = "pyagentspec.exceptions.fuzz.txt"
exceptions_found = dict()


def create_random_dict_with_str_keys(
    buf: bytes, encoding: str, allow_subdictionaries: bool = True
) -> Dict[str, Any]:
    random_dict = dict()
    num_entries = random.randint(1, 4)
    for entry in range(num_entries):
        selector = random.randint(0, 4)
        if selector == 0:
            value = int.from_bytes(buf, "big")
        elif selector == 1:
            value = float(int.from_bytes(buf, "big"))
        elif selector == 2:
            value = buf.decode(encoding)
        elif selector == 3 and allow_subdictionaries:
            value = create_random_dict_with_str_keys(
                buf=buf, encoding=encoding, allow_subdictionaries=False
            )
        else:
            value = None
        random_dict[bytes(buf[entry % len(buf)]).decode(encoding)] = value
    return random_dict


def create_metadata(
    buf: bytes,
    encoding: str,
) -> Optional[Dict[str, Any]]:
    return (
        create_random_dict_with_str_keys(buf=buf, encoding=encoding)
        if random.randint(0, 1)
        else None
    )


def create_property(
    buf: bytes,
    encoding: str,
    allow_complex_types: bool = True,
) -> Property:
    selector = random.randint(0, 7)
    title = buf.decode(encoding)
    description = buf.decode(encoding) if random.randint(0, 1) else None
    default = buf.decode(encoding) if random.randint(0, 1) else None
    if selector == 0:
        return StringProperty(title=title, description=description, default=default)
    elif selector == 1:
        return BooleanProperty(title=title, description=description, default=default)
    elif selector == 2:
        return IntegerProperty(title=title, description=description, default=default)
    elif selector == 3:
        return FloatProperty(title=title, description=description, default=default)
    elif selector == 4 and allow_complex_types:
        any_of = [create_property(buf=buf, encoding=encoding) for _ in range(random.randint(0, 4))]
        return UnionProperty(title=title, description=description, default=default, any_of=any_of)
    elif selector == 5 and allow_complex_types:
        return ListProperty(
            title=title,
            description=description,
            default=default,
            item_type=create_property(buf=buf, encoding=encoding, allow_complex_types=False),
        )
    elif selector == 6 and allow_complex_types:
        return DictProperty(
            title=title,
            description=description,
            default=default,
            value_type=create_property(buf=buf, encoding=encoding, allow_complex_types=False),
        )
    else:
        return NullProperty(title=title, description=description, default=default)


def create_tool(
    buf: bytes,
    encoding: str,
) -> Tool:
    selector = random.randint(0, 3)
    name = buf.decode(encoding)
    description = buf.decode(encoding)
    metadata = create_metadata(buf=buf, encoding=encoding)
    inputs = [create_property(buf=buf, encoding=encoding) for _ in range(random.randint(0, 4))]
    outputs = [create_property(buf=buf, encoding=encoding) for _ in range(random.randint(0, 4))]
    if selector == 0:
        return ServerTool(
            name=name,
            description=description,
            inputs=inputs,
            outputs=outputs,
            metadata=metadata,
        )
    elif selector == 1:
        return ClientTool(
            name=name,
            description=description,
            inputs=inputs,
            outputs=outputs,
            metadata=metadata,
        )
    elif selector == 2:
        return RemoteTool(
            name=name,
            description=description,
            inputs=inputs,
            outputs=outputs,
            url=buf.decode(encoding),
            http_method=buf.decode(encoding),
            api_spec_uri=buf.decode(encoding) if random.randint(0, 1) else None,
            data=create_random_dict_with_str_keys(buf=buf, encoding=encoding),
            query_params=create_random_dict_with_str_keys(buf=buf, encoding=encoding),
            headers=create_random_dict_with_str_keys(buf=buf, encoding=encoding),
            metadata=metadata,
        )
    else:
        return BuiltinTool(
            name=name,
            description=description,
            inputs=inputs,
            outputs=outputs,
            metadata=metadata,
            tool_type=buf.decode(encoding),
            configuration=create_random_dict_with_str_keys(buf=buf, encoding=encoding),
            executor_name=buf.decode(encoding),
            tool_version=buf.decode(encoding),
        )


def create_oci_client_config(
    buf: bytes,
    encoding: str,
) -> OciClientConfig:
    selector = random.randint(0, 4)
    description = buf.decode(encoding) if random.randint(0, 1) else None
    metadata = create_metadata(buf=buf, encoding=encoding)
    if selector == 0:
        return OciClientConfigWithSecurityToken(
            name=buf.decode(encoding),
            description=description,
            metadata=metadata,
            service_endpoint=buf.decode(encoding),
            auth_profile=buf.decode(encoding),
            auth_file_location=buf.decode(encoding),
        )
    elif selector == 1:
        return OciClientConfigWithInstancePrincipal(
            name=buf.decode(encoding),
            description=description,
            metadata=metadata,
            service_endpoint=buf.decode(encoding),
        )
    elif selector == 2:
        return OciClientConfigWithResourcePrincipal(
            name=buf.decode(encoding),
            description=description,
            metadata=metadata,
            service_endpoint=buf.decode(encoding),
        )
    else:
        return OciClientConfigWithApiKey(
            name=buf.decode(encoding),
            description=description,
            metadata=metadata,
            service_endpoint=buf.decode(encoding),
            auth_profile=buf.decode(encoding),
            auth_file_location=buf.decode(encoding),
        )


def create_llm(
    buf: bytes,
    encoding: str,
) -> LlmConfig:
    metadata = create_metadata(buf=buf, encoding=encoding)
    description = buf.decode(encoding) if random.randint(0, 1) else None
    generation_parameters = None
    if random.randint(0, 1):
        generation_parameters = LlmGenerationConfig(
            max_tokens=int.from_bytes(buf, "big") if random.randint(0, 1) else None,
            temperature=float(int.from_bytes(buf, "big")) if random.randint(0, 1) else None,
            top_p=float(int.from_bytes(buf, "big")) if random.randint(0, 1) else None,
        )
    if random.randint(0, 1):
        return VllmConfig(
            name=buf.decode(encoding),
            description=description,
            url=buf.decode(encoding),
            model_id=buf.decode(encoding),
            default_generation_parameters=generation_parameters,
            metadata=metadata,
        )
    else:
        return OciGenAiConfig(
            name=buf.decode(encoding),
            description=description,
            model_id=buf.decode(encoding),
            compartment_id=buf.decode(encoding),
            client_config=create_oci_client_config(buf=buf, encoding=encoding),
            metadata=metadata,
        )


def create_node(
    buf: bytes,
    encoding: str,
    allow_subflows: bool = True,
    allow_subagents: bool = True,
) -> Node:
    metadata = create_metadata(buf=buf, encoding=encoding)
    name = buf.decode(encoding)
    description = buf.decode(encoding)
    inputs = [create_property(buf=buf, encoding=encoding) for _ in range(random.randint(0, 4))]
    outputs = [create_property(buf=buf, encoding=encoding) for _ in range(random.randint(0, 4))]
    branches = [buf.decode(encoding) for _ in range(random.randint(0, 4))]
    selector = random.randint(0, 8)
    if selector == 0:
        return StartNode(
            name=name,
            description=description,
            inputs=inputs,
            outputs=outputs,
            branches=branches,
            metadata=metadata,
        )
    elif selector == 1:
        return ToolNode(
            name=name,
            description=description,
            tool=create_tool(buf=buf, encoding=encoding),
            inputs=inputs,
            outputs=outputs,
            branches=branches,
            metadata=metadata,
        )
    elif selector == 2 and allow_subflows:
        return FlowNode(
            name=name,
            description=description,
            flow=create_flow(
                buf=buf,
                encoding=encoding,
                allow_subflows=allow_subflows,
                allow_subagents=allow_subagents,
            ),
            inputs=inputs,
            outputs=outputs,
            branches=branches,
            metadata=metadata,
        )
    elif selector == 3 and allow_subagents:
        return AgentNode(
            name=name,
            description=description,
            agent=create_agent(
                buf=buf,
                encoding=encoding,
                allow_subflows=allow_subflows,
                allow_subagents=allow_subagents,
            ),
            inputs=inputs,
            outputs=outputs,
            branches=branches,
            metadata=metadata,
        )
    elif selector == 4:
        return LlmNode(
            name=name,
            description=description,
            inputs=inputs,
            outputs=outputs,
            llm_config=create_llm(buf=buf, encoding=encoding),
            prompt_template=buf.decode(encoding),
            branches=branches,
            metadata=metadata,
        )
    elif selector == 5:
        return BranchingNode(
            name=name,
            description=description,
            inputs=inputs,
            outputs=outputs,
            mapping=create_random_dict_with_str_keys(
                buf=buf, encoding=encoding, allow_subdictionaries=False
            ),
            branches=branches,
            metadata=metadata,
        )
    elif selector == 6:
        return ApiNode(
            name=name,
            description=description,
            url=buf.decode(encoding),
            http_method=buf.decode(encoding),
            api_spec_uri=buf.decode(encoding) if random.randint(0, 1) else None,
            data=create_random_dict_with_str_keys(buf=buf, encoding=encoding),
            query_params=create_random_dict_with_str_keys(buf=buf, encoding=encoding),
            headers=create_random_dict_with_str_keys(buf=buf, encoding=encoding),
            inputs=inputs,
            outputs=outputs,
            branches=branches,
            metadata=metadata,
        )
    elif selector == 7:
        return BranchingNode(
            name=name,
            description=description,
            inputs=inputs,
            outputs=outputs,
            mapping=create_random_dict_with_str_keys(
                buf=buf, encoding=encoding, allow_subdictionaries=False
            ),
            branches=branches,
            metadata=metadata,
        )
    else:
        return EndNode(
            name=name,
            description=description,
            inputs=inputs,
            outputs=outputs,
            branches=branches,
            metadata=metadata,
        )


def create_flow(
    buf: bytes,
    encoding: str,
    allow_subflows: bool = True,
    allow_subagents: bool = True,
) -> Flow:
    metadata = create_metadata(buf=buf, encoding=encoding)
    description = buf.decode(encoding) if random.randint(0, 1) else None
    nodes = [
        create_node(
            buf=buf,
            encoding=encoding,
            allow_subflows=allow_subflows,
            allow_subagents=allow_subagents,
        )
        for _ in range(random.randint(0, 10))
    ]
    control_flow_connections = [
        ControlFlowEdge(
            name=buf.decode(encoding),
            description=description,
            metadata=metadata,
            from_node=random.choice(nodes),
            from_branch=buf.decode(encoding) if random.randint(0, 1) else None,
            to_node=random.choice(nodes),
        )
    ]
    data_flow_connections = (
        [
            DataFlowEdge(
                name=buf.decode(encoding),
                description=description,
                metadata=metadata,
                source_node=random.choice(nodes),
                source_output=buf.decode(encoding),
                destination_node=random.choice(nodes),
                destination_input=buf.decode(encoding),
            )
        ]
        if random.randint(0, 1)
        else None
    )
    return Flow(
        name=buf.decode(encoding),
        description=description,
        start_node=random.choice(nodes),
        nodes=nodes,
        control_flow_connections=control_flow_connections,
        data_flow_connections=data_flow_connections,
        metadata=metadata,
    )


def create_agent(
    buf: bytes,
    encoding: str,
    allow_subagents: bool = True,
    allow_subflows: bool = True,
) -> Agent:
    flows = (
        [create_flow(buf=buf, encoding=encoding) for _ in range(random.randint(0, 4))]
        if allow_subflows
        else []
    )
    agents = (
        [create_agent(buf=buf, encoding=encoding) for _ in range(random.randint(0, 4))]
        if allow_subagents
        else []
    )
    description = buf.decode(encoding) if random.randint(0, 1) else None
    tools = [create_tool(buf=buf, encoding=encoding) for _ in range(random.randint(0, 4))]
    metadata = create_metadata(buf=buf, encoding=encoding)
    return Agent(
        name=buf.decode(encoding),
        description=description,
        llm=create_llm(buf=buf, encoding=encoding),
        flows=flows,
        agents=agents,
        tools=tools,
        system_prompt=buf.decode(encoding),
        metadata=metadata,
    )


def serialize_and_deserialize_component(component: Component) -> None:
    serializer = AgentSpecSerializer()
    serialized_component = serializer.to_yaml(component=component)
    deserializer = AgentSpecDeserializer()
    _ = deserializer.from_yaml(serialized_component)


def test_llm(buf: bytes, encoding: str):
    serialize_and_deserialize_component(create_llm(buf=buf, encoding=encoding))


def test_node(buf: bytes, encoding: str):
    serialize_and_deserialize_component(create_node(buf=buf, encoding=encoding))


def test_tool(buf: bytes, encoding: str):
    serialize_and_deserialize_component(create_tool(buf=buf, encoding=encoding))


def test_flow(buf: bytes, encoding: str):
    serialize_and_deserialize_component(create_flow(buf=buf, encoding=encoding))


def test_agent(buf: bytes, encoding: str):
    serialize_and_deserialize_component(create_agent(buf=buf, encoding=encoding))


def test_deserialize_existing_yaml(buf: bytes, encoding: str):
    configs_dir = Path(os.path.dirname(__file__)).parent / "tests" / "agentspec_configs"
    valid_yaml_files = [
        dir_name
        for dir_name in os.listdir(configs_dir)
        if dir_name.endswith(".yaml") or dir_name.endswith(".yml")
    ]
    with open(configs_dir / random.choice(valid_yaml_files)) as config_file:
        serialized_component = config_file.read()
    _ = AgentSpecDeserializer().from_yaml(yaml_content=serialized_component)


@PythonFuzz
def fuzz(buf):

    random.seed()
    encoding = "utf-8"
    test_functions = [
        test_llm,
        test_flow,
        test_node,
        test_agent,
        test_tool,
        test_deserialize_existing_yaml,
    ]

    # We proceed with a fuzz test only if the buffer can be correctly decoded
    try:
        _ = buf.decode(encoding)
        buffer_can_be_decoded = True
    except UnicodeDecodeError:
        buffer_can_be_decoded = False

    if buffer_can_be_decoded:
        try:

            test_function = random.choice(test_functions)
            test_function(buf, encoding)

        except Exception as e:

            # The way we store exceptions needs to take into account 2 things
            # - The code might raise many exceptions, so result files can grow bigger and bigger
            # - The code can be interrupted at any time, even in the middle of a write
            # To take into account these two concerns, we split the data we store in two parts
            # - an exception file where we store unique exception (verbose) information, including an identifier
            # - a results file where we record only the identifier of the exception raised
            exception_str = str(e)
            if exception_str not in exceptions_found:
                stacktrace = str(traceback.format_exc())
                exceptions_found[exception_str] = len(exceptions_found)
                with open(fuzz_exceptions_output_filename, "a") as outfile:
                    # Strings can contain new lines that are hard to remove, so we use another format
                    # Elements are separated by a line made of four colons: "::::"
                    for s in [exceptions_found[exception_str], type(e), exception_str, stacktrace]:
                        print(s, end="\n::::\n", file=outfile)
            exception_idx = exceptions_found[exception_str]
            with open(fuzz_output_filename, "a") as outfile:
                print(f"{exception_idx}", file=outfile)


if __name__ == "__main__":
    if os.path.isfile(fuzz_output_filename):
        os.remove(fuzz_output_filename)
    if os.path.isfile(fuzz_exceptions_output_filename):
        os.remove(fuzz_exceptions_output_filename)
    fuzz()
