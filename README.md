# Clay self-healing workflows — starter kit

A starter kit for mirroring Clay Workflows and Audiences config into a git repo, reviewing changes as pull requests, and applying them back to Clay on merge. This is generalized and stripped of anything workspace-specific: no credentials, no real workspace IDs, nothing here can touch anyone's Clay workspace on its own.

## What's in this repo

- **`SKILL.md`** — a Claude Skill. Drop it into `.claude/skills/clay-self-healing-workflows/` in your own project and Claude will walk you through scaffolding a repo like this one against your own workspace. You can also just read it top to bottom and follow the steps by hand; nothing here requires Claude Code specifically.
- **`templates/`** — what actually gets copied into your working repo: the pull/apply scripts, the GitHub Action, a `.gitignore`, and a `README.md` written for the repo you're about to build (not this one).
- **`examples/`** — fake-but-realistic output, so you can see the actual shape of a pulled workflow, a field definition, and a saved segment before you've run anything against a real workspace. Nothing in here is real data; don't copy it into your working repo, just read it.

## Getting started

1. Read `SKILL.md`, or hand this whole repo to Claude Code and ask it to follow the skill.
2. `clay login` with your own credential. See `templates/README.md`'s "Credentials" section before you touch CI. Clay rotates the OAuth refresh token on every use, and that has real consequences for how you set up the GitHub Action.
3. Copy `templates/` into your own repo and pull your first workflow.

## What this does and doesn't cover

Workflow config (graph + prompts) and Audiences config (field definitions + saved segments) are both full CRUD through the `clay` CLI, so both get the same pull-review-apply treatment. Audience *records* and *activities* are data, not config, and deliberately stay out of git. That's the same reason workflow *runs* aren't versioned, only the workflow *definition* is. Functions aren't covered; there's no CRUD for them through the CLI as of this writing.
