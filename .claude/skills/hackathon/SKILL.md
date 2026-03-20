---
name: hackathon
description: "This skill should be used when the user asks to \"chat with the team\", \"send a message to teammates\", \"check chatroom\", \"check team status\", \"sync with team\", \"notify teammates\", or mentions multi-agent coordination, team communication, or tmux pane messaging. Also triggers on /hackathon commands. Use this skill proactively whenever team coordination is needed during hackathon work."
---

# Multi-Agent Team Communication

Coordinate a team of AI coding agents running in parallel tmux panes with a shared chatroom and direct messaging.

## Configuration

All agent names, pane numbers, and tmux targets are defined in `team.conf` at the project root. Read it before any operation that references panes or agent names.

`team.conf` is the source of truth. Never hardcode a tmux session like `1:0`, and never assume another project's repo path. Resolve commands relative to the current project root.

## Commands

Based on the argument provided by the user ($ARGUMENTS), execute one of the following:

### `chat <message>` — Broadcast to team

Post to chatroom AND send directly to every teammate so they process it.

1. Read `team.conf` to get pane numbers
2. Run `./chat <YourName> "<message>"`
3. Run `./send --from <YourName> <pane> "<message>"` for each teammate pane

### `send <pane> <message>` — Direct message

Type a message directly into one teammate's CLI input:
```
./send --from <YourName> <pane> "<message>"
```
The `--from` flag prefixes the message with the sender's name so the receiver knows who sent it.

For a broadcast to all teammate panes in the current tmux target:
```
./send --from <YourName> --all "<message>"
```

### `notify <pane> <message>` — Ephemeral ping

Flash a tmux notification on a teammate's pane:
```
./notify <pane> "<message>"
```

### `read` — Read chatroom

Read and summarize the latest messages from `chatroom.md`.

### `status` — Check all teammates

Read `team.conf` for pane numbers, then capture each pane:
```
tmux capture-pane -t "<target>.<pane>" -p | tail -20
```

### `sync` — Full team sync

1. Read chatroom
2. Capture all teammate panes
3. Post a status update via `chat`

### `recruit` — Rebuild the team layout

Ensure the current tmux window has the standard 3-agent layout and launch any
missing teammates:
```
./recruit --as Claude
./recruit --as Gemini --force
```

### `help` (or no argument) — Show available commands

Display the command list above.

## Communication Protocol

### Identity Rules
- **Never impersonate another agent or the User.** Always use your own name.
- **The web chat (chatserver) is User-only.** Agents must not send messages through the web chat UI. Use `./chat` and `./send` from your pane.
- If you must debug the web chat, prefix your message with `[DEBUG <YourName>]`.

### Response Etiquette
- **Only respond when addressed.** If a message is directed at a specific teammate (`@Gemini`, `@Codex`), only that agent should respond. Others should read but stay silent.
- **Respond to broadcasts.** If a message addresses everyone or no one specific, any agent may respond.
- **Don't relay addressed messages.** If the User says `@Codex do X`, do NOT repeat/relay that message to Codex via `./send`. The chatroom is shared — they can read it themselves. Only use `./send` for messages the recipient wouldn't otherwise see.

### Consensus Before Action
- **Wait for all teammates** to review and approve before pushing code or finalizing decisions. Don't rush with partial consensus.
- Slower reviewers often provide the most valuable feedback — wait for them.

### Notification Protocol

Posting to chatroom via `./chat` is **not** real notification. The `chat` script writes to a file and flashes an ephemeral tmux message that disappears in seconds.

**Real notification = `./send` to their pane.** This types directly into the teammate's CLI input.

Whenever announcing something to the team, **always do both**:
1. `./chat` for persistent chatroom record
2. `./send` to each teammate pane for actual delivery

Never claim "notified the team" after only running `./chat`.

## Scripts

| Script | Purpose |
|--------|---------|
| `chat` | Append to chatroom + flash tmux notification to all panes |
| `send` | Paste message into a teammate's CLI input via tmux buffer |
| `notify` | Ephemeral tmux display-message on a single pane |
| `archive` | Move old chatroom messages to `chatroom_archive.md` |
| `chat-daemon` | Background daemon that auto-archives periodically |

## Additional Resources

### Reference Files
- **`references/safety.md`** — Concurrency safety details, flock usage, tmux buffer handling, and the Gemini escape-key workaround
