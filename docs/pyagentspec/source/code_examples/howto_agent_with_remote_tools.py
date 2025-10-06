# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.
# mypy: ignore-errors

# .. define-properties:

from pyagentspec.property import ListProperty, StringProperty

agent_title_property = StringProperty(
    title="agent_title",
    description="The agent title",
    default="Benefits Assistant Agent",
)

agent_description_property = StringProperty(
    title="agent_description",
    description="The agent description",
    default=(
        "This agent provides employees with accurate and efficient responses to"
        "benefits-related inquiries"
    ),
)

workflow_title_property = StringProperty(
    title="workflow_title",
    description="The workflow title",
    default="Benefits Advisor Workflow",
)

workflow_description_property = StringProperty(
    title="workflow_description",
    description="The workflow description",
    default=(
        "This Agent workflow is designed for integration within the benefits product's chatbot, "
        "enabling seamless interaction with employees."
    ),
)

topics_property = StringProperty(
    title="topics",
    description="The topics",
    default=(
        "- Medical Insurance"
        "\n- General Benefits Coverage"
        "\n- Retirement Benefits Coverage"
        "\n- Employee Benefits Enrollments"
    ),
)

special_instructions_property = StringProperty(
    title="special_instructions",
    description="The special instructions",
    default=(
        "\n- If insufficient data is available to answer a query, ask the user for clarification or additional information."
        "\n- Only entertain questions related to benefits."
        "\n- Fetch factual information from documents using the RAG Retriever tool instead of generating it yourself."
        "\n- For user-specific details like costs or savings, use the REST tool to obtain only relevant information."
        "\n- Use the Calculator Tool for queries requiring calculations."
        "\n- Provide relevant details (e.g., insurance company, health plan, names, dates) as input to the RAG Retriever tool for effective semantic search."
        "\n- If a question is repeated, respond politely without mentioning the repetition."
        "\n- Your goal is to consolidate information retrieved from tools into a coherent answer addressing the user's query."
        "\n- Treat the USER_QUERY as the sole source of the user's question."
    ),
)

format_instructions_property = StringProperty(title="format_instructions")
context_property = StringProperty(title="context")
employee_property = StringProperty(title="employee_id")

task_property = StringProperty(
    title="task",
    description="A task, expressed as an imperative, of which data to look up in the database",
)

query_property = StringProperty(
    title="query",
    description="The query string in interrogative form to be used to retrieve documents for addressing user questions.",
)

problem_property = StringProperty(
    title="problem",
    description="A mathematical problem in natural language.",
)

benefits_enrollment_status_property = StringProperty(
    title="benefits_enrollment_status",
    description="Output of the tool Benefits_Enrollment_Status_REST_API_Tool",
)

cost_and_contribution_property = StringProperty(
    title="cost_and_contribution",
    description="Output of the tool Costs_and_Contributions_REST_API_Tool",
)

coverage_and_plan_details_property = StringProperty(
    title="coverage_and_plan",
    description="Output of the tool Coverage_and_Plan_Details_REST_API_Tool",
)

dependents_and_beneficiaries_property = StringProperty(
    title="dependents_and_beneficiaries",
    description="Output of the tool Dependents_and_Beneficiaries_REST_API_Tool",
)

providers_and_policy_info_property = StringProperty(
    title="providers_and_policy_info",
    description="Output of the tool Providers_and_Policy_Information_REST_API_Tool",
)

calculator_output_property = StringProperty(
    title="calculator_output",
    description="Output of the tool Calculator_Tool",
)

benefits_policy_rag_property = ListProperty(
    title="benefits_policy_rag",
    description="Output of the tool RAG_Retrieval_Tool",
    item_type=StringProperty(),
)

# .. end-define-properties:

# .. define-tools:

from urllib.parse import urljoin

from pyagentspec.tools.remotetool import RemoteTool

# Change this url depending on where the API is hosted
remote_tools_url: str = "http://127.0.0.1:HOST_PORT/"

