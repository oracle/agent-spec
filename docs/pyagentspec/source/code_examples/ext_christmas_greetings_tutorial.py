# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# isort:skip_file
# fmt: off
# mypy: ignore-errors

from pyagentspec.llms import OpenAiConfig

llm_config = OpenAiConfig(
    name="openai-llm",
    model_id="model-id", # e.g. "gpt-4.1"
)

from pyagentspec.property import StringProperty, Property, ListProperty

# Email data schema for recipient and sender information
email_data_schema = {
    "title": "email_data",
    "description": "Consolidated data for email sending",
    "type": "object",
    "properties": {
        "recipient_name": {
            "type": "string",
            "description": "Name of the recipient",
            "default": "",
        },
        "recipient_info": {
            "type": "string",
            "description": "Information about the recipient including relationship, and notes etc.",
            "default": "",
        },
        "recipient_email": {
            "type": "string",
            "description": "The email address of the recipient",
            "default": "",
        },
        "sender_name": {
            "type": "string",
            "description": "The name of the sender",
            "default": "",
        },
    },
}
email_data_property = Property(json_schema=email_data_schema)

subject_property = StringProperty(
    title="subject", description="The subject line of the email."
)
body_property = StringProperty(
    title="body", description="The body content of the email."
)

image_property = StringProperty(title="image", description="Image generation.")
result_property = StringProperty(
    title="result", description="Result of the email sending operation."
)

from pyagentspec.flows.flow import Flow
from pyagentspec.flows.node import Node
from pyagentspec.flows.nodes import (
    EndNode,
    LlmNode,
    StartNode,
    ToolNode,
)
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.tools import ServerTool

# Helper functions for creating edges
def create_data_flow_edge(
    source_node: Node,
    source_output: str,
    destination_node: Node,
    destination_input: str,
) -> DataFlowEdge:
    return DataFlowEdge(
        name=f"{source_node.name}_{destination_node.name}",
        source_node=source_node,
        source_output=source_output,
        destination_node=destination_node,
        destination_input=destination_input,
    )


def create_control_flow_edge(
    from_node: Node, to_node: Node, from_branch: str | None = None
) -> ControlFlowEdge:
    return ControlFlowEdge(
        name=f"{from_node.name}_{to_node.name}_{from_branch}",
        from_node=from_node,
        to_node=to_node,
        from_branch=from_branch,
    )


# Initialize lists for nodes and edges
data_flow_edges: list[DataFlowEdge] = []
control_flow_edges: list[ControlFlowEdge] = []
flow_nodes: list[Node] = []


# Start and End nodes for the subflow
start_node = StartNode(name="start_node", inputs=[email_data_property])
end_node = EndNode(name="end_node", outputs=[result_property])
flow_nodes.extend([start_node, end_node])

# LLM node for message generation
CUSTOM_INSTRUCTIONS = """
You are a friendly holiday greeter tasked with creating personalized Christmas greetings to recipients. Your primary goal is to craft thoughtful, customized messages based on recipient details.

**Workflow:**
- **1. Recipient Information:** Use the provided details about the recipient, such as name, relationship (friend, family, colleague), and any specific notes (e.g., recent achievements, shared memories).
- **2. Message Customization:** Create a unique, heartfelt Christmas message tailored to the recipient.
- **3. Drafting:** Draft the message, ensuring it reflects a warm, festive tone and includes personalized elements.

**Guidelines:**
- Use a warm, friendly tone in all messages. Reflect the spirit of the holiday season.
- Use about 200 words for the message.
- Ensure messages are personalized, avoid generic content unless no details are provided.

Your greetings should brighten the recipient's day and strengthen connections during the holiday season.

Please make sure the body is formatted with spacing and new lines like a proper email.

Information about recipients and senders is in: {{email_data}}
""".strip()

