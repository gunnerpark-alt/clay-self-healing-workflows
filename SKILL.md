---
name: clay-self-healing-workflows
description: Scaffold a repo that mirrors your Clay Workflows and Audiences config as git-diffable files, with a GitHub Action that applies merged changes back to Clay. Use when someone wants to set up self-healing or self-improving Clay workflows, version-control their workflow/audience config, or asks how to get their Workflows/Audiences into a GitHub repo.
---

# Clay self-healing workflows — starter kit

This scaffolds a repo where your Clay Workflows and Audiences config live as files, get reviewed as pull requests, and get applied back to Clay by a GitHub Action on merge.

It does not include any credentials, workspace IDs, or account setup for you. You provide your own Clay login; nothing here can touch anyone else's workspace.

## What this covers, and what it doesn't

**Covered, with real CLI backing:**
- **Workflows** — the graph (nodes, edges, triggers) as JSON, prompts as their own Markdown files, code nodes as their own `.py` files.
- **Audiences config** — field definitions (`clay audiences fields`) and saved segments (`clay audiences`: name, description, filter AST). Both are full CRUD via the CLI, same shape as workflow nodes.

**Deliberately not covered:**
- **Audience records and activities.** Those are data, not config. That's the same way workflow *runs* aren't versioned, only the workflow *definition* is. Don't put customer/lead data in git.
- **Functions.** As of this writing there's no CRUD for Functions via the CLI. You can read them through the Table Read API, but not edit them this way.

## Steps to run when this skill is invoked

1. **Confirm the working directory is (or will become) the repo to scaffold.** If it's not a git repo yet, run `git init`.

2. **Check the user's own Clay auth** — run `clay whoami`. If it fails, tell them to run `clay login` themselves and pick their own workspace. Never ask for or accept a pasted credential; this whole pattern depends on each consumer (the user, the CI Action, any agent) having its own login, because Clay rotates the OAuth refresh token on every use. A shared or copied credential strands whichever consumer didn't refresh it last. Say this plainly if they ask why.

3. **Read `examples/` first if it's your own first time through this**, then **copy the contents of `templates/` into the target repo:**
   - `templates/tools/*.py` → `tools/`
   - `templates/.github/workflows/apply-on-merge.yml` → `.github/workflows/`
   - `templates/.gitignore` → `.gitignore`
   - `templates/README.md` → `README.md` (this becomes their repo's own README; edit the workflow IDs section before committing)

4. **Ask which workflows to track** (name or ID; run `clay workflows list` if they don't know). Run:
   ```
   python3 tools/pull_workflows.py <workflowId> [<workflowId> ...]
   ```
   This writes `workflows/<slug>/workflow.json` and the node prompt/code files. Confirm a second `pull_workflows.py` run produces an empty `git diff`. That's the property the whole review model depends on. If it doesn't, something in that workspace's graph isn't canonicalizing cleanly; don't proceed until it's clean.

5. **Ask if they also want Audiences config tracked.** If yes:
   ```
   python3 tools/pull_audiences.py
   ```
   Writes `audiences/fields/<entity-type>.json` and `audiences/segments/<slug>.json`.

6. **Set up the write credential for CI**, per the README's "Credentials" section: a GitHub Actions secret by default, with the self-rotating in-repo pattern offered only as an advanced option and only for a private, access-controlled repo. Do this step yourself only if asked; otherwise just point to the README section, since it involves the user's own GitHub org settings.

7. **Walk through `tools/apply_workflows.py` and `tools/apply_audiences.py` in dry-run first** (no `--write`) against a change they make on purpose, so they see the diff/plan output before anything applies for real.

8. **Mention, but don't build, the two optional layers** described in the README's "Going further" section: a Claude Managed Agent for a proactive nightly review, and Claude Tag for a reactive Slack-triggered fix. Both need account-level setup (an Anthropic Managed Agent deployment; a Slack admin grant for Claude Tag) that lives outside this repo, so scaffolding stops at pointing to those docs rather than automating them.

Keep the tone practical. This is infrastructure, not magic. The value is that Workflow and Audience config becomes something a pull request can review, not that an agent is doing anything it couldn't already do through the CLI directly.
