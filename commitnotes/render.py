"""Rendering release notes as Markdown or JSON."""

import json
from typing import List, Optional, Sequence

from .commits import Entry, TITLES, group


def _line(entry: Entry, show_scopes: bool, show_hashes: bool) -> str:
    parts = []
    if show_scopes and entry.scope:
        parts.append(f"**{entry.scope}:**")
    parts.append(entry.subject)
    line = "- " + " ".join(parts)
    if show_hashes and entry.sha:
        line += f" ({entry.sha[:7]})"
    return line


def render_markdown(
    entries: Sequence[Entry],
    version: Optional[str] = None,
    since: Optional[str] = None,
    show_scopes: bool = True,
    show_hashes: bool = False,
    breaking_only: bool = False,
    empty_note: str = "No changes.",
) -> str:
    """Renders the notes as a Markdown document."""
    lines: List[str] = []
    if version:
        lines.append(f"# {version}")
        lines.append("")
    if since:
        lines.append(f"Changes since {since}.")
        lines.append("")
    selected = [entry for entry in entries if entry.breaking] if breaking_only else list(entries)
    if breaking_only:
        lines.append("## Breaking Changes")
        lines.append("")
        if not selected:
            lines.append(empty_note)
        for entry in selected:
            lines.append(_line(entry, show_scopes, show_hashes))
        lines.append("")
    else:
        for kind, bucket in group(selected):
            lines.append(f"## {TITLES.get(kind, kind.title())}")
            lines.append("")
            for entry in bucket:
                lines.append(_line(entry, show_scopes, show_hashes))
            lines.append("")
    if not selected and not breaking_only:
        lines.append(empty_note)
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def render_json(
    entries: Sequence[Entry],
    version: Optional[str] = None,
    since: Optional[str] = None,
    breaking_only: bool = False,
) -> str:
    """Renders the notes as a JSON document."""
    selected = [entry for entry in entries if entry.breaking] if breaking_only else list(entries)
    document = {
        "version": version,
        "since": since,
        "commits": [
            {
                "sha": entry.sha,
                "type": entry.kind,
                "scope": entry.scope,
                "subject": entry.subject,
                "breaking": entry.breaking,
                "breaking_text": entry.breaking_text,
            }
            for entry in selected
        ],
        "counts": {
            kind: len(bucket) for kind, bucket in group(selected)
        },
    }
    return json.dumps(document, indent=2)