message_generator_node = LlmNode(
    name="message_generator_node",
    prompt_template=CUSTOM_INSTRUCTIONS,
    llm_config=llm_config,
    inputs=[email_data_property],
    outputs=[subject_property, body_property],
)
flow_nodes.append(message_generator_node)
control_flow_edges.append(
    create_control_flow_edge(start_node, message_generator_node)
)
data_flow_edges.append(
    create_data_flow_edge(
        start_node, "email_data", message_generator_node, "email_data"
    )
)

# Tool node for image generation
generate_image_tool = ServerTool(
    name="generate_image_tool",
    description="Generate image based on text.",
    inputs=[body_property],
    outputs=[image_property],
)
generate_image_node = ToolNode(name="generate_image_node", tool=generate_image_tool)
flow_nodes.append(generate_image_node)
control_flow_edges.append(
    create_control_flow_edge(message_generator_node, generate_image_node)
)
data_flow_edges.append(
    create_data_flow_edge(message_generator_node, "body", generate_image_node, "body")
)

# Tool node for sending email
send_email_tool = ServerTool(
    name="send_email_tool",
    description="Send email.",
    inputs=[email_data_property, subject_property, body_property, image_property],
    outputs=[result_property],
)
send_email_node = ToolNode(name="send_email_node", tool=send_email_tool)
flow_nodes.append(send_email_node)
control_flow_edges.extend(
    [
        create_control_flow_edge(generate_image_node, send_email_node),
        create_control_flow_edge(send_email_node, end_node),
    ]
)
data_flow_edges.extend(
    [
        create_data_flow_edge(
            message_generator_node, "subject", send_email_node, "subject"
        ),
        create_data_flow_edge(message_generator_node, "body", send_email_node, "body"),
        create_data_flow_edge(generate_image_node, "image", send_email_node, "image"),
        create_data_flow_edge(start_node, "email_data", send_email_node, "email_data"),
        create_data_flow_edge(send_email_node, "result", end_node, "result"),
    ]
)


# Define the flow
flow = Flow(
    name="Christmas_Greetings_Flow",
    start_node=start_node,
    nodes=flow_nodes,
    control_flow_connections=control_flow_edges,
    data_flow_connections=data_flow_edges,
    inputs=[email_data_property],
    outputs=[result_property],
)


iterated_email_data_property = ListProperty(
    title="iterated_email_data", item_type=email_data_property
)
collected_result_property = ListProperty(
    title="collected_result", item_type=result_property
)

from pyagentspec.flows.nodes import MapNode
map_node = MapNode(name="map_node", subflow=flow)

iterated_email_data_property = ListProperty(
    title="iterated_email_data", item_type=email_data_property
)
collected_result_property = ListProperty(
    title="collected_result", item_type=result_property
)

main_start_node = StartNode(name="main_start_node", inputs=[iterated_email_data_property])
main_end_node = EndNode(name="main_end_node", outputs=[collected_result_property])

# Main flow
main_flow = Flow(
    name="MapNode_Christmas_Greetings_Flow",
    start_node=main_start_node,
    nodes=[main_start_node, main_end_node, map_node],
    control_flow_connections=[
        create_control_flow_edge(main_start_node, map_node),
        create_control_flow_edge(map_node, main_end_node),
    ],
    data_flow_connections=[
        create_data_flow_edge(
            main_start_node, "iterated_email_data", map_node, "iterated_email_data"
        ),
        create_data_flow_edge(
            map_node, "collected_result", main_end_node, "collected_result"
        ),
    ],
)


from pyagentspec.serialization import AgentSpecSerializer

serialized_flow = AgentSpecSerializer().to_json(main_flow)

## Running the Flow (Uncomment to run)

# # Wayflow
# from wayflowcore.tools import tool
# from wayflowcore.property import StringProperty as WayflowStringProperty
# import os
# import httpx

# @tool(
#     description_mode="only_docstring",
#     output_descriptors=[WayflowStringProperty("image")],
# )
# def generate_image_impl(body: str) -> str:
#     """
#     Generate an image using a Multimodal LLM based on the email generated

