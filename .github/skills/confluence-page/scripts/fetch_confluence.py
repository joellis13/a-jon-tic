#!/usr/bin/env python3
"""Fetch and format a Confluence page for Copilot context."""

import sys
import os
import json
import base64
import urllib.request
import urllib.error
import urllib.parse
import re
from pathlib import Path

CONFLUENCE_BASE_URL = "https://joellis13.atlassian.net"


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

    elif node_type == "expand":
        title = node.get("attrs", {}).get("title", "")
        inner = "".join(adf_to_text(c, indent) for c in content)
        return f"<details><summary>{title}</summary>\n\n{inner}\n</details>\n"

    elif node_type == "panel":
        panel_type = node.get("attrs", {}).get("panelType", "info").upper()
        inner = "".join(adf_to_text(c, indent) for c in content)
        return f"> **[{panel_type}]** {inner.strip()}\n"

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


# ---------------------------------------------------------------------------
# Input parsing
# ---------------------------------------------------------------------------

def parse_input(raw):
    """
    Resolve user input to a Confluence page ID or search title.
    Returns ("id", "<page_id>") or ("title", "<search_title>").
    """
    raw = raw.strip()

    # Numeric ID
    if re.fullmatch(r"\d+", raw):
        return ("id", raw)

    # Full or partial Confluence URL — extract the numeric page ID
    # Handles: /wiki/spaces/SPACE/pages/123456789/...
    #          /wiki/x/<tiny-id>  (tiny links handled separately)
    id_match = re.search(r"/pages/(\d+)", raw)
    if id_match:
        return ("id", id_match.group(1))

    # Tiny link: /wiki/x/<base64-ish>
    tiny_match = re.search(r"/wiki/x/([A-Za-z0-9_-]+)", raw)
    if tiny_match:
        return ("tiny", tiny_match.group(1))

    # Everything else treated as a title search
    return ("title", raw)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _api_get(path, credentials, params=None):
    """Make an authenticated GET request to the Confluence REST API."""
    url = f"{CONFLUENCE_BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Basic {credentials}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def fetch_by_id(page_id, credentials):
    """Fetch a Confluence page by its numeric ID."""
    return _api_get(
        f"/wiki/api/v2/pages/{page_id}",
        credentials,
        params={"body-format": "atlas_doc_format", "get-draft": "false"},
    )


def fetch_by_tiny(tiny_id, credentials):
    """Fetch a Confluence page by its tiny link ID."""
    # Tiny links redirect — fetch the page via the legacy content API
    return _api_get(
        f"/wiki/rest/api/content/{tiny_id}",
        credentials,
        params={"expand": "body.atlas_doc_format,space,ancestors,version"},
    )


def search_by_title(title, credentials):
    """Search for a Confluence page by title using CQL."""
    cql = f'title = "{title}" AND type = page'
    result = _api_get(
        "/wiki/rest/api/content/search",
        credentials,
        params={"cql": cql, "expand": "space", "limit": 5},
    )
    results = result.get("results", [])
    if not results:
        return None, []
    if len(results) == 1:
        # Fetch full page with body
        return fetch_by_id(results[0]["id"], credentials), []
    # Multiple matches — return None and let caller report them
    return None, results


# ---------------------------------------------------------------------------
# Page formatter
# ---------------------------------------------------------------------------

def format_page(page, input_type="id"):
    """Format a Confluence page API response into clean markdown."""
    lines = []

    # --- Handle v2 API shape vs legacy shape ---
    if "title" in page:
        title = page.get("title", "(untitled)")
    else:
        title = "(untitled)"

    # Space
    space_name = ""
    if "spaceId" in page:
        space_name = page.get("spaceId", "")  # v2 only has ID; name resolved separately
    elif "space" in page:
        space_name = (page.get("space") or {}).get("name", "")

    # Version / last updated
    version = page.get("version") or {}
    updated_by = (version.get("authorId") or version.get("by", {}).get("displayName") or "")
    updated_at = (version.get("createdAt") or version.get("when") or "")[:10]
    version_number = version.get("number", "")

    # Page URL
    links = page.get("_links") or {}
    page_url = links.get("webui", "")
    if page_url and not page_url.startswith("http"):
        page_url = CONFLUENCE_BASE_URL + "/wiki" + page_url

    lines.append(f"# {title}")
    lines.append("")
    if space_name:
        lines.append(f"**Space:** {space_name}  ")
    if updated_at:
        lines.append(f"**Last Updated:** {updated_at}  ")
    if updated_by:
        lines.append(f"**Updated By:** {updated_by}  ")
    if version_number:
        lines.append(f"**Version:** {version_number}  ")
    if page_url:
        lines.append(f"**URL:** {page_url}  ")
    lines.append("")

    # --- Body ---
    body = page.get("body") or {}

    # v2 API: body.atlas_doc_format.value (JSON string)
    adf_value = (body.get("atlas_doc_format") or {}).get("value")

    if adf_value:
        if isinstance(adf_value, str):
            adf_value = json.loads(adf_value)
        lines.append(adf_to_text(adf_value))
    else:
        lines.append("*(no body content)*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_confluence.py <PAGE-ID | URL | 'Page Title'>", file=sys.stderr)
        sys.exit(1)

    raw_input = " ".join(sys.argv[1:])

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
    input_type, value = parse_input(raw_input)

    try:
        if input_type == "id":
            page = fetch_by_id(value, credentials)
        elif input_type == "tiny":
            page = fetch_by_tiny(value, credentials)
        else:
            page, candidates = search_by_title(value, credentials)
            if candidates:
                print(f"ERROR: Multiple pages found for '{value}'. Provide a page ID or URL instead:", file=sys.stderr)
                for c in candidates:
                    space = (c.get("space") or {}).get("key", "")
                    print(f"  [{c['id']}] ({space}) {c['title']}", file=sys.stderr)
                sys.exit(1)
            if page is None:
                print(f"ERROR: No page found matching title '{value}'.", file=sys.stderr)
                sys.exit(1)

    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"ERROR: Page not found — {raw_input}", file=sys.stderr)
        elif e.code == 401:
            print("ERROR: Authentication failed. Check JIRA_USER_EMAIL and JIRA_API_TOKEN.", file=sys.stderr)
        elif e.code == 403:
            print("ERROR: Access denied. You may not have permission to view this page.", file=sys.stderr)
        else:
            print(f"ERROR: Confluence API returned {e.code}: {e.read().decode()[:300]}", file=sys.stderr)
        sys.exit(1)

    response_path = Path(__file__).parent / "response.json"
    with open(response_path, "w", encoding="utf-8") as f:
        json.dump(page, f, indent=2)

    print(format_page(page, input_type))


if __name__ == "__main__":
    main()
