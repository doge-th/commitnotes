import json
import os
import subprocess
import tempfile
import unittest

from commitnotes.cli import main, run
from commitnotes.commits import (
    group,
    is_repository,
    latest_tag,
    make_entry,
    read_commits,
    unconventional,
)
from commitnotes.render import render_json, render_markdown


def git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, stdout=subprocess.PIPE
    ).stdout.decode()


def commit(repo, message, filename="file.txt", content=None):
    path = os.path.join(repo, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as handle:
        handle.write((content or message) + "\n")
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=Tester", "-c", "user.email=t@example.com", "commit", "-m", message)


def make_repo(messages, tags=(), tag_after_first=False):
    directory = tempfile.mkdtemp(prefix="commitnotes-")
    git(directory, "init", "-q", "-b", "main")
    git(directory, "config", "user.name", "Tester")
    git(directory, "config", "user.email", "t@example.com")
    for index, message in enumerate(messages):
        commit(directory, message, filename="f%d.txt" % index)
        if tag_after_first and index == 0:
            for tag in tags:
                git(directory, "tag", tag)
            tags = ()
    for tag in tags:
        git(directory, "tag", tag)
    return directory


class Parsing(unittest.TestCase):
    def test_parses_type_scope_and_subject(self):
        entry = make_entry("abc123", "feat(parser): add a thing", "")
        self.assertEqual(entry.kind, "feat")
        self.assertEqual(entry.scope, "parser")
        self.assertEqual(entry.subject, "add a thing")
        self.assertFalse(entry.breaking)

    def test_bang_marks_a_breaking_change(self):
        entry = make_entry("abc123", "feat(api)!: drop the old shape", "")
        self.assertTrue(entry.breaking)
        self.assertEqual(entry.subject, "drop the old shape")

    def test_breaking_footer_counts(self):
        entry = make_entry("abc", "feat: change it", "BREAKING CHANGE: the old call is gone")
        self.assertTrue(entry.breaking)
        self.assertIn("old call", entry.breaking_text)

    def test_unconventional_message_is_kept(self):
        entry = make_entry("abc", "just a message", "")
        self.assertEqual(entry.kind, "other")
        self.assertEqual(entry.subject, "just a message")

    def test_revert_is_its_own_kind(self):
        entry = make_entry("abc", "revert: feat: thing", "")
        self.assertEqual(entry.kind, "revert")

    def test_grouping_order_puts_features_first(self):
        entries = [
            make_entry("a", "chore: tidy", ""),
            make_entry("b", "fix: repair", ""),
            make_entry("c", "feat: build", ""),
            make_entry("d", "docs: describe", ""),
        ]
        kinds = [kind for kind, _ in group(entries)]
        self.assertEqual(kinds, ["feat", "fix", "docs", "chore"])


class Repository(unittest.TestCase):
    def test_reads_commits_newest_first(self):
        repo = make_repo(["feat: one", "fix: two"])
        entries = read_commits(repo)
        # The type prefix is the section, not part of the subject.
        self.assertEqual([entry.subject for entry in entries], ["two", "one"])
        self.assertEqual([entry.kind for entry in entries], ["fix", "feat"])

    def test_reads_since_a_tag(self):
        repo = make_repo(["feat: one", "fix: two"], tags=["v1.0.0"], tag_after_first=True)
        entries = read_commits(repo, since="v1.0.0")
        self.assertEqual([entry.subject for entry in entries], ["two"])

    def test_latest_tag(self):
        repo = make_repo(["feat: one"], tags=["v0.1.0", "v0.2.0"])
        self.assertEqual(latest_tag(repo), "v0.2.0")

    def test_no_tag_returns_none(self):
        repo = make_repo(["feat: one"])
        self.assertIsNone(latest_tag(repo))

    def test_merges_are_skipped_by_default(self):
        repo = make_repo(["feat: one"])
        git(repo, "checkout", "-q", "-b", "side")
        commit(repo, "fix: side", filename="side.txt")
        git(repo, "checkout", "-q", "main")
        git(repo, "merge", "-q", "--no-ff", "-m", "Merge branch 'side'", "side")
        subjects = [entry.subject for entry in read_commits(repo)]
        self.assertNotIn("Merge branch 'side'", subjects)
        subjects = [entry.subject for entry in read_commits(repo, include_merges=True)]
        self.assertIn("Merge branch 'side'", subjects)

    def test_not_a_repository(self):
        self.assertFalse(is_repository(tempfile.mkdtemp()))


class Rendering(unittest.TestCase):
    def setUp(self):
        self.entries = [
            make_entry("aaa1111", "feat(parser): add a thing", ""),
            make_entry("bbb2222", "fix: repair the thing", ""),
            make_entry("ccc3333", "docs: describe the thing", ""),
        ]

    def test_markdown_groups_sections(self):
        text = render_markdown(self.entries)
        self.assertIn("## Features", text)
        self.assertIn("## Bug Fixes", text)
        self.assertIn("**parser:** add a thing", text)
        self.assertLess(text.index("## Features"), text.index("## Bug Fixes"))

    def test_markdown_can_hide_scopes(self):
        text = render_markdown(self.entries, show_scopes=False)
        self.assertNotIn("**parser:**", text)

    def test_markdown_can_show_hashes(self):
        text = render_markdown(self.entries, show_hashes=True)
        self.assertIn("(aaa1111)", text)

    def test_breaking_only(self):
        entries = self.entries + [make_entry("ddd", "feat(api)!: drop it", "")]
        text = render_markdown(entries, breaking_only=True)
        self.assertIn("## Breaking Changes", text)
        self.assertIn("drop it", text)
        self.assertNotIn("repair the thing", text)

    def test_json_shape(self):
        document = json.loads(render_json(self.entries, version="v1.2.0"))
        self.assertEqual(document["version"], "v1.2.0")
        self.assertEqual(len(document["commits"]), 3)
        self.assertEqual(document["counts"]["feat"], 1)


class CommandLine(unittest.TestCase):
    def test_prints_markdown(self):
        repo = make_repo(["feat: one", "fix: two"])
        out = run([repo])
        self.assertEqual(out, 0)

    def test_check_reports_unconventional_commits(self):
        repo = make_repo(["feat: fine", "not conventional at all"])
        self.assertEqual(run(["--check", repo]), 1)
        self.assertEqual(run(["--check", make_repo(["feat: fine"])]), 0)

    def test_list_tags(self):
        repo = make_repo(["feat: one"], tags=["v0.1.0", "v0.2.0"])
        self.assertEqual(run(["--list-tags", repo]), 0)

    def test_rejects_a_path_outside_a_repository(self):
        self.assertEqual(run([tempfile.mkdtemp()]), 2)

    def test_main_is_importable(self):
        self.assertTrue(callable(main))


if __name__ == "__main__":
    unittest.main()
