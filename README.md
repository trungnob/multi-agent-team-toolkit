# Multi-Agent Team Toolkit

Orchestrate multiple AI coding agents — **Claude, Gemini, Codex**, or any CLI-based LLM — as a synchronized engineering team in tmux.

This toolkit transforms your terminal into a high-bandwidth mission control, breaking down the context silos of individual AI chat windows and enabling real-time, cross-model collaboration.

![Web Chat UI](screenshots/web-chat.png)

## Why Use This?

- **Cognitive Diversity** — Combine Claude's nuanced reasoning, Gemini's research capabilities, and Codex's implementation speed on the same problem.
- **Context Synchronization** — A shared, persistent chatroom ensures every agent is on the same page regarding goals, architecture, and blockers.
- **Direct Agent-to-Agent Messaging** — Scripts allow agents to message each other directly, enabling autonomous code review, brainstorming, and task handoffs.
- **Lightweight & Portable** — Zero heavy dependencies. Built on Bash, flock, and tmux — works anywhere your CLI does.

## Screenshots

### Three agents collaborating in tmux
![tmux session with 3 agents](screenshots/tmux-agents.png)

### Web chat UI with live updates
![Web Chat UI](screenshots/web-chat.png)

## What's Included

| File | Description |
|------|-------------|
| `team.conf` | Central configuration — tmux target, pane mapping, agent names |
| `chat` | Post a message to the shared chatroom + notify all panes |
| `send` | Type a message directly into a teammate's CLI input |
| `notify` | Send an ephemeral tmux notification to a pane |
| `archive` | Move old chatroom messages to `chatroom_archive.md` |
| `chat-daemon` | Background daemon that auto-archives every N minutes |
| `chatserver.py` | Web UI for the chatroom (live view, archive, send messages) |
| `.claude/skills/hackathon/` | Claude Code skill for team coordination |
| `TEAM_TOOLS.md` | Full reference doc for all tools |

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/trungnob/multi-agent-team-toolkit.git my-team
cd my-team
```

Edit `team.conf` to match your tmux layout:

```bash
TMUX_TARGET="myteam:0"   # your tmux session:window
PANE_CLAUDE=0
PANE_GEMINI=1
PANE_CODEX=2
```

### 2. Set up tmux

```bash
tmux new-session -d -s myteam
tmux split-window -h -t myteam
tmux split-window -v -t myteam
tmux attach -t myteam

# Pane 0: claude
# Pane 1: gemini
# Pane 2: codex
```

### 3. Make scripts executable and initialize

```bash
chmod +x chat send notify archive chat-daemon
touch chatroom.md
```

### 4. Start communicating

```bash
# Post to the team chatroom
./chat Claude "I've finished the auth module, ready for review"

# Send a direct message to Gemini (pane 1)
./send --from Claude 1 "Can you review the auth module?"

# Quick ping to Codex (pane 2)
./notify 2 "Check the chatroom!"

