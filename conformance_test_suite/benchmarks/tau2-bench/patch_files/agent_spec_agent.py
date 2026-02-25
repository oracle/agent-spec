# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# mypy: ignore-errors

import os
from dataclasses import dataclass
from typing import Any, List, Optional

from tau2.agent.base import LocalAgent, ValidAgentInputMessage
from tau2.agent.llm_agent import AGENT_INSTRUCTION, SYSTEM_PROMPT
from tau2.data_model.message import (
    AssistantMessage,
    Message,
    MultiToolMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from tau2.domains.retail.data_model import (
    Order,
    Product,
    User,
)
from tau2.environment.environment import Environment
from tau2.environment.tool import Tool

from pyagentspec.agent import Agent
from pyagentspec.property import ListProperty, StringProperty
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.tools import ServerTool


@dataclass
class ToolResult:
    content: Any
    tool_request_id: str


class AgentSpecAgentState:
    """The state of the agent."""

    def __init__(self, runnable):
        self.runnable = runnable


class AgentSpecAgent(LocalAgent[AgentSpecAgentState]):

    def __init__(self, tools: list[Tool], domain_policy: str, environment: Environment):
        super().__init__(tools, domain_policy)
        self.environment = environment
        self.orchestrator = None
        self.tool_registry = None

    def set_orchestrator(self, orchestrator):
        self.orchestrator = orchestrator

    def generate_next_message(
        self, message: ValidAgentInputMessage, state: AgentSpecAgentState
    ) -> tuple[AssistantMessage, AgentSpecAgentState]:
        """
        Generate the next message from a user/tool message(s) and an agent state.
        Args:
            message: The user message or tool message(s).
            state: The agent state.

        Returns:
            A tuple of an assistant message and an agent state.
        """
        if isinstance(message, ToolMessage):
            print("Tool: {}".format(message))
            state.runnable.append_tool_results(
                ToolResult(
                    content=message.content,
                    tool_request_id=message.id,
                )
            )
        elif isinstance(message, MultiToolMessage):
            for tm in message.tool_messages:
                print("Tool: {}".format(tm))
                state.runnable.append_tool_results(
                    ToolResult(
                        content=tm.content,
                        tool_request_id=tm.id,
                    )
                )
        elif isinstance(message, UserMessage):
            print("User: {}".format(message))
            state.runnable.append_user_message(message.content)
        else:
            print(message.type)
            raise NotImplemented("uh oh ! unsupported message type")
        status = state.runnable.run()
        if getattr(status, "tool_requests", []):
            agent_message = AssistantMessage(
                role="assistant",
                tool_calls=[
                    ToolCall(
                        id=tool_request.tool_request_id,
                        name=tool_request.name,
                        arguments=(
                            tool_request.args["kwargs"]
                            if "kwargs" in tool_request.args
                            else tool_request.args
                        ),
                        requestor="assistant",
                    )
                    for tool_request in status.tool_requests
                ],
            )
            return agent_message, state
        elif getattr(status, "agent_messages", []):
            last_message = status.agent_messages[-1]
            agent_message = AssistantMessage(
                role="assistant",
                content=last_message,
            )
            print("Agent: {}".format(last_message))
            return agent_message, state
        else:
            raise NotImplementedError(f"uh oh ! what is this message {status}")

    def get_init_state(
        self,
        message_history: Optional[list[Message]] = None,
    ) -> AgentSpecAgentState:
        """
        Get the initial state of the agent.
        This is required to be able to rerun an agent from any point in the conversation.
        Args:
            message_history: The message history.

        Returns:
            The initial state of the agent.
        """

        def calculate(expression: str) -> str:
            """
            Calculate the result of a mathematical expression.

            Args:
                expression: The mathematical expression to calculate, such as '2 + 2'. The expression can contain numbers, operators (+, -, *, /), parentheses, and spaces.

            Returns:
                The result of the mathematical expression.

            Raises:
                ValueError: If the expression is invalid.
            """
            return self._tool_callable("calculate", expression=expression)

        def cancel_pending_order(order_id: str, reason: str) -> Order:
            """Cancel a pending order. If the order is already processed or delivered,
            it cannot be cancelled. The agent needs to explain the cancellation detail
            and ask for explicit user confirmation (yes/no) to proceed. If the user confirms,
            the order status will be changed to 'cancelled' and the payment will be refunded.
            The refund will be added to the user's gift card balance immediately if the payment
            was made using a gift card, otherwise the refund would take 5-7 business days to process.
            The function returns the order details after the cancellation.

            Args:
                order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.
                reason: The reason for cancellation, which should be either 'no longer needed' or 'ordered by mistake'.

            Returns:
                Order: The order details after the cancellation.
            """
            return self._tool_callable("cancel_pending_order", order_id=order_id, reason=reason)

        def exchange_delivered_order_items(
            order_id: str,
            item_ids: List[str],
            new_item_ids: List[str],
            payment_method_id: str,
        ) -> Order:
            """Exchange items in a delivered order to new items of the same product type.
            For a delivered order, return or exchange can be only done once by the agent.
            The agent needs to explain the exchange detail and ask for explicit user confirmation (yes/no) to proceed.

            Args:
                order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.
                item_ids: The item ids to be exchanged, each such as '1008292230'. There could be duplicate items in the list.
                new_item_ids: The item ids to be exchanged for, each such as '1008292230'.
                             There could be duplicate items in the list. Each new item id should match the item id
                             in the same position and be of the same product.
                payment_method_id: The payment method id to pay or receive refund for the item price difference,
                                 such as 'gift_card_0000000' or 'credit_card_0000000'. These can be looked up
                                 from the user or order details.

            Returns:
                Order: The order details after the exchange.

            Raises:
                ValueError: If the order is not delivered.
                ValueError: If the items to be exchanged do not exist.
                ValueError: If the new items do not exist or do not match the old items.
                ValueError: If the number of items to be exchanged does not match.
            """
            return self._tool_callable(
                "exchange_delivered_order_items",
                order_id=order_id,
                item_ids=item_ids,
                new_item_ids=new_item_ids,
                payment_method_id=payment_method_id,
            )

        def find_user_id_by_name_zip(first_name: str, last_name: str, zip: str) -> str:
            """Find user id by first name, last name, and zip code. If the user is not found, the function
            will return an error message. By default, find user id by email, and only call this function
            if the user is not found by email or cannot remember email.

            Args:
                first_name: The first name of the customer, such as 'John'.
                last_name: The last name of the customer, such as 'Doe'.
                zip: The zip code of the customer, such as '12345'.

            Returns:
                str: The user id if found, otherwise an error message.

            Raises:
                ValueError: If the user is not found.
            """
            return self._tool_callable(
                "find_user_id_by_name_zip", first_name=first_name, last_name=last_name, zip=zip
            )

        def find_user_id_by_email(email: str) -> str:
            """Find user id by email. If the user is not found, the function will return an error message.

            Args:
                email: The email of the user, such as 'something@example.com'.

            Returns:
                str: The user id if found, otherwise an error message.

            Raises:
                ValueError: If the user is not found.
            """
            return self._tool_callable("find_user_id_by_email", email=email)

        def get_order_details(order_id: str) -> Order:
            """Get the status and details of an order.

            Args:
                order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.

            Returns:
                Order: The order details.

            Raises:
                ValueError: If the order is not found.
            """
            return self._tool_callable("get_order_details", order_id=order_id)

        def get_product_details(product_id: str) -> Product:
            """Get the inventory details of a product.

            Args:
                product_id: The product id, such as '6086499569'. Be careful the product id is different from the item id.

            Returns:
                Product: The product details.

            Raises:
                ValueError: If the product is not found.
            """
            return self._tool_callable("get_product_details", product_id=product_id)

        def get_user_details(user_id: str) -> User:
            """Get the details of a user, including their orders.

            Args:
                user_id: The user id, such as 'sara_doe_496'.

            Returns:
                User: The user details.

            Raises:
                ValueError: If the user is not found.
            """
            return self._tool_callable("get_user_details", user_id=user_id)

        def list_all_product_types() -> str:
            """List the name and product id of all product types.
            Each product type has a variety of different items with unique item ids and options.
            There are only 50 product types in the store.

            Returns:
                str: A JSON string mapping product names to their product IDs, sorted alphabetically by name.
            """
            return self._tool_callable("list_all_product_types")

        def modify_pending_order_address(
            order_id: str,
            address1: str,
            address2: str,
            city: str,
            state: str,
            country: str,
            zip: str,
        ) -> Order:
            """Modify the shipping address of a pending order. The agent needs to explain the modification detail and ask for explicit user confirmation (yes/no) to proceed.

            Args:
                order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.
                address1: The first line of the address, such as '123 Main St'.
                address2: The second line of the address, such as 'Apt 1' or ''.
                city: The city, such as 'San Francisco'.
                state: The state, such as 'CA'.
                country: The country, such as 'USA'.
                zip: The zip code, such as '12345'.

            Returns:
                Order: The order details after the modification.

            Raises:
                ValueError: If the order is not pending.
            """
            return self._tool_callable(
                "modify_pending_order_address",
                order_id=order_id,
                address1=address1,
                address2=address2,
                city=city,
                state=state,
                country=country,
                zip=zip,
            )

        def modify_pending_order_items(
            order_id: str,
            item_ids: List[str],
            new_item_ids: List[str],
            payment_method_id: str,
        ) -> Order:
            """Modify items in a pending order to new items of the same product type. For a pending order, this function can only be called once. The agent needs to explain the exchange detail and ask for explicit user confirmation (yes/no) to proceed.

            Args:
                order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.
                item_ids: The item ids to be modified, each such as '1008292230'. There could be duplicate items in the list.
                new_item_ids: The item ids to be modified for, each such as '1008292230'. There could be duplicate items in the list. Each new item id should match the item id in the same position and be of the same product.
                payment_method_id: The payment method id to pay or receive refund for the item price difference, such as 'gift_card_0000000' or 'credit_card_0000000'. These can be looked up from the user or order details.

            Returns:
                Order: The order details after the modification.

            Raises:
                ValueError: If the order is not pending.
                ValueError: If the items to be modified do not exist.
                ValueError: If the new items do not exist or do not match the old items.
                ValueError: If the number of items to be modified does not match.
            """
            return self._tool_callable(
                "modify_pending_order_items",
                order_id=order_id,
                item_ids=item_ids,
                payment_method_id=payment_method_id,
                new_item_ids=new_item_ids,
            )

        def modify_pending_order_payment(
            order_id: str,
            payment_method_id: str,
        ) -> Order:
            """Modify the payment method of a pending order. The agent needs to explain the modification detail and ask for explicit user confirmation (yes/no) to proceed.

            Args:
                order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.
                payment_method_id: The payment method id to pay or receive refund for the item price difference, such as 'gift_card_0000000' or 'credit_card_0000000'. These can be looked up from the user or order details.

            Returns:
                Order: The order details after the modification.

            Raises:
                ValueError: If the order is not pending.
                ValueError: If the payment method does not exist.
                ValueError: If the payment history has more than one payment.
                ValueError: If the new payment method is the same as the current one.
            """
            return self._tool_callable(
                "modify_pending_order_payment",
                order_id=order_id,
                payment_method_id=payment_method_id,
            )

        def modify_user_address(
            user_id: str,
            address1: str,
            address2: str,
            city: str,
            state: str,
            country: str,
            zip: str,
        ) -> User:
            """Modify the default address of a user. The agent needs to explain the modification detail and ask for explicit user confirmation (yes/no) to proceed.

            Args:
                user_id: The user id, such as 'sara_doe_496'.
                address1: The first line of the address, such as '123 Main St'.
                address2: The second line of the address, such as 'Apt 1' or ''.
                city: The city, such as 'San Francisco'.
                state: The state, such as 'CA'.
                country: The country, such as 'USA'.
                zip: The zip code, such as '12345'.

            Returns:
                User: The user details after the modification.

            Raises:
                ValueError: If the user is not found.
            """
            return self._tool_callable(
                "modify_user_address",
                user_id=user_id,
                address1=address1,
                address2=address2,
                city=city,
                state=state,
                country=country,
                zip=zip,
            )

        def return_delivered_order_items(
            order_id: str,
            item_ids: List[str],
            payment_method_id: str,
        ) -> Order:
            """Return some items of a delivered order.
            The order status will be changed to 'return requested'.
            The agent needs to explain the return detail and ask for explicit user confirmation (yes/no) to proceed.
            The user will receive follow-up email for how and where to return the item.

            Args:
                order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.
                item_ids: The item ids to be returned, each such as '1008292230'. There could be duplicate items in the list.
                payment_method_id: The payment method id to pay or receive refund for the item price difference, such as 'gift_card_0000000' or 'credit_card_0000000'.
                                 These can be looked up from the user or order details.

            Returns:
                Order: The order details after requesting the return.

            Raises:
                ValueError: If the order is not delivered.
                ValueError: If the payment method is not the original payment method or a gift card.
                ValueError: If the items to be returned do not exist.
            """
            return self._tool_callable(
                "return_delivered_order_items",
                order_id=order_id,
                item_ids=item_ids,
                payment_method_id=payment_method_id,
            )

        def transfer_to_human_agents(summary: str) -> str:
            """
            Transfer the user to a human agent, with a summary of the user's issue.
            Only transfer if
             -  the user explicitly asks for a human agent
             -  given the policy and the available tools, you cannot solve the user's issue.

            Args:
                summary: A summary of the user's issue.

            Returns:
                A message indicating the user has been transferred to a human agent.
            """
            return self._tool_callable("transfer_to_human_agents", summary=summary)

        tool_registry = {
            "calculate": calculate,
            "cancel_pending_order": cancel_pending_order,
            "exchange_delivered_order_items": exchange_delivered_order_items,
            "find_user_id_by_name_zip": find_user_id_by_name_zip,
            "find_user_id_by_email": find_user_id_by_email,
            "get_order_details": get_order_details,
            "get_product_details": get_product_details,
            "get_user_details": get_user_details,
            "list_all_product_types": list_all_product_types,
            "modify_pending_order_address": modify_pending_order_address,
            "modify_pending_order_items": modify_pending_order_items,
            "modify_pending_order_payment": modify_pending_order_payment,
            "modify_user_address": modify_user_address,
            "return_delivered_order_items": return_delivered_order_items,
            "transfer_to_human_agents": transfer_to_human_agents,
        }
        self.tool_registry = tool_registry

        with open(os.environ["MODEL_NAME"]) as file:
            llm_config_json = file.read()
        deserializer = AgentSpecDeserializer()
        llm_config = deserializer.from_json(llm_config_json)
        agent = Agent(
            name="tau2_bench_agent",
            llm_config=llm_config,
            system_prompt=SYSTEM_PROMPT.format(
                domain_policy=self.domain_policy, agent_instruction=AGENT_INSTRUCTION
            ),
            tools=[self._adapt_tool_to_agentspec(tool) for tool in self.tools],
        )
        agent_as_yaml = AgentSpecSerializer().to_yaml(agent)

        RUNTIME_CLASS_IMPORT_PATH = os.getenv("RUNTIME_CLASS_IMPORT_PATH")
        runtime_module_import_path, runtime_classname = RUNTIME_CLASS_IMPORT_PATH.rsplit(".", 1)
        runtime_module = __import__(runtime_module_import_path)
        agent_spec_runtime_loader_cls = getattr(runtime_module, runtime_classname)
        runnable = agent_spec_runtime_loader_cls.load(agent_as_yaml, tool_registry=tool_registry)
        runnable.start()
        return AgentSpecAgentState(runnable)

    def _tool_callable(self, tool_name: str, **kwargs: Any) -> Any:
        print("Calling tool {} with arguments: {}".format(tool_name, kwargs))
        if not isinstance(kwargs, dict):
            raise RuntimeError(f"kwargs should be a dict.")

        def safe_value(val):
            if isinstance(val, type):
                return None
            return val

        tool_call = ToolCall(
            id="",
            name=tool_name,
            arguments={k: safe_value(v) for k, v in kwargs.items()},
            requestor="assistant",
        )
        agent_message = AssistantMessage(
            role="assistant",
            tool_calls=[tool_call],
        )
        self.orchestrator.trajectory.append(agent_message)
        tool_message = self.environment.get_response(tool_call)
        self.orchestrator.trajectory.append(tool_message)
        return tool_message.content

    def _adapt_tool_to_agentspec(self, tool: Tool) -> ServerTool:
        openai_schema = tool.openai_schema.get("function")
        return ServerTool(
            name=tool.name,
            description=self.tool_registry[tool.name].__doc__,  # openai_schema["description"],
            inputs=[
                self._adapt_param_to_agentspec(field_name, field)
                for field_name, field in tool.params.model_fields.items()
            ],
        )

    def _adapt_param_to_agentspec(self, field_name: str, field):
        # TODO ??? This could use "to open ai schema"
        if field.annotation == str:
            return StringProperty(title=field_name, description=field.description)
        elif field.annotation == List[str]:
            return ListProperty(
                title=field_name,
                description=field.description,
                item_type=StringProperty(title="inner_list_type"),
            )
        else:
            raise NotImplementedError(f"No support for field: {field}")
