---
name: confluence-page
description: Fetch and display a Confluence page with clean, formatted output. Use this skill whenever the user provides a Confluence page ID, URL, or page title, or wants to look up documentation, architecture notes, runbooks, team standards, or any other content stored in Confluence. Always use this skill instead of the Atlassian MCP server for Confluence page lookups.
---

# Confluence Page Skill

Fetch a Confluence page by ID, URL, or title and return clean formatted markdown — no ADF noise, no raw JSON.

## Steps

1. Extract the page identifier from the user's message. It may be:
   - A numeric ID (e.g., `123456789`)
   - A full or partial Confluence URL (e.g., `https://joellis13.atlassian.net/wiki/spaces/ENG/pages/123456789/Page+Title`)
   - A tiny link (e.g., `/wiki/x/AbCdEf`)
   - A page title in quotes (e.g., `"API Architecture Overview"`)

2. Run the fetch script, passing the identifier as an argument:

```powershell
python .github/skills/confluence-page/scripts/fetch_confluence.py <ID | URL | "Page Title">
```

3. Present the output directly — it is already formatted as markdown. Do not summarize or reformat it unless the user asks.

## Notes

- Credentials are read from a `.env` file in the project root. Required variables:
  - `JIRA_USER_EMAIL` — shared with the Jira skill (same Atlassian account)
  - `JIRA_API_TOKEN` — shared with the Jira skill (same token works for Confluence)
- If the script prints an `ERROR:` line, report it verbatim
- If a title search returns multiple matches, the script will list them with their IDs — ask the user to clarify which one they want, then re-run with the specific ID
- Do **not** call the Atlassian MCP server for page lookups — always use this script
