# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# isort:skip_file
# mypy: ignore-errors

# .. start-##_Define_the_LLM
from pyagentspec.llms import VllmConfig

llm_config = VllmConfig(
    name="vllm-llama-4-maverick",
    model_id="llama-4-maverick",
    url="http://url.to.my.vllm.server/llama4mav",
)
# .. end-##_Define_the_LLM

# .. start-##_Specialist_tools
from pyagentspec.property import (
    BooleanProperty,
    StringProperty,
    NumberProperty,
    DictProperty,
    UnionProperty,
    IntegerProperty,
    NullProperty,
)
from pyagentspec.tools import ServerTool

check_refund_eligibility = ServerTool(
    name="Check refund eligibility",
    description="Checks if a given order is eligible for a refund based on company policy.",
    inputs=[StringProperty(title="order_id"), StringProperty(title="customer_id")],
    outputs=[
        DictProperty(
            title="refund_eligibility",
            value_type=UnionProperty(
                any_of=[BooleanProperty(), NumberProperty(), StringProperty()]
            ),
        )
    ],
)

process_refund = ServerTool(
    name="Process refund",
    description="Processes a refund for a specific order and amount.",
    inputs=[
        StringProperty(title="order_id"),
        NumberProperty(title="amount"),
        StringProperty(title="reason"),
    ],
    outputs=[
        DictProperty(
            title="refund_status",
            value_type=UnionProperty(any_of=[StringProperty(), BooleanProperty()]),
        )
    ],
)

# .. end-##_Specialist_tools

# .. start-##_Specialist_prompt
REFUND_SPECIALIST_SYSTEM_PROMPT = """
You are a Refund Specialist agent whose objective is to process customer refund requests accurately and efficiently based on company policy.

# Instructions
- Receive the refund request details (e.g., order ID, customer ID, reason) from the 'CustomerServiceManager'.
- Use the `check_refund_eligibility` tool to verify if the request meets the refund policy criteria using the provided order and customer IDs.
- If the check indicates eligibility, determine the correct refund amount (up to the maximum allowed from the eligibility check).
- If eligible, use the `process_refund` tool to execute the refund for the determined amount, providing order ID and reason.
- If ineligible based on the check, clearly note the reason provided by the tool.
- Report the final outcome (e.g., "Refund processed successfully, Refund ID: [ID], Amount: [Amount]", or "Refund denied: [Reason from eligibility check]") back to the 'CustomerServiceManager'.
- Do not engage in general conversation; focus solely on the refund process.
""".strip()
# .. end-##_Specialist_prompt

# .. start-##_Specialist_agent
from pyagentspec.agent import Agent

refund_specialist_agent = Agent(
    name="RefundSpecialist",
    description="Specializes in processing customer refund requests by verifying eligibility and executing the refund transaction using available tools.",
    llm_config=llm_config,
    system_prompt=REFUND_SPECIALIST_SYSTEM_PROMPT,
    tools=[check_refund_eligibility, process_refund],
)
# .. end-##_Specialist_agent

# .. start-##_Surveyor_tools
record_survey_response = ServerTool(
    name="Record survey response",
    description="Records the customer's satisfaction survey response.",
    inputs=[
        StringProperty(title="customer_id"),
        UnionProperty(
            title="satisfaction_score",
            any_of=[IntegerProperty(), NullProperty()],
            default=None,
        ),
        UnionProperty(
            title="comments",
            any_of=[StringProperty(), NullProperty()],
            default=None,
        ),
    ],
    outputs=[
        DictProperty(
            title="recording_status",
            value_type=UnionProperty(any_of=[BooleanProperty(), StringProperty()]),
        )
    ],
)
# .. end-##_Surveyor_tools

# .. start-##_Surveyor_prompt
SURVEYOR_SYSTEM_PROMPT = """
You are a Satisfaction Surveyor agent tasked with collecting customer feedback about their recent service experience in a friendly manner.

# Instructions
- Receive the trigger to conduct a survey from the 'CustomerServiceManager', including context like the customer ID and the nature of the interaction if provided.
- Politely ask the customer if they have a moment to provide feedback on their recent interaction.
- If the customer agrees, ask 1-2 concise questions about their satisfaction (e.g., "On a scale of 1 to 5, where 5 is highly satisfied, how satisfied were you with the resolution provided today?", "Is there anything else you'd like to share about your experience?").
- Use the `record_survey_response` tool to log the customer's feedback, including the satisfaction score and any comments provided. Ensure you pass the correct customer ID.
- If the customer declines to participate, thank them for their time anyway. Do not pressure them. Use the `record_survey_response` tool to log the declination if possible (e.g., score=None, comments="Declined survey").
- Thank the customer for their participation if they provided feedback.
- Report back to the 'CustomerServiceManager' confirming that the survey was attempted and whether it was completed or declined.
""".strip()
# .. end-##_Surveyor_prompt

# .. start-##_Surveyor_agent
surveyor_agent = Agent(
    name="SatisfactionSurveyor",
    description="Conducts brief surveys to gather feedback on customer satisfaction following service interactions.",
    llm_config=llm_config,
    system_prompt=SURVEYOR_SYSTEM_PROMPT,
    tools=[record_survey_response],
)
# .. end-##_Surveyor_agent

# .. start-##_Manager_prompt
MANAGER_SYSTEM_PROMPT = """
You are a Customer Service Manager agent tasked with handling incoming customer interactions and orchestrating the resolution process efficiently.

# Instructions
- Greet the customer politely and acknowledge their message.
- Analyze the customer's message to understand their core need (e.g., refund request, general query, feedback).
- Answer common informational questions (e.g., about shipping times, return policy basics) directly if you have the knowledge, before delegating.
- If the request is clearly about a refund, gather necessary details (like Order ID) if missing, and then assign the task to the 'RefundSpecialist' agent. Provide all relevant context.
- If the interaction seems successfully concluded (e.g., refund processed, query answered) and requesting feedback is appropriate, assign the task to the 'SatisfactionSurveyor' agent. Provide customer context.
- For general queries you cannot handle directly and that don't fit the specialist agents, state your limitations clearly and politely.
- Await responses or status updates from specialist agents you have assigned to.
- Summarize the final outcome or confirmation for the customer based on specialist agent reports.
- Maintain a helpful, empathetic, and professional tone throughout the interaction.

# Additional Context
Customer ID: {{customer_id}}
Company policies: {{company_policy_info}}
""".strip()
# .. end-##_Manager_prompt

# .. start-##_Manager_agent
customer_service_manager = Agent(
    name="CustomerServiceManager",
    description="Acts as the primary contact point for customer inquiries, analyzes the request, routes tasks to specialized agents (Refund Specialist, Satisfaction Surveyor), and ensures resolution.",
    llm_config=llm_config,
    system_prompt=MANAGER_SYSTEM_PROMPT,
)
# .. end-##_Manager_agent

# .. start-##_Managerworkers_pattern
from pyagentspec.managerworkers import ManagerWorkers

assistant = ManagerWorkers(
    name="managerworkers",
    group_manager=customer_service_manager,
    workers=[refund_specialist_agent, surveyor_agent],
)
# .. end-##_Managerworkers_pattern

# .. start-##_Export_serialization
from pyagentspec.serialization import AgentSpecSerializer

serialized_assistant = AgentSpecSerializer().to_json(assistant)

# you can print the serialized form or save it to a file
print(serialized_assistant)
# .. end-##_Export_serialization
