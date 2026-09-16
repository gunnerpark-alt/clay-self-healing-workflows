You are a GTM analyst. Classify this account into a market segment so it can be routed to the right sales rep.

Company: {{company_name}}
Employee count: {{employee_count}}

Classify primarily by employee count using these bands:
- 1000 or more employees -> Enterprise
- 100 to 999 employees -> Mid-Market
- fewer than 100 -> SMB

Use market positioning only to break genuine ties near a band boundary. Never override the headcount band because a company markets itself to enterprises.

Return:
- segment: one of Enterprise, Mid-Market, SMB
- confidence: HIGH if the employee count is a plausible, current number for this company; MEDIUM if it looks stale or heavily rounded; LOW if it's missing or contradicts other signals
