# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# mypy: ignore-errors

"""
Run the Tau2 Benchmark by after some monkey patching to include AgentSpec models.
"""
from typing import Optional

from loguru import logger
from tau2 import run
from tau2.agent.agent_spec_agent import AgentSpecAgent
from tau2.agent.llm_agent import LLMSoloAgent
from tau2.cli import main
from tau2.data_model.simulation import SimulationRun
from tau2.data_model.tasks import Task
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation
from tau2.orchestrator.orchestrator import Orchestrator
from tau2.registry import registry
from tau2.user.user_simulator import DummyUser


def patched_run_task(
    domain: str,
    task: Task,
    agent: str,
    user: str,
    llm_agent: Optional[str] = None,
    llm_args_agent: Optional[dict] = None,
    llm_user: Optional[str] = None,
    llm_args_user: Optional[dict] = None,
    max_steps: int = 100,
    max_errors: int = 10,
    evaluation_type: EvaluationType = EvaluationType.ALL,
    seed: Optional[int] = None,
    enforce_communication_protocol: bool = False,
) -> SimulationRun:
    """
    Monkey patch of Tau2's run_task to include AgentSpec model.
    If llm_as_judge is True, the LLM will be used to annotate the simulation run.
    Calculates the reward for the simulation run.
    Args:
        domain (str): The domain to run the simulation on.
        task (Task): The task to run.
        agent (str): The agent to run the simulation on.
        user (str): The user to run the simulation on.
        llm_agent (str): The model to use for the agent.
        llm_args_agent (dict): The arguments to pass to the LLM for the agent.
        llm_user (str): The model to use for the user.
        llm_args_user (dict): The arguments to pass to the LLM for the user.
        max_steps (int): The maximum number of steps to run the simulation.
        max_errors (int): The maximum number of errors to allow in the simulation.
        evaluation_type (EvaluationType): The type of evaluation to use.
        seed (int): The seed to use for the simulation.
        enforce_communication_protocol (bool): Whether to enforce communication protocol rules.
    Returns:
        The simulation run.
    """

    if max_steps <= 0:
        raise ValueError("Max steps must be greater than 0")
    if max_errors <= 0:
        raise ValueError("Max errors must be greater than 0")
    global registry
    logger.info(
        f"STARTING SIMULATION: Domain: {domain}, Task: {task.id}, Agent: {agent}, User: {user}"
    )
    environment_constructor = registry.get_env_constructor(domain)
    environment = environment_constructor()
    AgentConstructor = registry.get_agent_constructor(agent)

    solo_mode = False
    if issubclass(AgentConstructor, AgentSpecAgent):
        agent = AgentConstructor(
            tools=environment.get_tools(),
            domain_policy=environment.get_policy(),
            environment=environment,
        )
    else:
        agent = AgentConstructor(
            tools=environment.get_tools(),
            domain_policy=environment.get_policy(),
        )
    try:
        user_tools = environment.get_user_tools()
    except Exception:
        user_tools = None

    UserConstructor = registry.get_user_constructor(user)
    if issubclass(UserConstructor, DummyUser):
        assert isinstance(agent, LLMSoloAgent), "Dummy user can only be used with solo agent"

    user = UserConstructor(
        tools=user_tools,
        instructions=str(task.user_scenario),
        llm=llm_user,
        llm_args=llm_args_user,
    )

    orchestrator = Orchestrator(
        domain=domain,
        agent=agent,
        user=user,
        environment=environment,
        task=task,
        max_steps=max_steps,
        max_errors=max_errors,
        seed=seed,
        solo_mode=solo_mode,
        validate_communication=enforce_communication_protocol,
    )
    if isinstance(agent, AgentSpecAgent):
        agent.set_orchestrator(orchestrator)

    # If you want to start tracing on the benchmarks, you can wrap the orchestrator.run call
    # using the following lines and adding the span processors you want to execute

    # from pyagentspec.tracing.trace import Trace
    # with Trace(name="tau2-bench", span_processors=[...]) as trace:

    simulation = orchestrator.run()

    reward_info = evaluate_simulation(
        domain=domain,
        task=task,
        simulation=simulation,
        evaluation_type=evaluation_type,
        solo_mode=solo_mode,
    )

    simulation.reward_info = reward_info

    logger.info(
        f"FINISHED SIMULATION: Domain: {domain}, Task: {task.id}, Agent: {agent.__class__.__name__}, "
        f"User: {user.__class__.__name__}. Reward: {reward_info.reward}"
    )
    return simulation


if __name__ == "__main__":
    try:
        registry.register_agent(AgentSpecAgent, "agentspec_agent")
    except:
        ...
    run.run_task = patched_run_task
    main()
