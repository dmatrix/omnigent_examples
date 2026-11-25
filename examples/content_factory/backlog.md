## build-content-factories
- status: APPROVED
- title: How Omnigent Facilitates Building Agentic Content Factories
- summary: Use the content_factory example as a reference for building a factory on Omnigent primitives: a supervisor that delegates to sub-agents running on different harnesses, a custom stateful policy that gates irreversible actions behind human approval, tools auto-discovered from tools/python/, and a two-tier artifact layout separating free staging work from anything that ships outward.
- sources:
  - https://github.com/omnigent-ai/omnigent
  - https://github.com/dmatrix/omnigent_examples/tree/main/examples/content_factory

## contextual-policies
- status: PUBLISHED
- title: How Omnigent's Contextual Policies Gate Data, Not Just Tools
- summary: Omnigent policies can evaluate runtime context and return ALLOW, ASK, or DENY decisions. This lets an agent distinguish safe work from actions that require a human decision.
- sources:
  - https://github.com/omnigent-ai/omnigent

## cross-harness-delegation
- status: READY
- title: One Supervisor, Multiple Harnesses: Omnigent Sub-Agent Delegation
- summary: An Omnigent supervisor can delegate focused work to sub-agents configured with different execution harnesses. The supervisor coordinates the workflow while each worker stays scoped to its assigned role.
- sources:
  - https://github.com/omnigent-ai/omnigent

## stateful-risk-scoring
- status: READY
- title: Stateful Risk Scoring for Slow-Burn Agent Sessions
- summary: Stateful policies can retain session context and accumulate risk across otherwise ordinary tool calls. A later outbound action can then be blocked when the combined session risk crosses a threshold.
- sources:
  - https://github.com/omnigent-ai/omnigent

## guarded-tools-escalation
- status: READY
- title: Guarded Tools Turn Sensitive Agent Actions Into Approval Checkpoints
- summary: Omnigent's risk_score policy can escalate selected guarded_tools for human approval once accumulated session risk reaches a configured threshold, while ordinary workflow steps continue ungated.
- sources:
  - https://github.com/omnigent-ai/omnigent

## recurring-schedules
- status: READY
- title: Scheduled Agent Work and Tasks
- summary: Omnigent supports recurring scheduled tasks defined with an RRULE.
- sources:
  - https://github.com/omnigent-ai/omnigent

## mlflow-auto-issue-detection
- status: PUBLISHED
- title: Scheduled Agent Work
- summary: A common refrain among developers who are increasingly using coding agents is how to tackle large volume of traces? How can we unburden subject matter experts to plough through all the traces? The MLflow auto issue detection mitigates this by using agents to categorize issues and detect faulty patterns. Explain why this is important and how you can use MLflow to use it.

- sources:
  - https://github.com/mlflow/
  - https://mlflow.org
  - https://mlflow.org/docs/latest/genai/eval-monitor/ai-insights/detect-issues/



