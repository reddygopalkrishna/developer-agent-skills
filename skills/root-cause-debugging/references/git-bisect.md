# Git bisect guide

`git bisect` binary-searches commit history for the first commit where something changed. With N commits between good and bad, it needs about log2(N) tests: ~10 steps for 1,000 commits.

## Before you start

- Make sure the working tree is clean (`git status`). Stash or commit local changes.
- Confirm a **bad** commit (usually `HEAD`) actually fails with your reproduction.
- Find a **good** commit that actually passes: a release tag, a commit from last week, `git log --since="2 weeks ago" --oneline`. Test it; do not assume.
- Copy the reproduction (test script, test file) **outside the repository** or keep it untracked, so checking out old commits does not remove or change it.

## Manual bisect

```bash
git bisect start
git bisect bad                 # current commit is broken
git bisect good v1.4.0         # last known good tag or SHA
# Git checks out a commit halfway between. Build, test, then mark it:
git bisect good                # or: git bisect bad
# If this commit cannot be tested (does not build, unrelated breakage):
git bisect skip
# Repeat until Git prints "<sha> is the first bad commit".
git bisect reset               # return to where you started
```

Shortcut: `git bisect start <bad> <good>`, for example `git bisect start HEAD v1.4.0`.

## Automated bisect with `git bisect run`

```bash
git bisect start HEAD v1.4.0
git bisect run ./repro.sh
git bisect reset
```

Exit codes for the script:

| Exit code | Meaning |
|---|---|
| `0` | Commit is good |
| `1`-`127` except `125` | Commit is bad |
| `125` | Commit cannot be tested; skip it |
| anything else | Abort the bisect |

Example `repro.sh` (keep it outside the repo, e.g. in a temp directory, and pass its absolute path):

```sh
#!/bin/sh
# Dependencies can differ between commits: reinstall each step.
npm ci >/dev/null 2>&1 || exit 125      # cannot build -> skip
npx vitest run src/cart.test.ts -t "applies discount"
```

Python example:

```sh
#!/bin/sh
pip install -q -e . || exit 125
python -m pytest -q tests/test_orders.py::test_refund
```

Go example (a single test command works directly):

```bash
git bisect run go test -run '^TestRefund$' ./orders
```

If the test is new (it does not exist in old commits), put the test file outside the repo and copy it in inside the script, or turn it into a standalone script that only calls public code.

## Flaky reproductions

A flaky test makes bisect lie. Run the reproduction several times in the script and treat any failure as bad:

```sh
#!/bin/sh
for i in 1 2 3 4 5; do
  ./run-test.sh || exit 1
done
exit 0
```

## Bisecting something that is not a bug

For "when did this get slow" or "when did this output change", use custom terms so the prompts make sense:

```bash
git bisect start --term-old=fast --term-new=slow
git bisect slow HEAD
git bisect fast v2.0.0
# then: git bisect fast / git bisect slow, or git bisect run with a script
# that exits 0 when fast and 1 when slow
```

## Merge-heavy histories

`git bisect start --first-parent` only follows the first parent of merge commits, so it finds the merge (for example, the pull request) that introduced the change instead of descending into the merged branch. Then bisect inside that branch if needed.

## Useful commands

| Command | Purpose |
|---|---|
| `git bisect log` | Show the decisions so far (save it to share or replay) |
| `git bisect replay <file>` | Replay a saved log, e.g. after a wrong good/bad mark |
| `git bisect visualize` / `git bisect view` | Show the remaining suspect commits |
| `git bisect skip <sha>..<sha>` | Skip a range known to be untestable |
| `git bisect reset <commit>` | End bisect and check out a specific commit instead of the original |

## After you find the commit

1. Read the commit fully: `git show <sha>`.
2. Confirm: the parent passes and the commit fails (`git checkout <sha>~1`, test; `git checkout <sha>`, test).
3. The first bad commit tells you *where* the behavior changed, not *why*. Continue the root-cause workflow to explain the mechanism before fixing.
4. Run `git bisect reset` to return to your branch.

## Common pitfalls

- Marking a commit good or bad by eye instead of by running the reproduction. One wrong mark sends the whole search the wrong way; use `git bisect log` + `replay` to fix it.
- Stale build output or dependencies from a different commit. Clean and reinstall inside the script.
- The "good" commit was never actually good.
- The bug depends on data or environment that changed, not code. Bisect will then point at a random commit or never converge; go back to environment diffing.
