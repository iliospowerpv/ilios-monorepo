---
name: Validation code-review uses task baseline, not your commit
description: Why mark_task_complete's code review can REJECT in-scope work by diffing a stale/old baseline across many prior commits.
---

# mark_task_complete code review diffs the task baseline, not just your commit

The `mark_task_complete` validation code review compares against the baseline of
the platform's *currently-associated task*, not against your single new commit.
When the platform's `current_task` is **stale** (e.g. still pointing at an older,
already-finished task such as a prior "Audit & design …" item), that baseline is
very old, so the reviewed diff spans **every commit since** — including unrelated
prior work — and the review is judged against the **wrong task description**.

**Symptom:** a frontend-only, in-scope task gets REJECTED for "scope violation"
citing files you never touched (e.g. backend services, audit docs, other modules),
and the verdict quotes a task objective that isn't the one you implemented.

**Why:** the verdict is a false negative from task↔diff mismatch, not a problem
with your code.

**How to apply:**
1. Confirm your real surface: `git log --oneline -1` (your commit is usually
   already HEAD — the platform auto-commits) and `git show --name-only <sha>`.
2. If your commit touches only the intended files and your own checks pass
   (tests, tsc/webpack "No issues found.", eslint), the rejection is spurious.
3. Re-call `mark_task_complete` with a precise `skip_validation_reason` that names
   your commit SHA, its exact file list, and the verification path that did pass.
   Do **not** start deleting/reverting the prior commits the reviewer complained
   about — they are someone else's already-merged work, not yours.
