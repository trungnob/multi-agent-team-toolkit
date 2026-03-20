# Team Tools & Productivity Guide

## Configuration

All scripts read from `team.conf` in the project root. Edit it to match your tmux layout and agent names.

## Shared Communication

### Chatroom (persistent messages)
- **File**: `chatroom.md` in the project root
- Read it anytime to catch up on team discussion
- Append your messages to the end

### Chat Script (post + notify)
```bash
./chat <YourName> "<message>"
```
Posts to chatroom.md AND sends a tmux display-message to all agent panes.

```bash
./chat --sync <YourName> "<message>"
```
Appends to chatroom.md, flashes tmux notifications, and types the message into all teammate panes except the current one.

### Notify Script (quick ping)
```bash
./notify <pane> "<message>"
```

### Send Script (direct message to a teammate's input)
```bash
./send <pane> "<message>"
```
```bash
./send --all "<message>"
```
Uses tmux paste-buffer for most panes and a Gemini-specific literal typing path to avoid shell-mode paste bugs. When `--from` is supplied, the send is also logged to the shared chatroom once.

**IMPORTANT**: Do NOT use `tmux send-keys` with raw text — special characters
get escaped. Always use the `send` script instead.

### Recruit Script (recover or build the 3-agent pane layout)
```bash
./recruit --as Claude
./recruit --as Gemini --force
```
Detects the current tmux session/window, ensures a 3-pane layout, maps panes to agents, starts missing CLIs with low-friction flags, and rewrites `team.conf`.

### Read another agent's pane (see what they're doing)
```bash
tmux capture-pane -t "<target>.<pane>" -p | tail -20
```
(The tmux target is in `team.conf`)

## Chatroom Archiver
- `chatroom.md` only keeps the **last N minutes** of messages (configurable in `team.conf`)
- Older messages auto-move to `chatroom_archive.md`
- Background daemon runs periodically: `./chat-daemon start|stop|status`
- Manual archive: `./archive` (or `./archive --dry-run` to preview)
- All use the same `flock` as `chat` — no race conditions
- Full conversation history is always in `chatroom_archive.md`

## Concurrency Safety
All shared scripts use `flock` on lockfiles in `/tmp/` (derived from a hash of the project directory path).
No agent needs to worry about race conditions.

## Memory Systems (per agent)

Each agent has its own memory/persistence system. Setting these up helps maintain context across conversations.

### Claude
- Per-project instructions: `CLAUDE.md` in project root
- Memory: `~/.claude/projects/<project>/memory/`

### Gemini
- Project instructions: `GEMINI.md` in project root or `~/.gemini/GEMINI.md` globally

### Codex
- Rules: `~/.codex/rules/default.rules`
- Memories: `~/.codex/memories/`
- Per-project instructions: `AGENTS.md` or `codex.md` in project root

## Communication Protocol

### Identity
- **Always use your own agent name.** Never impersonate another agent or the User.
- **The web chat UI is for the human User only.** Agents must use `./chat` and `./send` from their panes, never the web interface.
- If debugging the web chat, prefix messages with `[DEBUG <YourName>]`.

### Response Etiquette
- **Only respond when addressed.** If a message says `@Gemini`, only Gemini responds. Others read silently.
- **Respond to broadcasts.** Messages addressed to everyone or no one specific are fair game.
- **Don't relay addressed messages.** If User says `@Codex do X`, don't repeat it to Codex via `./send` — they can read the chatroom. Only `./send` for things the recipient wouldn't otherwise see.
- **Be concise.** High signal-to-noise ratio in all team communication.

### Consensus
- **Wait for all teammates** before pushing code or finalizing decisions.
- Slower reviewers often catch the most important bugs — don't rush past them.

## Recommended Setup

1. **Edit `team.conf`** to match your tmux session/window and pane layout
2. **Create project-level instruction files** so your agent remembers team context
3. **Use the chat script** rather than raw file edits — it handles notifications
4. **Check chatroom.md regularly** before starting new work
5. **Start the archive daemon** with `./chat-daemon start` to keep chatroom tidy
