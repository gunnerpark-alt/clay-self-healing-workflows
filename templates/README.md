# Self-healing Clay workflows

Workflow and Audience config lives here as files. Changes get reviewed as pull requests. Merging applies them back to Clay.

## Layout

```
workflows/<slug>/workflow.json          graph: trigger, nodes, edges
workflows/<slug>/nodes/<node>.prompt.md agent prompts, one file each
workflows/<slug>/nodes/<node>.py        code node bodies, one file each
audiences/fields/<entity-type>.json     field definitions (people, companies)
audiences/segments/<slug>.json          one saved audience per file
tools/pull_workflows.py                 Clay -> repo
tools/apply_workflows.py                repo -> Clay
tools/pull_audiences.py                 Clay -> repo
tools/apply_audiences.py                repo -> Clay
.github/workflows/apply-on-merge.yml    runs apply_*.py --write on merge to main
```

Records and activities aren't here on purpose. Those are data, not config. That's the same reason workflow *runs* aren't versioned, only the workflow *definition* is. Don't add customer or lead data to this repo.

Functions aren't here either. There's no CRUD for them through the CLI as of this writing. You can read them through the Table Read API, but not edit them this way.

## Setup

1. `clay login` — your own login, your own workspace. Don't reuse anyone else's credential; see "Credentials" below for why.
2. Find the workflows you want to track: `clay workflows list`.
3. `python3 tools/pull_workflows.py <workflowId> [<workflowId> ...]`
4. If you also want Audience config tracked: `python3 tools/pull_audiences.py`
5. Run the same pull command a second time. The diff should be empty. If it isn't, something in your workspace's graph isn't canonicalizing the way these scripts expect. That's worth digging into before you trust the diffs `apply_*.py` produces later.
6. Commit, push, open the repo on GitHub.

## Making a change

Edit a prompt file, a node's fields in `workflow.json`, or a field/segment file directly. Then:

```
python3 tools/apply_workflows.py           # dry run — prints the plan
python3 tools/apply_workflows.py --write --publish   # actually applies it

python3 tools/apply_audiences.py
python3 tools/apply_audiences.py --write
```

Both scripts are dry-run by default. Nothing changes in Clay until you pass `--write`.

In practice you'd make the edit on a branch, open a PR so someone reviews the diff, and let the merge trigger the Action instead of running `--write` locally.

## Credentials

Clay rotates the OAuth refresh token every time it's used. That means a static, shared credential breaks the *other* thing using it as soon as either one refreshes. Give every consumer its own separate login: your own CLI login, the CI Action, any agent you add later. Don't copy one credential around to save a step; it'll strand something within a day.

For the GitHub Action, the default here is a plain Actions secret:

```
clay login                                   # a dedicated login just for CI
base64 -i ~/.config/clay/config.json | gh secret set CLAY_OAUTH_CONFIG
```

This secret will eventually go stale, again because of the refresh-token rotation. Expect to redo this occasionally; that's a reasonable tradeoff for most teams.

If you want the Action to stay working indefinitely without you touching it, there's a self-sustaining variant: the Action commits its own rotated credential back to the repo at the end of every run, instead of reading a static secret. That removes the maintenance step, but it also means the credential sits in plaintext in a file anyone with read access to this repo can see. Only do this on a private repo with tightly controlled access, never on anything public or widely shared.

## Going further

Two things extend this pattern beyond "you make the change." Neither is set up by this repo. Both need account-level configuration outside it.

**A scheduled Claude agent** that reads run history (and, for Audiences, activity) on its own cadence, and opens a PR itself when it finds something worth fixing or improving. This is a Claude Managed Agent deployment, configured through Anthropic's Managed Agents API. The agent gets this repo and a Clay credential mounted into it, and it's read-only against Clay: the only thing it can produce is a PR.

**Claude Tag**, so a rep can tag Claude in a Slack thread and get a live diagnosis against this same repo, with the fix applied directly through the CLI once someone approves in the thread. There's no PR here; the point is speed for a single-account fix. This needs a Slack admin to grant the Claude Tag channel access to this repo (claude.ai/admin-settings/claude-tag).

Both end up touching the exact same `workflows/` and `audiences/` files this repo already tracks. The scheduled agent proposes through a PR; Claude Tag writes directly and this repo catches up afterward with a plain sync commit. Either way, nothing changes without a person saying yes first.
