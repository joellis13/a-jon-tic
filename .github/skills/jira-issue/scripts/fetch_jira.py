#!/usr/bin/env python3
"""Fetch and format a Jira issue for Copilot context."""

import base64
import sys
import os
import json
import urllib.request
import urllib.error
from pathlib import Path

JIRA_BASE_URL = "https://joellis13.atlassian.net"


def load_env(env_path=None):
    """Load .env file into environment variables without overwriting existing ones."""
    if env_path is None:
        script_dir = Path(__file__).resolve().parent
        for parent in [script_dir] + list(script_dir.parents):
            candidate = parent / ".env"
            if candidate.exists():
                env_path = candidate
                break

    if env_path and Path(env_path).exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key, value)


# ---------------------------------------------------------------------------
# ADF → Markdown
# ---------------------------------------------------------------------------

def adf_to_text(node, indent=0):
    """Recursively convert an Atlassian Document Format node to markdown text."""
    if not node:
        return ""

    node_type = node.get("type", "")
    content = node.get("content", [])
    text = node.get("text", "")

    if node_type == "doc":
        return "\n".join(adf_to_text(c, indent) for c in content).strip()

    elif node_type == "paragraph":
        inner = "".join(adf_to_text(c, indent) for c in content)
        return inner + "\n"

    elif node_type == "text":
        marks = {m.get("type") for m in node.get("marks", [])}
        if "code" in marks:
            return f"`{text}`"
        if "bold" in marks and "em" in marks:
            return f"***{text}***"
        if "bold" in marks:
            return f"**{text}**"
        if "em" in marks:
            return f"*{text}*"
        if "strike" in marks:
            return f"~~{text}~~"
        if "link" in marks:
            for m in node.get("marks", []):
                if m.get("type") == "link":
                    href = m.get("attrs", {}).get("href", "")
                    return f"[{text}]({href})"
        return text

    elif node_type == "heading":
        level = node.get("attrs", {}).get("level", 1)
        inner = "".join(adf_to_text(c) for c in content)
        return "#" * level + " " + inner + "\n"

    elif node_type == "bulletList":
        lines = []
        for item in content:
            item_text = adf_to_text(item, indent + 1).rstrip()
            lines.append("  " * indent + "- " + item_text)
        return "\n".join(lines) + "\n"

    elif node_type == "orderedList":
        lines = []
        for i, item in enumerate(content, 1):
            item_text = adf_to_text(item, indent + 1).rstrip()
            lines.append("  " * indent + f"{i}. " + item_text)
        return "\n".join(lines) + "\n"

    elif node_type == "listItem":
        parts = [adf_to_text(c, indent).rstrip() for c in content]
        return " ".join(p for p in parts if p)

    elif node_type == "codeBlock":
        lang = node.get("attrs", {}).get("language", "")
        inner = "".join(adf_to_text(c) for c in content)
        return f"```{lang}\n{inner}\n```\n"

    elif node_type == "blockquote":
        inner = adf_to_text({"type": "doc", "content": content})
        return "\n".join("> " + line for line in inner.splitlines()) + "\n"

    elif node_type == "hardBreak":
        return "\n"

    elif node_type == "rule":
        return "\n---\n"

    elif node_type == "inlineCard":
        url = node.get("attrs", {}).get("url", "")
        return f"[{url}]({url})"

    elif node_type == "mention":
        return "@" + node.get("attrs", {}).get("text", "someone")

    elif node_type == "emoji":
        return node.get("attrs", {}).get("text", "")

    elif node_type == "table":
        return _adf_table_to_md(content)

    else:
        return "".join(adf_to_text(c, indent) for c in content)


def _adf_table_to_md(rows):
    """Convert ADF table rows to a markdown table."""
    md_rows = []
    for row in rows:
        cells = []
        for cell in row.get("content", []):
            cell_text = "".join(
                adf_to_text(c) for c in cell.get("content", [])
            ).strip().replace("\n", " ")
            cells.append(cell_text)
        md_rows.append("| " + " | ".join(cells) + " |")

    if len(md_rows) >= 1:
        col_count = md_rows[0].count("|") - 1
        md_rows.insert(1, "| " + " | ".join(["---"] * col_count) + " |")

    return "\n".join(md_rows) + "\n"


def _render_field(value):
    """Render an ADF field or plain string to text."""
    if isinstance(value, dict):
        return adf_to_text(value).strip()
    return str(value) if value else ""


# ---------------------------------------------------------------------------
# Issue formatter
# ---------------------------------------------------------------------------

