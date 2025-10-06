# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.
# mypy: ignore-errors

# .. define-properties:
from pyagentspec.property import Property

user_request_property = Property(
    json_schema=dict(
        title="user_request",
        type="string",
    )
)

code_property = Property(
    json_schema=dict(
        title="code",
        type="string",
        default="",
    )
)

review_property = Property(
    json_schema=dict(
        title="review",
        type="string",
        default="",
    )
)

is_code_ready_property = Property(
    json_schema=dict(
        title="is_code_ready",
        type="boolean",
        default=False,
    )
)
# .. end-define-properties:

from pyagentspec.llms.vllmconfig import VllmConfig

llm_config = VllmConfig(
    name="Vllm model",
    url="vllm_url",
    model_id="model_id",
)


# .. define-start-end-nodes:
from pyagentspec.flows.nodes import EndNode, StartNode

start_node = StartNode(
    name="Start node",
    inputs=[user_request_property],
)

end_node = EndNode(
    name="End node",
    outputs=[code_property],
)
# .. end-define-start-end-nodes:

# .. define-generate-review-nodes:
from pyagentspec.flows.nodes import LlmNode

generate_code_node = LlmNode(
    name="Generate code node",
    prompt_template="""You are a great code python software engineer.

    Please write the python code to satisfy the following user request: "{{user_request}}".

    You previously generated the following snippet of code:
    ```
    {{code}}
    ```
    Take inspiration from the snippet of code.

    The code reviewer gave the following feedback:
    {{review}}
    Take also into account the comments in the review

    Write only the python code.
    """,
    llm_config=llm_config,
    inputs=[user_request_property, code_property, review_property],
    outputs=[code_property],
)

review_code_node = LlmNode(
    name="Review code node",
    prompt_template="""You are a great code python software engineer, and a highly skilled code reviewer.
    Please review the following snippet of python code:
    ```
    {{code}}
    ```
    """,
    llm_config=llm_config,
    inputs=[code_property],
    outputs=[review_property],
)
# .. end-define-generate-review-nodes:

# .. define-branching-nodes:
from pyagentspec.flows.nodes import BranchingNode, LlmNode

is_code_ready_decision_node = LlmNode(
    name="Check if code is ready node",
    prompt_template="""You are a software engineer with 20 years of experience. You have to take a decision.
    Based on the following code review, do you think that the code is ready to be deployed?
    ```
    {{review}}
    ```
    Please answer only with `yes` or `no`.
    """,
    llm_config=llm_config,
    inputs=[review_property],
    outputs=[is_code_ready_property],
)

is_code_ready_branching_node = BranchingNode(
    name="Is code ready branching node",
    mapping={
        "yes": "yes",
        "no": "no",
    },
    inputs=[is_code_ready_property],
    outputs=[],
)
# .. end-define-branching-nodes:

# .. define-control-edges:
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge

control_flow_edges = [
    ControlFlowEdge(
        name="start_to_generate_code_control_edge",
        from_node=start_node,
        to_node=generate_code_node,
    ),
    ControlFlowEdge(
        name="generate_code_to_review_control_edge",
        from_node=generate_code_node,
        to_node=review_code_node,
    ),
    ControlFlowEdge(
        name="review_to_is_code_ready_decision_control_edge",
        from_node=review_code_node,
        to_node=is_code_ready_decision_node,
    ),
    ControlFlowEdge(
        name="is_code_ready_decision_to_is_code_ready_branching_control_edge",
        from_node=is_code_ready_decision_node,
        to_node=is_code_ready_branching_node,
    ),
    ControlFlowEdge(
        name="is_code_ready_branching_to_end_control_edge",
        from_node=is_code_ready_branching_node,
        from_branch="yes",
        to_node=end_node,
    ),
    ControlFlowEdge(
        name="is_code_ready_branching_to_generate_code_control_edge",
        from_node=is_code_ready_branching_node,
        from_branch="no",
        to_node=generate_code_node,
    ),
]

# .. end-define-control-edges:

