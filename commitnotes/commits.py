"""Reading conventional commits out of a git repository.

The parser is deliberately forgiving: a commit whose message does not follow
the convention is still a commit, it just lands under "Other changes"
instead of disappearing.
"""

import re
import subprocess
from typing import List, NamedTuple, Optional, Sequence, Tuple

# The order sections appear in a release note.
TYPES = (
    "feat",
    "fix",
    "perf",
    "refactor",
    "docs",
    "style",
    "test",
    "build",
    "ci",
    "chore",
)

# Section titles, keyed by commit type.
TITLES = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "perf": "Performance",
    "refactor": "Refactoring",
    "docs": "Documentation",
    "style": "Styling",
    "test": "Tests",
    "build": "Build",
    "ci": "CI",
    "chore": "Chores",
    "other": "Other Changes",
}

# type(scope)!: subject
HEADER = re.compile(
    r"^(?P<type>[A-Za-z]+)"
    r"(?:\((?P<scope>[^()]*)\))?"
    r"(?P<breaking>!)?"
    r":\s*(?P<subject>.+)$"
)

# A breaking change announced in the body.
BREAKING_FOOTER = re.compile(
    r"^BREAKING[ -]CHANGE:\s*(?P<text>.+)$", re.MULTILINE
)

# The record separator used with git's %x1f and %x1e placeholders.
UNIT = "\x1f"
RECORD = "\x1e"


class Entry(NamedTuple):
    """One commit, as the notes need it."""

    sha: str
    kind: str
    scope: str
    subject: str
    body: str
    breaking: bool
    breaking_text: str


class GitError(RuntimeError):
    pass


def run_git(args: Sequence[str], cwd: Optional[str] = None) -> str:
    """Runs git and returns its output. A failure raises GitError."""
    try:
        done = subprocess.run(
            ["git", *args],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as error:  # pragma: no cover - git is required
        raise GitError("git is not installed") from error
    if done.returncode != 0:
        message = done.stderr.decode("utf-8", "replace").strip()
        raise GitError(message or "git failed")
    return done.stdout.decode("utf-8", "replace")


def is_repository(cwd: Optional[str] = None) -> bool:
    """Whether the directory is inside a git work tree."""
    try:
        run_git(["rev-parse", "--is-inside-work-tree"], cwd)
    except GitError:
        return False
    return True


def tag_list(cwd: Optional[str] = None) -> List[str]:
    """The repository's tags, newest first.

    `git describe` is not usable here: with two tags on the same commit it
    picks the lexicographically smaller one, and a release wants the newest.
    """
    try:
        raw = run_git(
            [
                "for-each-ref",
                "--format=%(refname:short)",
                "--sort=-creatordate",
                "--sort=-refname",
                "refs/tags",
            ],
            cwd,
        )
    except GitError:
        return []
    return [line.strip() for line in raw.splitlines() if line.strip()]


def latest_tag(cwd: Optional[str] = None) -> Optional[str]:
    """The newest tag, or None when the repository has none."""
    tags = tag_list(cwd)
    return tags[0] if tags else None


def read_commits(
    cwd: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    include_merges: bool = False,
    limit: Optional[int] = None,
) -> List[Entry]:
    """Reads commits newest first, optionally between two refs."""
    revision = ""
    if since and until:
        revision = f"{since}..{until}"
    elif since:
        revision = f"{since}.."
    elif until:
        revision = until
    args = ["log", "--no-color"]
    if not include_merges:
        args.append("--no-merges")
    args += ["--pretty=format:%H" + UNIT + "%s" + UNIT + "%b" + RECORD]
    if limit:
        args += ["--max-count", str(limit)]
    if revision:
        args.append(revision)
    raw = run_git(args, cwd)
    entries: List[Entry] = []
    for record in raw.split(RECORD):
        record = record.strip("\n")
        if not record.strip():
            continue
        fields = record.split(UNIT)
        if len(fields) < 3:
            continue
        sha, subject, body = fields[0], fields[1], fields[2]
        entries.append(make_entry(sha, subject, body))
    return entries


def make_entry(sha: str, subject: str, body: str) -> Entry:
    """Turns a raw commit message into an entry."""
    first = subject.splitlines()[0].strip() if subject.strip() else ""
    match = HEADER.match(first)
    if match:
        kind = match.group("type").lower()
        scope = (match.group("scope") or "").strip()
        subject_text = match.group("subject").strip()
        breaking = bool(match.group("breaking"))
    else:
        kind = "other"
        scope = ""
        subject_text = first
        breaking = False
    footer = BREAKING_FOOTER.search(body or "")
    breaking_text = footer.group("text").strip() if footer else ""
    if breaking_text:
        breaking = True
    if breaking and not breaking_text:
        breaking_text = subject_text
    return Entry(
        sha=sha.strip(),
        kind=kind,
        scope=scope,
        subject=subject_text,
        body=(body or "").strip(),
        breaking=breaking,
        breaking_text=breaking_text,
    )


def group(entries: Sequence[Entry]) -> "List[Tuple[str, List[Entry]]]":
    """Groups entries by type, in the order the sections should appear."""
    buckets: "dict[str, List[Entry]]" = {}
    for entry in entries:
        buckets.setdefault(entry.kind, []).append(entry)
    ordered: "List[Tuple[str, List[Entry]]]" = []
    for kind in TYPES:
        if kind in buckets:
            ordered.append((kind, buckets.pop(kind)))
    for kind in sorted(buckets):
        ordered.append((kind, buckets[kind]))
    return ordered


def unconventional(entries: Sequence[Entry]) -> List[Entry]:
    """Entries whose message does not follow the convention."""
    return [entry for entry in entries if entry.kind == "other"]
