# Team Tools & Productivity Guide

## Configuration

All scripts read from `team.conf` in the project root. Edit it to match your tmux layout and agent names.

## Shared Communication

### Chatroom (persistent messages)
- **File**: `chatroom.md` in the project root
- Read it anytime to catch up on team discussion
- Append your messages to the end
- Treat broadcast messages as shared context, not an automatic request for everyone to reply

### Chat Script (post + notify)
```bash
./chat <YourName> "<message>"
```
Posts to `chatroom.md` and flashes a tmux display-message to all agent panes. This creates a durable record, but it is not guaranteed prompt-level delivery.

```bash
./chat --sync <YourName> "<message>"
```
Appends to `chatroom.md`, flashes tmux notifications, and types the message into all teammate panes except the current one. Use this only when teammates truly need immediate awareness.

### Notify Script (quick ping)
```bash
./notify <pane> "<message>"
```

### send Script (direct message to a teammate's input)
```bash
./send <pane> "<message>"
```
```bash
./send --all "<message>"
```
Uses tmux paste-buffer for most panes and a Gemini-specific literal typing path to avoid shell-mode paste bugs. Improved to handle Gemini's 'Working' and 'Queued' states by force-clearing stale input with `C-u` before delivery.

### Image Generation Skill (Multimodal)
Located at: `scripts/generate_image.py`
Requires: `pip install google-genai`
API Keys: `GEMINI_API_KEY` or `GOOGLE_API_KEY`

Usage:
```bash
python3 scripts/generate_image.py "a professional healthcare infographic"
```
Generated images are saved to the `uploads/` folder. Coordinate with the team before generating to avoid quota usage and duplicates.

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

## Team Communication Protocol

- Treat the browser-based web chat as the human operator channel by default. Agents should use `./chat`, `./chat --sync`, `./send`, and `./notify` for routine coordination.
- Use `./chat` for the durable record and `./send` for time-sensitive direct prompts. Use `./chat --sync` or `./send --all` only when actual prompt-level delivery is required.
- Read broadcast messages for context, but only reply when the message addresses you, addresses everyone, or addresses no one.
- If the user addresses a specific teammate, do not relay or restate that message to the named teammate unless explicitly asked.
- If a browser-side debug post is ever unavoidable, prefix it clearly, for example `[DEBUG Codex]`, so it is not mistaken for a normal user message.

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
