# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# isort:skip_file
# fmt: off
# mypy: ignore-errors
# docs-title: Code Example - How to Use AG-UI with Agent Spec

exit() # agui integration not installed
# .. start-##_Creating_the_agent
import os
from typing import Dict, Any

import dotenv
dotenv.load_dotenv()

from pyagentspec.agent import Agent
from pyagentspec.llms import OpenAiCompatibleConfig
from pyagentspec.tools import ServerTool
from pyagentspec.property import StringProperty
from pyagentspec.serialization import AgentSpecSerializer

def get_weather(location: str) -> Dict[str, Any]:
    """
    Get the weather for a given location.
    """
    import time
    time.sleep(1)  # simulate tool execution
    return {
        "temperature": 20,
        "conditions": "sunny",
        "humidity": 50,
        "wind_speed": 10,
        "feelsLike": 25,
    }

tool_input_property = StringProperty(
    title="location",
    description="The location to get the weather forecast. Must be a city/town name."
)
weather_result_property = StringProperty(title="weather_result")

weather_tool = ServerTool(
    name="get_weather",
    description="Get the weather for a given location.",
    inputs=[tool_input_property],
    outputs=[weather_result_property],
)

agent_llm = OpenAiCompatibleConfig(
    name="my_llm",
    model_id=os.environ.get("OPENAI_MODEL", "gpt-4o"),
    url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
)

agent = Agent(
    name="my_agent",
    llm_config=agent_llm,
    system_prompt="Based on the weather forecaset result and the user input, write a response to the user",
    tools=[weather_tool],
    human_in_the_loop=True,
)

backend_tool_rendering_agent_json = AgentSpecSerializer().to_json(agent)
tool_registry = {"get_weather": get_weather}
# .. end-##_Creating_the_agent
# .. start-##_Creating_the_app
import os
import importlib.util
import logging
from fastapi import APIRouter, FastAPI

from ag_ui_agentspec.agent import AgentSpecAgent
from ag_ui_agentspec.endpoint import add_agentspec_fastapi_endpoint

logger = logging.getLogger(__name__)
router = APIRouter()


def _is_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _mount(router: APIRouter):
    # LangGraph
    if _is_available("langgraph"):
        add_agentspec_fastapi_endpoint(
            app=router,
            agentspec_agent=AgentSpecAgent(
                backend_tool_rendering_agent_json,
                runtime="langgraph",
                tool_registry=tool_registry,
            ),
            path="/langgraph/backend_tool_rendering",
        )
    else:
        logger.info("LangGraph not available. Skipping LangGraph endpoints.")

    # Wayflow
    # The comment mentioned 'wayflowcore' specifically
    if _is_available("wayflowcore"):
        add_agentspec_fastapi_endpoint(
            app=router,
            agentspec_agent=AgentSpecAgent(
                backend_tool_rendering_agent_json,
                runtime="wayflow",
                tool_registry=tool_registry,
            ),
            path="/wayflow/backend_tool_rendering",
        )
    else:
        logger.info("Wayflow (wayflowcore) not available. Skipping Wayflow endpoints.")

# Create the Web App

app = FastAPI(title="Agent-Spec × AG-UI Examples")
_mount(router)
app.include_router(router)
port = int(os.getenv("PORT", "9003"))
# if __name__=="__main__":
#     import uvicorn
#     uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
# .. end-##_Creating_the_app