#     Parameters:
#         body: Email body content

#     Returns:
#         str: A b64 json encoded image data.
#     """
#     prompt = f"""
#     Create a beautiful and festive Christmas greeting card. 
#     The design should evoke a warm, inspiring, and joyful holiday atmosphere. 
#     Use the following email content as inspiration for the message, but please avoid copying the exact words. 
#     Instead, make the message general enough to fit anyone, but specific enough to feel personal and meaningful. 
#     The design should be elegant and incorporate Christmas-themed visuals like snowflakes, trees, ornaments, or winter scenes. 
#     Email Content Inspiration:
#     {body}
#     Keep the tone heartfelt and warm, with a balance of cheerfulness and inspiration. 
#     Feel free to include any symbolic holiday elements that would enhance the mood. 
#     Make sure the image conveys a sense of closeness and joy without directly quoting the email text.
#     Don't use more than 20 words. The card should have a clean, colored, flat design with no background elements. 
#     Keep it minimalistic, with the message or visual elements standing out. 
#     """
#     url = "https://api.openai.com/v1/images/generations"
#     payload = {"model": "gpt-image-1", "prompt": prompt}
#     openai_api_key = os.getenv("OPENAI_API_KEY", None)
#     if not openai_api_key:
#         return "Error: `OPENAI_API_KEY` not found in environment variables."
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {openai_api_key}",
#     }
#     try:
#         with httpx.Client() as client:
#             response = client.post(url, json=payload, headers=headers, timeout=120.0)
#             response.raise_for_status()
#             response_data = response.json()
#             image_data = response_data.get("data", [{}])[0].get("b64_json", "")
#             if not image_data:
#                 return "Error: No image URL returned from API."
#             return image_data
#     except httpx.TimeoutException as e:
#         return f"Error generating image: The request timed out. {str(e)}"
#     except httpx.RequestError as e:
#         return f"Error generating image: A request error occurred. {str(e)}"


# from typing import Dict
# import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from email.mime.image import MIMEImage
# import base64
# import re

# SENT_EMAILS_TRACKER = set()

# def is_valid_email(email):
#     pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
#     return re.match(pattern, email) is not None

# @tool(
#     description_mode="only_docstring",
#     output_descriptors=[WayflowStringProperty("result")],
# )
# def send_email_tool_impl(
#     email_data: Dict[str, str], subject: str, body: str, image: str
# ) -> str:
#     """
#     Send an email with the given subject and body to the recipient using Gmail's SMTP server.
#     Includes mechanisms to prevent sending the same email multiple times accidentally and to validate email addresses.

#     Parameters:
#         email_data: Consolidated data for email sending
#         subject: Subject of the email
#         body: Body of the email
#         image: Image to be attached in the email

#     Returns:
#         str: A message indicating the result of the email sending attempt.
#             If successful, returns a success message with the recipient's email address.
#             If the email was already sent, returns a message indicating it was skipped.
#             If the email address is invalid, returns a message indicating the validation failure.
#             If an error occurs, returns a failure message with the error description.
#     """
#     sender_email = os.getenv("EMAIL_ADDRESS", None)
#     if not sender_email:
#         return "Error: `EMAIL_ADDRESS` not found in environment variables."
#     sender_password = os.getenv("EMAIL_PASSWORD", None)
#     if not sender_password:
#         return "Error: `EMAIL_PASSWORD` not found in environment variables."

#     if not is_valid_email(email_data["recipient_email"]):
#         return f"Invalid email address: {email_data['recipient_email']}. Email not sent."

#     if email_data["recipient_email"] in SENT_EMAILS_TRACKER:
#         return f"Email already sent to {email_data['recipient_email']}, skipping to prevent duplication."