def format_issue(issue):
    """Format a full Jira issue dict into clean markdown."""
    fields = issue.get("fields", {})
    key = issue.get("key", "")

    lines = []
    lines.append(f"# {key}: {fields.get('summary', '(no summary)')}")
    lines.append("")

    # --- Core metadata ---
    def field_name(f, attr="name"):
        return (fields.get(f) or {}).get(attr, "")

    lines.append(f"**Type:** {field_name('issuetype')}  ")
    lines.append(f"**Status:** {field_name('status')}  ")
    lines.append(f"**Priority:** {field_name('priority') or 'None'}  ")
    lines.append(f"**Project:** {field_name('project')}  ")
    lines.append(f"**Assignee:** {field_name('assignee', 'displayName') or 'Unassigned'}  ")
    lines.append(f"**Reporter:** {field_name('reporter', 'displayName') or 'Unknown'}  ")
    lines.append(f"**Created:** {(fields.get('created') or '')[:10]}  ")
    lines.append(f"**Updated:** {(fields.get('updated') or '')[:10]}  ")

    # Story points — try common custom field IDs
    for sp_field in ("customfield_10016", "customfield_10028", "customfield_10034"):
        sp = fields.get(sp_field)
        if sp is not None:
            lines.append(f"**Story Points:** {sp}  ")
            break

    # Labels
    labels = fields.get("labels") or []
    if labels:
        lines.append(f"**Labels:** {', '.join(labels)}  ")

    # Components
    components = [c.get("name", "") for c in (fields.get("components") or [])]
    if components:
        lines.append(f"**Components:** {', '.join(components)}  ")

    # Fix versions
    fix_versions = [v.get("name", "") for v in (fields.get("fixVersions") or [])]
    if fix_versions:
        lines.append(f"**Fix Versions:** {', '.join(fix_versions)}  ")

    # Sprint (customfield_10020 is standard for Jira Software)
    sprint_field = fields.get("customfield_10020")
    if sprint_field:
        if isinstance(sprint_field, list) and sprint_field:
            sprint_name = sprint_field[-1].get("name", "")
        elif isinstance(sprint_field, dict):
            sprint_name = sprint_field.get("name", "")
        else:
            sprint_name = ""
        if sprint_name:
            lines.append(f"**Sprint:** {sprint_name}  ")

    # Parent / Epic
    parent = fields.get("parent")
    if parent:
        parent_key = parent.get("key", "")
        parent_summary = (parent.get("fields") or {}).get("summary", "")
        lines.append(f"**Parent:** {parent_key} — {parent_summary}  ")

    epic_link = fields.get("customfield_10014")
    if epic_link and not parent:
        lines.append(f"**Epic Link:** {epic_link}  ")

    lines.append("")

    # --- Description ---
    description = fields.get("description")
    if description:
        lines.append("## Description")
        lines.append("")
        lines.append(_render_field(description))
        lines.append("")

    # --- Acceptance Criteria (common custom field IDs) ---
    for ac_field in ("customfield_10071", "customfield_10033", "customfield_10300", "customfield_10500"):
        ac = fields.get(ac_field)
        if ac:
            lines.append("## Acceptance Criteria")
            lines.append("")
            lines.append(_render_field(ac))
            lines.append("")
            break

    # --- Subtasks ---
    subtasks = fields.get("subtasks") or []
    if subtasks:
        lines.append("## Subtasks")
        lines.append("")
        for st in subtasks:
            st_key = st.get("key", "")
            st_fields = st.get("fields") or {}
            st_summary = st_fields.get("summary", "")
            st_status = (st_fields.get("status") or {}).get("name", "")
            lines.append(f"- **{st_key}** {st_summary} *(status: {st_status})*")
        lines.append("")

    # --- Linked Issues ---
    issue_links = fields.get("issuelinks") or []
    if issue_links:
        lines.append("## Linked Issues")
        lines.append("")
        for link in issue_links:
            link_type = (link.get("type") or {}).get("name", "")
            inward = link.get("inwardIssue")
            outward = link.get("outwardIssue")
            linked = inward or outward
            if linked:
                direction = "inward" if inward else "outward"
                l_key = linked.get("key", "")
                l_summary = (linked.get("fields") or {}).get("summary", "")
                l_status = ((linked.get("fields") or {}).get("status") or {}).get("name", "")
                lines.append(f"- **{link_type}** ({direction}): [{l_key}] {l_summary} *(status: {l_status})*")
        lines.append("")

    # --- Comments (last 3) ---
    comment_data = fields.get("comment") or {}
    comments = comment_data.get("comments") or []
    total_comments = comment_data.get("total", len(comments))
    if comments:
        lines.append(f"## Comments ({total_comments} total — showing last 3)")
        lines.append("")
        for comment in comments[-3:]:
            author = (comment.get("author") or {}).get("displayName", "Unknown")
            created = (comment.get("created") or "")[:10]
            body = comment.get("body")
            body_text = _render_field(body)
            lines.append(f"**{author}** ({created}):")
            lines.append(body_text.strip())
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_jira.py <ISSUE-KEY>", file=sys.stderr)
        sys.exit(1)

    issue_key = sys.argv[1].upper()

    load_env()

    user_email = os.environ.get("JIRA_USER_EMAIL", "")
    api_token = os.environ.get("JIRA_API_TOKEN", "")

    missing = [k for k, v in {
        "JIRA_USER_EMAIL": user_email,
        "JIRA_API_TOKEN": api_token,
    }.items() if not v]

    if missing:
        print(f"ERROR: Missing required env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    credentials = base64.b64encode(f"{user_email}:{api_token}".encode()).decode()
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Basic {credentials}",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req) as response:
            issue = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"ERROR: Issue {issue_key} not found.", file=sys.stderr)
        elif e.code == 401:
            print("ERROR: Authentication failed. Check JIRA_USER_EMAIL and JIRA_API_TOKEN.", file=sys.stderr)
        else:
            print(f"ERROR: Jira API returned {e.code}: {e.read().decode()[:300]}", file=sys.stderr)
        sys.exit(1)

    response_path = Path(__file__).parent / "response.json"
    with open(response_path, "w", encoding="utf-8") as f:
        json.dump(issue, f, indent=2)

    print(format_issue(issue))


if __name__ == "__main__":
    main()
