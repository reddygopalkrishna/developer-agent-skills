# Git recovery recipes

Before any recipe that discards or rewrites something, create a backup ref (`git branch backup/<name>`) and get the user's confirmation. Almost anything that was ever committed can be recovered from the reflog for a while; uncommitted changes discarded with `reset --hard`, `restore` or `clean` usually cannot.

## Reset modes

| Command | Moves branch | Index (staged) | Working tree | Use for |
|---|---|---|---|---|
| `git reset --soft <commit>` | Yes | Kept | Kept | Redo commits: changes stay staged |
| `git reset <commit>` (`--mixed`, default) | Yes | Reset | Kept | Redo commits: changes become unstaged |
| `git reset --keep <commit>` | Yes | Reset | Updated, but aborts if local changes would be lost | Safe alternative to `--hard` |
| `git reset --hard <commit>` | Yes | Reset | Reset (uncommitted changes destroyed) | Only after confirmation and backup |

## Undo the last commit (not pushed)

```bash
git reset --soft HEAD~1      # keep changes staged
git reset HEAD~1             # keep changes unstaged
```

## Fix the last commit (not pushed)

```bash
git commit --amend -m "Better message"
git add forgotten_file && git commit --amend --no-edit
```

Amending a pushed commit rewrites history: prefer a new commit.

## Undo a pushed commit

```bash
git revert <sha>             # new commit that reverses <sha>
git revert -m 1 <merge-sha>  # revert a merge commit, keeping the first parent's side
```

After reverting a merge, merging the same branch again will not bring its changes back, because Git considers them already merged. Revert the revert first (`git revert <revert-sha>`), then merge.

## Recover lost commits (after reset, rebase or amend)

```bash
git reflog                    # find the SHA from before the mistake
git branch rescue <sha>       # safest: put a branch on it
# or move the current branch back (after confirmation):
git reset --keep <sha>
```

Right after a rebase, merge or reset, `ORIG_HEAD` points at where the branch was: `git branch rescue ORIG_HEAD`.

Reflog entries expire. By default, entries reachable from a branch are kept 90 days and unreachable ones 30 days (`gc.reflogExpire`, `gc.reflogExpireUnreachable`).

## Recover a deleted branch

The deletion message shows the SHA (`Deleted branch feature-x (was 1a2b3c4).`). Otherwise search the reflog:

```bash
git reflog | grep feature-x
git branch feature-x <sha>
```

## Recover a dropped stash

```bash
git fsck --no-reflogs --unreachable | grep commit
git show <sha>                # inspect candidates; stash commits have "WIP on" or "On <branch>" messages
git stash apply <sha>
```

## Commits landed on the wrong branch (not pushed)

Move the last N commits from `main` to a new branch:

```bash
git branch feature-x          # new branch at current commit keeps the work
git reset --keep HEAD~N       # move main back (after confirmation)
git switch feature-x
```

Move them to an existing branch instead:

```bash
git switch target-branch
git cherry-pick <sha1> <sha2>
git switch main
git reset --keep HEAD~N       # after confirmation
```

## Abort an operation in progress

```bash
git merge --abort
git rebase --abort
git cherry-pick --abort
git revert --abort
git am --abort
```

## Discard or unstage changes

```bash
git restore --staged <path>   # unstage, keep the changes
git restore --staged .        # unstage everything
git restore <path>            # discard working-tree changes (destructive: confirm)
git restore --source=<sha> -- <path>   # bring a file back from another commit
```

## Detached HEAD with new commits

```bash
git switch -c save-work       # keep the commits on a new branch
```

## Remove a file from the repository but keep it locally

```bash
git rm --cached .env
echo ".env" >> .gitignore
git commit -m "Stop tracking .env"
```

The file is still in history. If it contained secrets, rotate them and see the history-rewrite recipe below.

## Split the last commit

```bash
git reset HEAD~1
git add <first set of files> && git commit -m "First change"
git add <second set of files> && git commit -m "Second change"
```

## Make a local branch match the remote exactly

Discards local commits and changes on that branch. Confirm and back up first.

```bash
git branch backup/before-sync
git fetch origin
git reset --hard origin/<branch>
```

## Fix line endings after adding .gitattributes

```bash
git add --renormalize .
git commit -m "Normalize line endings"
```

## Rewrite history to remove a secret or a large file

Rotate any leaked secret **before** doing this. History rewriting changes commit IDs, needs a force-push, and every collaborator must re-clone or hard-reset. Agree on it with the user and the team first.

1. Install git-filter-repo (for example `pip install git-filter-repo`, or your OS package manager). It is the recommended replacement for `git filter-branch`.
2. Work on a fresh clone. filter-repo refuses to run on a clone that does not look fresh unless forced; that check protects you.

   ```bash
   git clone <url> repo-clean
   cd repo-clean
   ```

3. Remove a file from every commit:

   ```bash
   git filter-repo --invert-paths --path config/secrets.yml
   ```

   Or replace a secret string everywhere. Create `replacements.txt` containing a line such as `the-leaked-value==>REDACTED`, then:

   ```bash
   git filter-repo --replace-text replacements.txt
   ```

   Or strip large blobs:

   ```bash
   git filter-repo --strip-blobs-bigger-than 50M
   ```

4. filter-repo removes the `origin` remote to prevent accidental pushes. After checking the result (`git log`, search for the secret), re-add it and force-push all branches and tags, after confirmation:

   ```bash
   git remote add origin <url>
   git push --force --all
   git push --force --tags
   ```

5. Tell collaborators to re-clone (or fetch and reset every branch). Old clones still contain the secret and can push it back.
6. Hosting platforms may keep old commits reachable through pull request refs or caches. Follow the platform's documentation for removing sensitive data, which may involve contacting support.

An alternative tool for the same job is BFG Repo-Cleaner.
