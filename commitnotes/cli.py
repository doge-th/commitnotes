"""Command line entry point."""

import argparse
import sys
from typing import List, Optional

from . import __version__
from .commits import (
    GitError,
    Entry,
    is_repository,
    latest_tag,
    read_commits,
    tag_list,
    unconventional,
)
from .render import render_json, render_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="commitnotes",
        description="Release notes from conventional commits, with no dependencies.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="repository to read (default: the current directory)",
    )
    parser.add_argument(
        "--since",
        metavar="REF",
        default=None,
        help="start after this tag or commit (default: the latest tag)",
    )
    parser.add_argument(
        "--until",
        metavar="REF",
        default=None,
        help="stop at this tag or commit",
    )
    parser.add_argument(
        "--tag",
        metavar="TAG",
        default=None,
        help="notes for this version: everything up to the tag",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="use every commit, not just the ones since the latest tag",
    )
    parser.add_argument(
        "--include-merges",
        action="store_true",
        help="include merge commits",
    )
    parser.add_argument(
        "--breaking-only",
        action="store_true",
        help="only the breaking changes",
    )
    parser.add_argument(
        "--no-scope",
        action="store_true",
        help="leave the scope out of every line",
    )
    parser.add_argument(
        "--no-hashes",
        action="store_true",
        help="leave the commit hash out of every line",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print JSON instead of Markdown",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 when a commit message does not follow the convention",
    )
    parser.add_argument(
        "--list-tags",
        action="store_true",
        help="print the repository's tags, newest first",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    options = parser.parse_args(argv)
    path = options.path
    if not is_repository(path):
        sys.stderr.write(f"commitnotes: {path} is not a git repository\n")
        return 2
    if options.list_tags:
        for tag in tag_list(path):
            print(tag)
        return 0
    since = options.since
    until = options.until
    version = None
    if options.tag:
        version = options.tag
        until = options.tag
    elif not options.all and since is None:
        since = latest_tag(path)
    entries: List[Entry] = read_commits(
        path,
        since=since,
        until=until,
        include_merges=options.include_merges,
    )
    if options.check:
        offenders = unconventional(entries)
        for entry in offenders:
            sys.stderr.write(
                "commitnotes: %s does not follow the convention: %s\n"
                % (entry.sha[:7], entry.subject or "(no subject)")
            )
        if offenders:
            sys.stderr.write(
                "commitnotes: %d commit(s) are not conventional\n" % len(offenders)
            )
            return 1
        return 0
    if options.json:
        print(render_json(entries, version=version, since=since, breaking_only=options.breaking_only))
    else:
        print(
            render_markdown(
                entries,
                version=version,
                since=since,
                show_scopes=not options.no_scope,
                show_hashes=not options.no_hashes,
                breaking_only=options.breaking_only,
            ),
            end="",
        )
    return 0


def run(argv: Optional[List[str]] = None) -> int:
    """main, with git failures reported rather than raised."""
    try:
        return main(argv)
    except GitError as error:
        sys.stderr.write(f"commitnotes: {error}\n")
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run())
