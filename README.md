# commitnotes 📝

[![CI](https://img.shields.io/github/actions/workflow/status/doge-th/commitnotes/ci.yml?branch=main&label=CI)](https://github.com/doge-th/commitnotes/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)

**Release notes from conventional commits, with no dependencies.**

Your commits already say what changed. commitnotes turns them into release
notes — grouped, scoped, and ready to paste into a GitHub release. No Node, no
config file, one command.

```
$ commitnotes .

## Features

- add plugin name to hook errors (#24107) (40475e5)
- **create-vite:** use Solid 2 in solid templates (#24130) (3dfda24)

## Bug Fixes

- preserve drive letter case in `safeRealpathSync` on Windows (#24146) (3567471)
- close server on failed start (fix #23965) (#24020) (c732677)
- **server:** keep `this.addWatchFile` in `load` hook on a module's first request (#23861) (b516bc2)
- **optimizer:** respect top-level tsconfig option when scanning and bundling deps (#24119) (760a953)

## Performance

- **build:** skip build import analysis hooks for unaffected chunks (#24150) (1a06564)
- **build:** skip terser plugin when terser is not used (#24149) (3bde8ed)

## Refactoring

- **build:** skip license plugin via applyToEnvironment when disabled (#24134) (3c22583)
- simplify some conditions (#24125) (a379269)
```

*(that's commitnotes reading a real repository's history — the output is
unedited)*

## Why

Release notes get skipped, then someone reconstructs them from a merge
screen the night before a release. Meanwhile the information is already in
the history — the commit subject says what changed, the type says which
section it belongs in, and the scope says which part of the product.

commitnotes reads that and stops there:

- **Conventional commits in, release notes out.** `feat:`, `fix:`, `perf:`,
  `docs:`, `chore:` and the rest become sections, in the order a reader
  wants them.
- **Scopes are kept.** `fix(server): ...` reads as *server: fix ...*.
- **Breaking changes are found two ways**: the `!` marker
  (`feat(api)!: ...`) and a `BREAKING CHANGE:` footer.
- **Nothing is hidden.** A commit whose message does not follow the
  convention is still a commit — it lands under *Other Changes* instead of
  being dropped.

## Install

```bash
pip install commitnotes
```

Python 3.9–3.13. No dependencies: `git` and the standard library.

## Use

```bash
commitnotes                       # since the latest tag
commitnotes --since v1.2.0        # since a tag or commit
commitnotes --until v1.3.0        # up to a tag
commitnotes --tag v1.3.0          # the notes for one version
commitnotes --all                 # every commit
commitnotes --breaking-only       # only the breaking changes
commitnotes --json                # machine-readable
commitnotes --no-scope            # leave scopes out
commitnotes --no-hashes           # leave commit hashes out
commitnotes --include-merges      # include merge commits
commitnotes --list-tags           # the repository's tags, newest first
```

### In CI

Keep the messages honest:

```yaml
- run: commitnotes --check .
```

It exits 1 and names every commit whose message does not follow the
convention, so a branch that drifts gets caught before the release, not
after.

## What it reads

A commit subject like

```
feat(server): keep the watcher alive across a reload
```

becomes a *Features* entry. The type may carry a scope in parentheses and
a `!` before the colon. A body containing `BREAKING CHANGE: ...` marks the
commit as breaking even without the `!`.

Merge commits are skipped by default (`--include-merges` keeps them),
because a merge subject repeats work another commit already describes.

## Honest limits

- Only the subject line is classified; the body is kept for breaking-change
  footers, not summarised.
- Version numbers come from tags, not from a manifest — a repository that
  tags `v1.2.3` gets `v1.2.3` in the heading.
- The newest tag wins when several share a commit; `git describe` would pick
  the alphabetically smaller one.
- Squash-merged pull requests read as one commit, which is what a release
  note should say.

## Related tools

Also from the same author, all zero-dependency Python CLIs:

- [toktree](https://github.com/doge-th/toktree) — `du` for your LLM context window
- [githotspot](https://github.com/doge-th/githotspot) — churn × complexity hotspots in any git repo
- [todomold](https://github.com/doge-th/todomold) — which TODOs have rotted, ranked by blame age
- [awakehours](https://github.com/doge-th/awakehours) — timezone meeting grid for distributed teams
- [csvpulse](https://github.com/doge-th/csvpulse) — the health of a CSV file in one command
- [pyverscan](https://github.com/doge-th/pyverscan) — the oldest Python your code can run on

## License

[MIT](LICENSE)