#     msg = MIMEMultipart()
#     msg["From"] = sender_email
#     msg["To"] = email_data["recipient_email"]
#     msg["Subject"] = subject
#     msg.attach(MIMEText(body, "plain"))
#     image_data = base64.b64decode(image)
#     try:
#         image_name = "greetings.png"
#         image_attachment = MIMEImage(
#             image_data, name=image_name
#         )
#         image_attachment.add_header(
#             "Content-Disposition", f'attachment; filename="{image_name}"'
#         )
#         msg.attach(image_attachment)
#     except Exception as e:
#         return f"Failed to attach image: {str(e)}"
#     try:
#         with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp_server:
#             smtp_server.login(sender_email, sender_password)
#             smtp_server.sendmail(
#                 sender_email,
#                 email_data["recipient_email"],
#                 msg.as_string(),
#             )
#         SENT_EMAILS_TRACKER.add(email_data["recipient_email"])
#         return f"Email sent successfully to {email_data['recipient_email']}"
#     except Exception as e:
#         return f"Failed to send email to {email_data['recipient_email']}: {str(e)}"


# from wayflowcore.agentspec import AgentSpecLoader
# from wayflowcore.flow import Flow as RuntimeFlow

# # Register tools
# tool_registry = {
#     "generate_image_tool": generate_image_impl,
#     "send_email_tool": send_email_tool_impl,
# }

# # Load the flow
# flow_instance: RuntimeFlow = AgentSpecLoader(tool_registry=tool_registry).load_json(
#     serialized_flow
# )

# inputs = {
#     "iterated_email_data": [
#         {
#             "recipient_name": "Bethy",
#             "recipient_info": "Aunt. Extremely sweet and caring person. I loved going to her place for Thanksgiving.",
#             "recipient_email": "recipient_email@gmail.com",
#             "sender_name": "Matthew",
#         },
#         {
#             "recipient_name": "Jacob",
#             "recipient_info": "Uncle. Nice but tough person. He gave good advice when I just started my career.",
#             "recipient_email": "recipient_email@gmail.com",
#             "sender_name": "Matthew",
#         }
#     ]
# }

# conversation = flow_instance.start_conversation(inputs)
# status = conversation.execute()

# # Langgraph
# import os
# import httpx

# def generate_image_impl(body: str) -> str:
#     """
#     Generate an image using a Multimodal LLM based on the email generated

#     Parameters:
#         body: Email body content

#     Returns:
#         str: A b64 json encoded image data.
#     """
#     prompt = f"""
#     Create a beautiful and festive Christmas greeting card. 
#     The design should evoke a warm, inspiring, and joyful holiday atmosphere. 
#     Use the following email content as inspiration for the message, but please avoid copying the exact words. 
#     Instead, make the message general enough to fit anyone, but specific enough to feel personal and meaningful. 
#     The design should be elegant and incorporate Christmas-themed visuals like snowflakes, trees, ornaments, or winter scenes. 
#     Email Content Inspiration:
#     {body}
#     Keep the tone heartfelt and warm, with a balance of cheerfulness and inspiration. 
#     Feel free to include any symbolic holiday elements that would enhance the mood. 
#     Make sure the image conveys a sense of closeness and joy without directly quoting the email text.
#     Don't use more than 20 words. The card should have a clean, colored, flat design with no background elements. 
#     Keep it minimalistic, with the message or visual elements standing out. 
#     """
#     url = "https://api.openai.com/v1/images/generations"
#     payload = {"model": "gpt-image-1", "prompt": prompt}
#     openai_api_key = os.getenv("OPENAI_API_KEY", None)
#     if not openai_api_key:
#         return "Error: `OPENAI_API_KEY` not found in environment variables."
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {openai_api_key}",
#     }
#     try:
#         with httpx.Client() as client:
#             response = client.post(url, json=payload, headers=headers, timeout=120.0)
#             response.raise_for_status()
#             response_data = response.json()
#             image_data = response_data.get("data", [{}])[0].get("b64_json", "")
#             if not image_data:
#                 return "Error: No image URL returned from API."
#             return image_data
#     except httpx.TimeoutException as e:
#         return f"Error generating image: The request timed out. {str(e)}"
#     except httpx.RequestError as e:
#         return f"Error generating image: A request error occurred. {str(e)}"


