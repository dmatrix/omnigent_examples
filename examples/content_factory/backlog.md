## contextual-policies
- status: READY
- title: How Omnigent's Contextual Policies Gate Data, Not Just Tools
- summary: Omnigent policies can evaluate runtime context and return ALLOW, ASK, or DENY decisions. This lets an agent distinguish safe work from actions that require a human decision.
- sources:
  - https://github.com/dmatrix/omnigent

## cross-harness-delegation
- status: READY
- title: One Supervisor, Multiple Harnesses: Omnigent Sub-Agent Delegation
- summary: An Omnigent supervisor can delegate focused work to sub-agents configured with different execution harnesses. The supervisor coordinates the workflow while each worker stays scoped to its assigned role.
- sources:
  - https://github.com/dmatrix/omnigent

## stateful-risk-scoring
- status: READY
- title: Stateful Risk Scoring for Slow-Burn Agent Sessions
- summary: Stateful policies can retain session context and accumulate risk across otherwise ordinary tool calls. A later outbound action can then be blocked when the combined session risk crosses a threshold.
- sources:
  - https://github.com/dmatrix/omnigent

## guarded-tools-escalation
- status: PUBLISHED
- title: Guarded Tools Turn Sensitive Agent Actions Into Approval Checkpoints
- summary: Omnigent's risk_score policy can escalate selected guarded_tools for human approval once accumulated session risk reaches a configured threshold, while ordinary workflow steps continue ungated.
- sources:
  - https://github.com/dmatrix/omnigent

## recurring-schedules
- status: READY
- title: Scheduled Agent Work
- summary: Omnigent supports recurring scheduled tasks defined with an RRULE.
- sources:
  - https://github.com/dmatrix/omnigent
