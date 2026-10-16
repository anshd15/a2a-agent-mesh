# Security

Please report vulnerabilities privately through GitHub's "Report a vulnerability" (Security tab) rather than a public issue.

Known limits of the current demo setup:
- Specialists accept unauthenticated A2A requests; put them behind auth (e.g. Cloud Run ID tokens) before exposing them publicly.
- PII masking applies to what the planner sends to Gemini; delegated messages to remote agents are not masked yet.
- Guardrails are regex-based and will not catch every prompt-injection phrasing.