# Archive old messages
./archive --dry-run
```

### 5. Start the web UI (optional)

```bash
python3 chatserver.py
# Opens at http://localhost:9091
# Set CHATSERVER_PORT to use a different port
# Set CHATSERVER_BIND=0.0.0.0 to allow remote access (localhost only by default)
```

### 6. Start the archive daemon (optional)

```bash
./chat-daemon start   # auto-archives old messages every 5 min
./chat-daemon status  # check if running
./chat-daemon stop    # stop the daemon
```

### 7. Use the Claude Code skill (optional)

If you're using Claude Code, the `/hackathon` skill provides shortcuts:

```
/hackathon chat "message"       # post + notify all teammates
/hackathon send 1 "message"     # direct message to pane 1
/hackathon read                 # summarize recent chatroom
/hackathon status               # check what all agents are doing
/hackathon sync                 # read + check + post status update
```

## How It Works

The toolkit is built around a small set of shell scripts that coordinate through tmux, a shared Markdown chat log, and a single configuration file (`team.conf`). Every script resolves paths relative to its own location, so you can clone the repo anywhere without editing hardcoded paths.

### Concurrency Safety

The shared resources — chatroom file, tmux paste buffers, and archive daemon PID state — are protected by `flock` on lockfiles in `/tmp/`.

- `./chat` and `./archive` share the same chatroom lock, so appends and archive rewrites cannot interleave and corrupt `chatroom.md`.
- `./send` uses its own tmux send lock to serialize buffer creation, paste, and cleanup.
- `./chat-daemon` uses a dedicated PID lock so concurrent start/stop/status calls do not race.

Lock filenames are derived from a hash of the full project path, so multiple clones on the same machine won't collide.

### Reliable tmux Message Delivery

Direct messages use tmux `load-buffer` + `paste-buffer` instead of raw `send-keys`. This matters because `send-keys` can mis-handle quoting and special characters, especially with JSON, shell metacharacters, or punctuation.

The `./send` flow:

1. Acquire the tmux send lock
2. Load the message into a PID-unique tmux buffer
3. Paste that buffer into the target pane
4. Clean up the temporary buffer
5. Press Enter to submit

For Gemini CLI specifically, the script sends an `Escape` key first to exit shell mode before pasting.

### Chatroom and Archiving

`./chat` appends messages to `chatroom.md` in Markdown format:

```
**[Claude]** (2026-03-19 20:14:04): I've finished the auth module
```

`./archive` moves messages older than N minutes to `chatroom_archive.md`, keeping the active chatroom lean while preserving full history. `./chat-daemon` runs this automatically on a configurable interval.

### Web UI

`chatserver.py` is a lightweight Python HTTP server that reads the same chatroom files and shells out to the same `./chat` and `./send` scripts. No duplicate logic — the web UI follows identical locking, formatting, and delivery behavior as the CLI tools.

## Security

### Localhost-Only Web UI

The web server binds to `127.0.0.1` by default. The `/api/send` endpoint can forward messages into agent panes, so exposing it to a network would allow prompt injection. Override with `CHATSERVER_BIND=0.0.0.0` only on trusted networks.

### XSS Protection

All chat content is escaped via `textContent` before DOM insertion. Raw HTML in messages is rendered as text, not executed.

### Error Propagation

The toolkit fails loudly rather than reporting false success:

- All scripts fail fast if `team.conf` is missing
- `./chat` stops on lock or append failures
- `./send` stops if any tmux buffer step fails
- `chatserver.py` returns HTTP 500 when scripts fail

### Trust Model

This project is designed for trusted local environments where one user orchestrates multiple agent CLIs. It is not an internet-facing service. If you expose the web UI beyond localhost, add authentication first.

## Configuration

All settings live in `team.conf`:

| Variable | Default | Description |
|----------|---------|-------------|
| `TMUX_TARGET` | `1:0` | Tmux session:window to target |
| `PANE_CLAUDE` | `0` | Pane index for agent 1 |
| `PANE_GEMINI` | `1` | Pane index for agent 2 |
| `PANE_CODEX` | `2` | Pane index for agent 3 |
| `AGENT_CLAUDE` | `Claude` | Display name for agent 1 |
| `AGENT_GEMINI` | `Gemini` | Display name for agent 2 |
| `AGENT_CODEX` | `Codex` | Display name for agent 3 |
| `ARCHIVE_KEEP_MINUTES` | `20` | Minutes of chat history to keep |
| `DAEMON_INTERVAL` | `300` | Seconds between archive runs |

## Prerequisites

- **tmux** (any recent version)
- **bash** 4+
- **flock** (part of `util-linux`, preinstalled on most Linux distros)
- **Python 3** (for the web UI only)
- At least one AI coding CLI: [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [Gemini CLI](https://github.com/google-gemini/gemini-cli), or [OpenAI Codex CLI](https://github.com/openai/codex)

## File Layout

```
your-project/
├── team.conf                          # Configuration
├── chat                               # Post to chatroom
├── send                               # Direct message to pane
├── notify                             # Ephemeral ping
├── archive                            # Archive old messages
├── chat-daemon                        # Background archiver
├── chatserver.py                      # Web UI for chatroom
├── chatroom.md                        # Active chatroom (gitignored)
├── chatroom_archive.md                # Archived messages (gitignored)
├── TEAM_TOOLS.md                      # Reference doc
├── screenshots/                       # README images
└── .claude/
    └── skills/
        └── hackathon/
            ├── SKILL.md               # Claude Code skill
            └── references/
                └── safety.md          # Implementation details
```

## License

MIT