# .. define-data-edges:
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge

data_flow_edges = [
    DataFlowEdge(
        name="start_to_generate_code_user_request_data_edge",
        source_node=start_node,
        source_output="user_request",
        destination_node=generate_code_node,
        destination_input="user_request",
    ),
    DataFlowEdge(
        name="generate_code_to_end_code_data_edge",
        source_node=generate_code_node,
        source_output="code",
        destination_node=end_node,
        destination_input="code",
    ),
    DataFlowEdge(
        name="generate_code_to_generate_code_code_data_edge",
        source_node=generate_code_node,
        source_output="code",
        destination_node=generate_code_node,
        destination_input="code",
    ),
    DataFlowEdge(
        name="generate_code_to_review_code_data_edge",
        source_node=generate_code_node,
        source_output="code",
        destination_node=review_code_node,
        destination_input="code",
    ),
    DataFlowEdge(
        name="review_code_to_generate_code_review_data_edge",
        source_node=review_code_node,
        source_output="review",
        destination_node=generate_code_node,
        destination_input="review",
    ),
    DataFlowEdge(
        name="review_code_to_is_code_ready_review_data_edge",
        source_node=review_code_node,
        source_output="review",
        destination_node=is_code_ready_decision_node,
        destination_input="review",
    ),
    DataFlowEdge(
        name="review_code_to_is_code_ready_flag_data_edge",
        source_node=is_code_ready_decision_node,
        source_output="is_code_ready",
        destination_node=is_code_ready_branching_node,
        destination_input="is_code_ready",
    ),
]

# .. end-define-data-edges:

# .. define-flow:
from pyagentspec.flows.flow import Flow

final_assistant_flow = Flow(
    name="Generate code and review flow",
    description="Flow that given a user request, generates a python code snippet to satisfy it and passes it through a code review before returning it",
    start_node=start_node,
    nodes=[
        start_node,
        generate_code_node,
        review_code_node,
        is_code_ready_decision_node,
        is_code_ready_branching_node,
        end_node,
    ],
    control_flow_connections=control_flow_edges,
    data_flow_connections=data_flow_edges,
)

# .. end-define-flow:

# .. export-serialization:
from pyagentspec.serialization import AgentSpecSerializer

if __name__ == "__main__":
    serialized_agent = AgentSpecSerializer().to_json(final_assistant_flow)
    print(serialized_agent)

# .. end-export-serialization:


# .. full-code:
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import BranchingNode, EndNode, LlmNode, StartNode
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.property import Property
from pyagentspec.serialization import AgentSpecSerializer

user_request_property = Property(
    json_schema=dict(
        title="user_request",
        type="string",
    )
)

code_property = Property(
    json_schema=dict(
        title="code",
        type="string",
        default="",
    )
)

review_property = Property(
    json_schema=dict(
        title="review",
        type="string",
        default="",
    )
)

is_code_ready_property = Property(
    json_schema=dict(
        title="is_code_ready",
        type="boolean",
        default=False,
    )
)


llm_config = VllmConfig(
    name="Vllm model",
    url="vllm_url",
    model_id="model_id",
)


start_node = StartNode(
    name="Start node",
    inputs=[user_request_property],
)

end_node = EndNode(
    name="End node",
    outputs=[code_property],
)


generate_code_node = LlmNode(
    name="Generate code node",
    prompt_template="""You are a great code python software engineer.

    Please write the python code to satisfy the following user request: "{{user_request}}".

    You previously generated the following snippet of code:
    ```
    {{code}}
    ```
    Take inspiration from the snippet of code.

    The code reviewer gave the following feedback:
    {{review}}
    Take also into account the comments in the review

    Write only the python code.
    """,
    llm_config=llm_config,
    inputs=[user_request_property, code_property, review_property],
    outputs=[code_property],
)

review_code_node = LlmNode(
    name="Review code node",
    prompt_template="""You are a great code python software engineer, and a highly skilled code reviewer.
    Please review the following snippet of python code:
    ```
    {{code}}
    ```
    """,
    llm_config=llm_config,
    inputs=[code_property],
    outputs=[review_property],
)

