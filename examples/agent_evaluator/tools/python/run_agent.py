"""Launch a target agent as a child session and send test prompts."""

from __future__ import annotations

from omnigent_client.tools import tool


@tool
def run_agent(agent_path: str, prompts: list[str]) -> str:
    """
    Launch an omnigent agent and send it a sequence of test prompts.

    This tool is informational — it returns instructions for the evaluator
    agent to execute via the builtin sys_session_create and sys_session_send
    tools, which handle the actual session lifecycle.

    :param agent_path: Path to the agent directory, e.g. "examples/telco_customer_agent/".
    :param prompts: List of test prompts to send to the agent.
    :returns: Step-by-step instructions for running the evaluation.
    """
    steps = [
        f"Target agent: {agent_path}",
        f"Test prompts ({len(prompts)}):",
    ]
    for i, prompt in enumerate(prompts, 1):
        steps.append(f"  {i}. {prompt}")

    steps.append("")
    steps.append("Execute these steps using your builtin tools:")
    steps.append(f'1. Call sys_session_create(config_path="{agent_path}", '
                 f'title="eval-target")')
    steps.append("2. For each prompt, call sys_session_send(session_id=<id>, "
                 "args=<prompt>) using the conversation_id from step 1")
    steps.append("3. Each sys_session_send returns the agent's response")
    steps.append("4. After all prompts, call collect_traces to get MLflow traces")
    steps.append("5. Call evaluate_traces to score the traces")
    steps.append("6. Optionally call check_policies to verify policy compliance")

    return "\n".join(steps)