tools = [
    RemoteTool(
        name="Benefits_Enrollment_Status_REST_API_Tool",
        description="Tracks the current status and pending actions related to benefits enrollment.",
        url=urljoin(remote_tools_url, "benefits/{{task}}"),
        http_method="GET",
        inputs=[task_property],
        outputs=[benefits_enrollment_status_property],
    ),
    RemoteTool(
        name="Costs_and_Contributions_REST_API_Tool",
        description="Generates a breakdown of costs and contributions associated with benefits plans.",
        url=urljoin(remote_tools_url, "costs"),
        http_method="GET",
        data={"employee_id": "{{employee_id}}"},
        inputs=[employee_property],
        outputs=[cost_and_contribution_property],
    ),
    RemoteTool(
        name="Coverage_and_Plan_Details_REST_API_Tool",
        description="Provides detailed information about the employee's existing benefits coverage and plans.",
        url=urljoin(remote_tools_url, "coverage/{{task}}"),
        http_method="GET",
        inputs=[task_property],
        outputs=[coverage_and_plan_details_property],
    ),
    RemoteTool(
        name="Dependents_and_Beneficiaries_REST_API_Tool",
        description="Retrieves information about dependents and beneficiaries linked to benefits plans.",
        url=urljoin(remote_tools_url, "dependents/{{task}}"),
        http_method="GET",
        inputs=[task_property],
        outputs=[dependents_and_beneficiaries_property],
    ),
    RemoteTool(
        name="Providers_and_Policy_Information_REST_API_Tool",
        description="Offers details about benefits providers and policy-related information.",
        url=urljoin(remote_tools_url, "providers/{{task}}"),
        http_method="GET",
        inputs=[task_property],
        outputs=[providers_and_policy_info_property],
    ),
    RemoteTool(
        name="RAG_Retrieval_Tool",
        description="This tool empowers agents to retrieve HR benefits policy documents or chunks of documents from a knowledge base, enhancing the accuracy of responses.",
        url=urljoin(remote_tools_url, "rag"),
        data={"query": "{{query}}"},
        http_method="GET",
        inputs=[query_property],
        outputs=[benefits_policy_rag_property],
    ),
    RemoteTool(
        name="Calculator_Tool",
        description="This tool allows agents to perform real-time mathematical computations for needs like estimates of benefits costs, deductibles, coverages, etc.",
        url=urljoin(remote_tools_url, "calculator"),
        data={"problem": "{{problem}}"},
        http_method="POST",
        inputs=[problem_property],
        outputs=[calculator_output_property],
    ),
]

# .. end-define-tools:
from pyagentspec.llms.vllmconfig import VllmConfig

llm_config = VllmConfig(
    name="Vllm model",
    url="vllm_url",
    model_id="model_id",
)
# .. define-agent:


from pyagentspec.agent import Agent

system_prompt = """You are a helpful agent. Your official title is: {{agent_title}}.
The following statement describes your responsibilities:
"{{agent_description}}".

You are part of the workflow {{workflow_title}} within the company.
The following is a quick description of the workflow:
"{{workflow_description}}".

Your tasks are related to the following topics with their special instructions:
{{topics}}

Here are some extra special instructions:
{{special_instructions}}

Your answer is intended to be customer-facing, be sure to be professional in your response.
Do not invent answers or information.

{{format_instructions}}

{{context}}
"""

agent = Agent(
    name="Benefits Advisor",
    llm_config=llm_config,
    tools=tools,
    system_prompt=system_prompt,
    inputs=[
        agent_title_property,
        agent_description_property,
        workflow_title_property,
        workflow_description_property,
        topics_property,
        format_instructions_property,
        special_instructions_property,
        context_property,
    ],
)

# .. end-define-agent:

# .. export-serialization:

if __name__ == "__main__":

    from pyagentspec.serialization import AgentSpecSerializer

    serialized_agent = AgentSpecSerializer().to_json(agent)

    # you can print the serialized form or save it to a file
    print(serialized_agent)

# .. end-export-serialization:
