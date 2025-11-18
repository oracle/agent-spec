# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# isort:skip_file
# fmt: off
# mypy: ignore-errors

# .. define-llm
from pyagentspec.llms import VllmConfig

llm_config = VllmConfig(
    model_id="model_id",
    url="LLAMA_PLACEHOLDER_LINK",
    name="meta.llama-3.3-70b-instruct",
)

# .. start-tools
from pyagentspec.property import ListProperty, StringProperty
from pyagentspec.tools import ServerTool

symptoms_checker = ServerTool(
    name="Symptoms checker",
    description="Checks symptoms against the medical knowledge base.",
    inputs=[ListProperty(title="symptoms", item_type=StringProperty())],
    outputs=[ListProperty(title="possible_conditions", item_type=StringProperty())],
)

get_medication_info = ServerTool(
    name="Get medication info",
    description="Provides availability and information about a medication.",
    inputs=[StringProperty(title="drug_name")],
    outputs=[StringProperty(title="medication_info")],
)

knowledge_tool = ServerTool(
    name="Knowledge tool",
    description=" Provides diagnosis and treatment information for skin conditions.",
    inputs=[StringProperty(title="condition")],
    outputs=[StringProperty(title="treatment_info")],
)

# .. end-tools

# .. start-first-agent
from pyagentspec.agent import Agent

general_practitioner_system_prompt = """
You are an helpful general practitioner LLM doctor responsible for handling patient consultations.
Your goal is to assess patients' symptoms, provide initial diagnoses, pescribe medication for
mild conditions or refer to other specialists as needed.

## When to Use Each Tool
- symptoms_checker: Use this to look up possible conditions based on symptoms reported by the patient.

## When to query other Agents
- Pharmacist: Every time you need to prescribe some medication, give the condition description and prescription to the Pharmacist.
- Dermatologist: If the patient has a skin condition, ask expert advice/diagnosis to the Dermatologist after the initial exchange.

# Specific instructions
## Initial exchange
When a patient first shares symptoms ask about for exactly 1 round of questions, consisting of asking about medical history and
simple questions (e.g. do they have known allergies, when did the symptoms started, did they already tried some treatment/medication, etc)).
Always ask for this one round of information to the user before prescribing medication / referring to other agents.

## Identifying condition
Use the symptoms checker to confirm the condition (for mild conditions only. For other conditions, refer to specialists).

## Mild conditions
* If the patient has a mild cold, prescribe medicationA.
    - Give the condition description and prescription to the Pharmacist.

## Skin conditions
* If the patient has a skin condition, ask for expert advice/diagnosis from the Dermatologist.
Here, you don't need to ask for the user confirmation. Directly call the Dermatologist
    - Provide the patient's symptoms/initial hypothesis to the Dermatologist and ask for a diagnosis.
    - The Dermatologist may query the Pharmacist to confirm the availability of the prescribed medication.
    - Once the treatment is confirmed, pass on the prescription to the patient and ask them to follow the instructions.
""".strip()

general_practitioner = Agent(
    name="GeneralPractitioner",
    description="General Practitioner. Primary point of contact for patients, handles general medical inquiries, provides initial diagnoses, and manages referrals.",
    llm_config=llm_config,
    tools=[symptoms_checker],
    system_prompt=general_practitioner_system_prompt,
)
# .. end-first-agent


# .. start-second-agent
pharmacist_system_prompt = """
You are an helpful Pharmacist LLM Agent responsible for giving information about medication.
Your goal is to answer queries from the General Practitioner Doctor about medication information
and availabilities.

## When to Use Each Tool
- get_medication_info: Use this to look up availability and information about a specific medication.
""".strip()

pharmacist = Agent(
    name="Pharmacist",
    description="Pharmacist. Gives availability and information about specific medication.",
    llm_config=llm_config,
    tools=[get_medication_info],
    system_prompt=pharmacist_system_prompt,
)
# .. end-second-agent

# .. start-third-agent
dermatologist_system_prompt = """
You are an helpful Dermatologist LLM Agent responsible for diagnosing and treating skin conditions.
Your goal is to assess patients' symptoms, provide accurate diagnoses, and prescribe effective treatments.

## When to Use Each Tool
- knowledge_tool: Use this to look up diagnosis and treatment information for specific skin conditions.

## When to query other Agents
- Pharmacist: Every time you need to prescribe some medication, give the condition description and prescription to the Pharmacist.

# Specific instructions
## Initial exchange
When a patient's symptoms are referred to you by the General Practitioner, review the symptoms and use the knowledge tool to confirm the diagnosis.
## Prescription
Prescribe the recommended treatment for the diagnosed condition and query the Pharmacist to confirm the availability of the prescribed medication.

When answering back to the General Practitioner, describe your diagnosis and the prescription.
Tell the General Practitioner that you already checked with the pharmacist for availability.
""".strip()

dermatologist = Agent(
    name="Dermatologist",
    description="Dermatologist. Diagnoses and treats skin conditions.",
    llm_config=llm_config,
    tools=[knowledge_tool],
    system_prompt=dermatologist_system_prompt,
)
# .. end-third-agent

# .. start-swarm
from pyagentspec.swarm import Swarm

assistant = Swarm(
    name="Swarm",
    first_agent=general_practitioner,
    relationships=[
        (general_practitioner, pharmacist),
        (general_practitioner, dermatologist),
        (dermatologist, pharmacist),
    ],
)
# .. end-swarm

# .. start-serialization
from pyagentspec.serialization import AgentSpecSerializer

serialized_assistant = AgentSpecSerializer().to_json(assistant)
# .. end-serialization
print(serialized_assistant)
# .. start-swarm-with-handoff
assistant = Swarm(
    name="Swarm",
    first_agent=general_practitioner,
    relationships=[
        (general_practitioner, pharmacist),
        (general_practitioner, dermatologist),
        (dermatologist, pharmacist),
    ],
    handoff=True,  # <-- Add this
)
# .. end-swarm-with-handoff