is_code_ready_decision_node = LlmNode(
    name="Check if code is ready node",
    prompt_template="""You are a software engineer with 20 years of experience. You have to take a decision.
    Based on the following code review, do you think that the code is ready to be deployed?
    ```
    {{review}}
    ```
    Please answer only with `yes` or `no`.
    """,
    llm_config=llm_config,
    inputs=[review_property],
    outputs=[is_code_ready_property],
)

is_code_ready_branching_node = BranchingNode(
    name="Is code ready branching node",
    mapping={
        "yes": "yes",
        "no": "no",
    },
    inputs=[is_code_ready_property],
    outputs=[],
)

control_flow_edges = [
    ControlFlowEdge(
        name="start_to_generate_code_control_edge",
        from_node=start_node,
        to_node=generate_code_node,
    ),
    ControlFlowEdge(
        name="generate_code_to_review_control_edge",
        from_node=generate_code_node,
        to_node=review_code_node,
    ),
    ControlFlowEdge(
        name="review_to_is_code_ready_decision_control_edge",
        from_node=review_code_node,
        to_node=is_code_ready_decision_node,
    ),
    ControlFlowEdge(
        name="is_code_ready_decision_to_is_code_ready_branching_control_edge",
        from_node=is_code_ready_decision_node,
        to_node=is_code_ready_branching_node,
    ),
    ControlFlowEdge(
        name="is_code_ready_branching_to_end_control_edge",
        from_node=is_code_ready_branching_node,
        from_branch="yes",
        to_node=end_node,
    ),
    ControlFlowEdge(
        name="is_code_ready_branching_to_generate_code_control_edge",
        from_node=is_code_ready_branching_node,
        from_branch="no",
        to_node=generate_code_node,
    ),
]


data_flow_edges = [
    DataFlowEdge(
        name="start_to_generate_code_user_request_data_edge",
        source_node=start_node,
        source_output="user_request",
        destination_node=generate_code_node,
        destination_input="user_request",
    ),
    DataFlowEdge(
        name="generate_code_to_end_code_data_edge",
        source_node=generate_code_node,
        source_output="code",
        destination_node=end_node,
        destination_input="code",
    ),
    DataFlowEdge(
        name="generate_code_to_generate_code_code_data_edge",
        source_node=generate_code_node,
        source_output="code",
        destination_node=generate_code_node,
        destination_input="code",
    ),
    DataFlowEdge(
        name="generate_code_to_review_code_data_edge",
        source_node=generate_code_node,
        source_output="code",
        destination_node=review_code_node,
        destination_input="code",
    ),
    DataFlowEdge(
        name="review_code_to_generate_code_review_data_edge",
        source_node=review_code_node,
        source_output="review",
        destination_node=generate_code_node,
        destination_input="review",
    ),
    DataFlowEdge(
        name="review_code_to_is_code_ready_review_data_edge",
        source_node=review_code_node,
        source_output="review",
        destination_node=is_code_ready_decision_node,
        destination_input="review",
    ),
    DataFlowEdge(
        name="review_code_to_is_code_ready_flag_data_edge",
        source_node=is_code_ready_decision_node,
        source_output="is_code_ready",
        destination_node=is_code_ready_branching_node,
        destination_input="is_code_ready",
    ),
]


final_assistant_flow = Flow(
    name="Generate code and review flow",
    description="Flow that given a user request, generates a python code snippet to satisfy it and passes it through a code review before returning it",
    start_node=start_node,
    nodes=[
        start_node,
        generate_code_node,
        review_code_node,
        is_code_ready_decision_node,
        is_code_ready_branching_node,
        end_node,
    ],
    control_flow_connections=control_flow_edges,
    data_flow_connections=data_flow_edges,
)


if __name__ == "__main__":
    serialized_agent = AgentSpecSerializer().to_json(final_assistant_flow)
    print(serialized_agent)
# .. end-full-code:
