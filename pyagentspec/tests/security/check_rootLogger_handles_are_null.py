# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""
If somewhere our code initializes a StreamHandler this test will alert you to it.
It could be due to a dependency or your own code in the pyagentspec package.
The test will also catch all import failures due to syntax errors.

The implications are that applications that import pyagentspec cannot send logging info anymore.
As the resident RootLogger suppresses all downstream logging initialization via logging.basicConfig.
"""

import logging
import os

# Must not import packages outside the Python Standard Library here


def listloggers():
    rootlogger = logging.getLogger()
    print(rootlogger)
    for h in rootlogger.handlers:
        print("     %s" % h)

    for nm, lgr in logging.Logger.manager.loggerDict.items():
        print("+ [%-20s] %s " % (nm, lgr))
        if not isinstance(lgr, logging.PlaceHolder):
            for h in lgr.handlers:
                print("     %s" % h)


def import_pyagentspec():
    from pyagentspec.agent import Agent
    from pyagentspec.llms import LlmGenerationConfig, VllmConfig
    from pyagentspec.property import StringProperty
    from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
    from pyagentspec.tools import ClientTool, RemoteTool, ServerTool

    serializer = AgentSpecSerializer()
    deserializer = AgentSpecDeserializer()
    llama_endpoint = os.environ.get("LLAMA_API_URL")
    if not llama_endpoint:
        raise Exception("LLAMA_API_URL is not set in the environment")
    llm_config = VllmConfig(
        name="llm",
        url=llama_endpoint,
        model_id="meta-llama/Meta-Llama-3.1-8B-Instruct",
        default_generation_parameters=LlmGenerationConfig(temperature=0.5),
    )
    agent = Agent(
        id="abc123",
        name="default_agent",
        llm_config=llm_config,
        system_prompt="You are a great agent. You are talking to {{username}}. Be kind.",
        tools=[
            ClientTool(
                name="do_nothing",
                description="do nothing",
                inputs=[StringProperty(title="x")],
                outputs=[StringProperty(title="x")],
            ),
            ServerTool(
                name="do_nothing 2",
                description="do nothing again",
                inputs=[StringProperty(title="x")],
                outputs=[StringProperty(title="x")],
            ),
            RemoteTool(
                id="tool3",
                name="do_nothing 3",
                description="do nothing another time",
                inputs=[StringProperty(title="x")],
                outputs=[StringProperty(title="x")],
                url="my.awesome.endpoint",
                http_method="GET",
                api_spec_uri=None,
                data={"x": "{{x}}", "b": "c"},
                query_params={"d": 1, "e": "c"},
            ),
        ],
        inputs=[StringProperty(title="username")],
    )
    serialized_agent = serializer.to_yaml(agent)
    _ = deserializer.from_yaml(serialized_agent)

    from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
    from pyagentspec.flows.flow import Flow
    from pyagentspec.flows.nodes import (
        ApiNode,
        EndNode,
        LlmNode,
        StartNode,
    )
    from pyagentspec.llms import OciGenAiConfig
    from pyagentspec.llms.ociclientconfig import OciClientConfigWithSecurityToken

    oci_llm_config = OciGenAiConfig(
        id="oci genai llm",
        name="oci genai llm",
        model_id="model.id",
        compartment_id="compartment.id",
        client_config=OciClientConfigWithSecurityToken(
            name="oci client",
            service_endpoint="service.endpoint",
            auth_profile="user_profile",
            auth_file_location="auth/file/location.txt",
        ),
        default_generation_parameters=LlmGenerationConfig(temperature=0.6),
    )

    start_node = StartNode(
        name="start",
        inputs=[StringProperty(title="username"), StringProperty(title="user_input")],
    )
    llm_node = LlmNode(
        name="prompt",
        llm_config=oci_llm_config,
        prompt_template="{{username}} is asking: {{user_input}}",
        outputs=[StringProperty(title="llm_output")],
    )
    api_node = ApiNode(
        id="api node",
        name="api call that does nothing",
        inputs=[StringProperty(title="input")],
        outputs=[StringProperty(title="output")],
        url="my.awesome.endpoint",
        http_method="POST",
        data={"input": "{{input}}"},
    )
    end_node = EndNode(name="end", outputs=[StringProperty(title="llm_output")])
    control_flow_edges = [
        ControlFlowEdge(
            name="cfe1",
            from_node=start_node,
            to_node=llm_node,
        ),
        ControlFlowEdge(
            name="cfe2",
            from_node=llm_node,
            to_node=api_node,
        ),
        ControlFlowEdge(
            name="cfe3",
            from_node=api_node,
            to_node=end_node,
        ),
    ]
    data_flow_edges = [
        DataFlowEdge(
            name="dfe1",
            source_node=start_node,
            source_output="username",
            destination_node=llm_node,
            destination_input="username",
        ),
        DataFlowEdge(
            name="dfe2",
            source_node=start_node,
            source_output="user_input",
            destination_node=llm_node,
            destination_input="user_input",
        ),
        DataFlowEdge(
            name="dfe3",
            source_node=llm_node,
            source_output="llm_output",
            destination_node=api_node,
            destination_input="input",
        ),
        DataFlowEdge(
            name="dfe4",
            source_node=api_node,
            source_output="output",
            destination_node=end_node,
            destination_input="llm_output",
        ),
    ]
    flow = Flow(
        start_node=start_node,
        nodes=[start_node, llm_node, api_node, end_node],
        control_flow_connections=control_flow_edges,
        data_flow_connections=data_flow_edges,
        name="default_flow",
        id="321cba",
    )
    serialized_flow = serializer.to_yaml(flow)
    _ = deserializer.from_yaml(serialized_flow)


def test_for_empty_rootlogger():

    rootlogger = logging.getLogger()
    if len(rootlogger.handlers) != 0:
        raise Exception(
            "rootLoggers must be empty. This file should only have PSL packages in its header."
            f"{rootlogger.handlers}"
        )
    import_pyagentspec()
    if len(rootlogger.handlers) != 0:
        listloggers()
        raise Exception(
            "Following rootLoggers have been initialized on import of pyagentspec package:\n"
            f"{rootlogger.handlers}"
        )


if __name__ == "__main__":
    test_for_empty_rootlogger()
