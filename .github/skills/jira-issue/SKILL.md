---
name: jira-issue
description: Fetch and display a Jira issue with clean, formatted output. Use this skill whenever the user mentions a Jira issue key (e.g., ABC-123, PROJ-456), asks about a story, ticket, bug, or task in Jira, or wants to look up requirements, status, assignee, description, or any other details for a Jira item. Always use this skill instead of the Atlassian MCP server for Jira issue lookups.
---

# Jira Issue Skill

Fetch a Jira issue by its key and return clean, formatted markdown — no raw JSON, no ADF noise.

## Steps

1. Extract the issue key from the user's message (e.g., `ABC-123`)
2. Run the fetch script:

```powershell
python .github/skills/jira-issue/scripts/fetch_jira.py <ISSUE-KEY>
```

3. Present the output directly — it is already formatted as markdown. Do not summarize or reformat it further unless the user asks.

## Notes

- Credentials are read from a `.env` file in the project root. Required variables:
  - `JIRA_USER_EMAIL` — the email associated with the API token
  - `JIRA_API_TOKEN` — generated at https://id.atlassian.com/manage-profile/security/api-tokens
- If the script prints an `ERROR:` line, report it verbatim so the user can diagnose it
- Do **not** call the Atlassian MCP server for issue lookups — always use this script
