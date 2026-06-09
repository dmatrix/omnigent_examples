---
name: customer-report
description: Generate a structured telco customer report with PII redaction guidelines.
---

When asked to produce a customer report:
1. State which data sources were queried (customers, billing, subscriptions, devices)
2. Summarize by plan tier (how many customers per tier, average revenue)
3. Highlight churn risk: customers with past_due status, auto_renew=false, or contract ending within 90 days
4. Device breakdown: top devices by make/model, installment payment totals
5. Revenue metrics: total MRR, average revenue per user (ARPU), discount impact
6. Redaction rules: replace full email with "s***@gmail.com", show only last 4 of phone number, never show SSN
7. Flag any customers ported from competitors (business intelligence)
8. End with recommended actions (retention outreach, upgrade opportunities)
