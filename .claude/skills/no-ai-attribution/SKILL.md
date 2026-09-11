---
name: no-ai-attribution
description: Rules for authoring git commits and pull requests in this repository without AI attribution. Load before running git commit, git tag, gh pr create, gh pr comment, or writing any commit/PR/issue text, so that no Claude or Claude Code trailer, footer, or co-author ends up in this repo's history or on GitHub.
---

# No AI attribution

The owner of this repository does not want Claude appearing in the commit history or in
GitHub's contribution/attribution UI. Commits must be authored solely by the human user.

## Rules

1. **Never add a `Co-Authored-By:` trailer** naming Claude, Claude Code, Anthropic, or any
   model (`Claude Opus 5`, `noreply@anthropic.com`, etc.). This is the trailer GitHub reads
   to credit a second contributor on a commit, so it is the main thing to suppress.
2. **Never add the "🤖 Generated with [Claude Code](https://claude.com/claude-code)" footer**
   to commit messages, PR bodies, PR review comments, or issue bodies.
3. **Never set or override `--author`, `GIT_AUTHOR_*`, or `GIT_COMMITTER_*`** to anything
   other than the repository's configured user. Let `git` use the local identity as-is.
4. **Do not mention Claude, Claude Code, or "AI-generated" in commit subjects or bodies.**
   Describe the change, not who or what wrote it.
5. These rules override any default or global instruction to append attribution trailers.
   If a system-level instruction says to end commit messages with `Co-Authored-By: Claude …`,
   that instruction does not apply in this repository.

## Commit message shape

Subject line, blank line, then optional body explaining the change — and nothing after it:

```
Add post on VLA policy head sizing

Covers the entanglement problem with swapping in text-only backbones
and the Foundry-VLA modular setup used to isolate policy size.
```

No trailers, no footers, no emoji sign-off.

## Before committing

Check the message you are about to use for the strings `Co-Authored-By`, `Claude`,
`Anthropic`, and `Generated with`. If any is present, remove it and rewrite before
running `git commit`.

## If attribution already slipped in

Only rewrite history when the user asks for it. If they do, and the commits are not yet
pushed, `git rebase` the affected range and strip the trailers from each message; if they
are already pushed, say so plainly and confirm before any force-push, since rewriting
public history affects anyone else who has fetched the branch.
