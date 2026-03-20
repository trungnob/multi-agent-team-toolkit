---
name: hackathon
description: "This skill should be used when the user asks to \"chat with the team\", \"send a message to teammates\", \"check chatroom\", \"check team status\", \"sync with team\", \"notify teammates\", or mentions multi-agent coordination, team communication, or tmux pane messaging. Also triggers on /hackathon commands. Use this skill proactively whenever team coordination is needed during hackathon work."
---

# Multi-Agent Team Communication

Coordinate a team of AI coding agents running in parallel tmux panes with a shared chatroom and direct messaging.

## Configuration

All agent names, pane numbers, and tmux targets are defined in `team.conf` at the project root. Read it before any operation that references panes or agent names.

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

### `help` (or no argument) — Show available commands

Display the command list above.

## Critical Rule: Notification Protocol

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
