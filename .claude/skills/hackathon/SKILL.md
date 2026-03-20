---
name: hackathon
description: "This skill should be used when the user asks to \"chat with the team\", \"send a message to teammates\", \"check chatroom\", \"check team status\", \"sync with team\", \"notify teammates\", \"recruit teammates\", \"summon the team\", \"set up the team\", or mentions multi-agent coordination, team communication, or tmux pane messaging. Also triggers on /hackathon commands. Use this skill proactively whenever team coordination is needed during hackathon work."
---

# Multi-Agent Team Communication

Coordinate a team of AI coding agents running in parallel tmux panes with a shared chatroom and direct messaging.

## Configuration

All agent names, pane numbers, and tmux targets are defined in `team.conf` at the project root. Read it before any operation that references panes or agent names.

## Commands

Based on the argument provided by the user ($ARGUMENTS), execute one of the following:

### `recruit` — Summon the team

Detect the current tmux target, create missing panes, start all agents with the correct "no sandbox" options, and update `team.conf`.
```
./recruit
```
Run this to quickly set up or recover the multi-agent environment in your current window.

### `chat <message>` — Broadcast to team (Synced)

Post to chatroom AND send directly to every teammate so they process it.
```
./chat --sync <YourName> "<message>"
```
The `--sync` flag ensures the message is typed into every teammate's CLI input, following our Critical Rule.

### `send <pane|--all> <message>` — Direct message

Type a message directly into one or more teammate's CLI input:
```
./send --from <YourName> <pane|--all> "<message>"
```
Use `--all` to message everyone. The `--from` flag prefixes the message with the sender's name and logs it to the chatroom.

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
3. Post a status update via `chat --sync`

### `help` (or no argument) — Show available commands

Display the command list above.

## Communication Etiquette

### Always reply to the chatroom
When the User asks you a question or gives you a task (especially from the web chat), **always post your response to the chatroom** using `./chat`. The chatroom is the shared visible channel — the web chat reads from it. Pane-to-pane DMs (`./send`) are optional and supplementary; they must not replace chatroom replies.

**Rule: If the User can't see your answer in the web chat, you didn't answer.**

### Response rules
1. **Only Respond When Necessary**:
   - Respond if you are **directly addressed** (e.g., `@Gemini`).
   - Respond if the message is addressed to the **entire team**, **everyone**, or the **user**.
   - Respond if **no specific addressee** is mentioned and you have relevant input.
2. **Read-Only Mode**:
   - If a message is addressed to another specific teammate, read it to stay in sync, but **do not respond** and **do not relay/repeat** the message to them.
3. **Be Concise**:
   - Aim for high signal-to-noise ratio in all team communications.

### DMs are optional, chatroom is mandatory
- `./chat` to post to chatroom = **mandatory** for any reply the User should see
- `./send` to DM a teammate = **optional** for urgent pane delivery
- Never reply only via DM if the User asked the question

## Critical Rule: Notification Protocol

Posting to chatroom via `./chat` (without `--sync`) is **not** real notification. The `chat` script writes to a file and flashes an ephemeral tmux message that disappears in seconds.

**Real notification = typing into their pane.**

Always use `./chat --sync` for general announcements or `./send` for direct messages. This ensures the team actually processes your input.

## Scripts

| Script | Purpose |
|--------|---------|
| `recruit` | Detect tmux target, create panes, start agents, update `team.conf`. |
| `chat` | Append to chatroom + notify. Use `--sync` for full team delivery. |
| `send` | Paste message into teammate CLI inputs. Supports `--all`. |
| `notify` | Ephemeral tmux display-message on a single pane. |
| `archive` | Move old chatroom messages to `chatroom_archive.md`. |
| `chat-daemon` | Background daemon that auto-archives periodically. |

*Note: The `send` script includes special logic for Gemini panes to handle shell-mode Escaping.*

## Additional Resources

### Reference Files
- **`references/safety.md`** — Concurrency safety details, flock usage, and tmux buffer handling.