# from typing import Dict
# import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from email.mime.image import MIMEImage
# import base64
# import re

# SENT_EMAILS_TRACKER = set()

# def is_valid_email(email):
#     pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
#     return re.match(pattern, email) is not None

# def send_email_tool_impl(
#     email_data: Dict[str, str], subject: str, body: str, image: str
# ) -> str:
#     """
#     Send an email with the given subject and body to the recipient using Gmail's SMTP server.
#     Includes mechanisms to prevent sending the same email multiple times accidentally and to validate email addresses.

#     Parameters:
#         email_data: Consolidated data for email sending
#         subject: Subject of the email
#         body: Body of the email
#         image: Image to be attached in the email

#     Returns:
#         str: A message indicating the result of the email sending attempt.
#             If successful, returns a success message with the recipient's email address.
#             If the email was already sent, returns a message indicating it was skipped.
#             If the email address is invalid, returns a message indicating the validation failure.
#             If an error occurs, returns a failure message with the error description.
#     """
#     sender_email = os.getenv("EMAIL_ADDRESS", None)
#     if not sender_email:
#         return "Error: `EMAIL_ADDRESS` not found in environment variables."
#     sender_password = os.getenv("EMAIL_PASSWORD", None)
#     if not sender_password:
#         return "Error: `EMAIL_PASSWORD` not found in environment variables."

#     if not is_valid_email(email_data["recipient_email"]):
#         return f"Invalid email address: {email_data['recipient_email']}. Email not sent."

#     if email_data["recipient_email"] in SENT_EMAILS_TRACKER:
#         return f"Email already sent to {email_data['recipient_email']}, skipping to prevent duplication."

#     msg = MIMEMultipart()
#     msg["From"] = sender_email
#     msg["To"] = email_data["recipient_email"]
#     msg["Subject"] = subject
#     msg.attach(MIMEText(body, "plain"))
#     image_data = base64.b64decode(image)
#     try:
#         image_name = "greetings.png"
#         image_attachment = MIMEImage(
#             image_data, name=image_name
#         )
#         image_attachment.add_header(
#             "Content-Disposition", f'attachment; filename="{image_name}"'
#         )
#         msg.attach(image_attachment)
#     except Exception as e:
#         return f"Failed to attach image: {str(e)}"
#     try:
#         with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp_server:
#             smtp_server.login(sender_email, sender_password)
#             smtp_server.sendmail(
#                 sender_email,
#                 email_data["recipient_email"],
#                 msg.as_string(),
#             )
#         SENT_EMAILS_TRACKER.add(email_data["recipient_email"])
#         return f"Email sent successfully to {email_data['recipient_email']}"
#     except Exception as e:
#         return f"Failed to send email to {email_data['recipient_email']}: {str(e)}"

# from pyagentspec.adapters.langgraph import AgentSpecLoader

# tool_registry = {
#     "generate_image_tool": generate_image_impl,
#     "send_email_tool": send_email_tool_impl,
# }

# langgraph_flow = AgentSpecLoader(tool_registry=tool_registry).load_json(serialized_flow)

# inputs = {
#     "iterated_email_data": [
#         {
#             "recipient_name": "Bethy",
#             "recipient_info": "Aunt. Extremely sweet and caring person. I loved going to her place for Thanksgiving.",
#             "recipient_email": "recipient_email@gmail.com",
#             "sender_name": "Matthew",
#         },
#         {
#             "recipient_name": "Jacob",
#             "recipient_info": "Uncle. Nice but tough person. He gave good advice when I just started my career.",
#             "recipient_email": "recipient_email@gmail.com",
#             "sender_name": "Matthew",
#         }
#     ]
# }


# config = {"configurable": {"thread_id": "1"}}
# result = langgraph_flow.invoke(
#     {"inputs": inputs}, config,
# )
