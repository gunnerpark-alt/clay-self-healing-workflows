There's no example credential file here on purpose.

Running `clay login` writes a credential file to `~/.config/clay/config.json`. Its exact contents aren't something to hand-author or guess at from a template. It's written by the CLI itself, and Clay rotates its OAuth refresh token on every use, so a copy you made five minutes ago may already be stale.

The only thing worth remembering about it:

- Never commit it. The `.gitignore` in `templates/` already blocks `clay-config.json` and anything matching `clay-config*.json`.
- Give every consumer (your own CLI, the CI Action, any agent you add later) its own separate login. A shared or copied credential strands whichever consumer refreshes it second.
- For the GitHub Action, base64 it into a repo secret, not a file in the repo. See `templates/README.md`'s "Credentials" section for the exact command and the tradeoffs.
