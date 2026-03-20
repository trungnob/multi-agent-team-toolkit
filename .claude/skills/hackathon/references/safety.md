# Concurrency Safety & Implementation Details

## Locking Strategy

All scripts use `flock` to serialize access to shared resources. Lock files are stored in `/tmp/` and keyed by an MD5 hash of the project directory path to avoid collisions between multiple clones.

### Lock Files

| Lock | Protects | Used by |
|------|----------|---------|
| `team_<hash>_chatroom.lock` | Chatroom file writes | `chat`, `archive` |
| `team_<hash>_tmux_send.lock` | Tmux buffer operations | `send` |
| `team_<hash>_chat_daemon.lock` | Daemon PID file | `chat-daemon` |

### How It Works

```bash
PROJECT_HASH=$(printf "%s" "$SCRIPT_DIR" | md5sum | cut -c1-8)
LOCKFILE="/tmp/team_${PROJECT_HASH}_chatroom.lock"

(
  flock -w 10 200 || { echo "ERROR: Could not acquire lock"; exit 1; }
  # ... critical section ...
) 200>"$LOCKFILE"
```

## Tmux Buffer Safety (`send` script)

The `send` script uses tmux `load-buffer` + `paste-buffer` instead of `send-keys` to avoid character escaping issues with special characters.

### Per-PID Buffer Names

Each invocation uses a PID-unique buffer name (`send_$$`) to prevent concurrent sends from clobbering each other. A cleanup trap ensures the buffer is deleted even if the script exits unexpectedly.

### Gemini Escape Workaround

When sending to the Gemini CLI pane, the script first checks whether Gemini visibly shows `!` shell mode, a suggestion overlay, or a busy "Working/Thinking" title. It only sends `Escape` when shell mode or suggestions are actually visible, clears any stale input with `Ctrl+U`, and refuses to queue a new message while Gemini is still working. Delivery still uses `send-keys -l` instead of `paste-buffer`. That avoids the bug where stale or pasted text gets interpreted as a shell command or accumulates in Gemini's chat box.

## Chatroom Archiving

The `archive` script keeps `chatroom.md` lean by moving messages older than N minutes (configurable via `ARCHIVE_KEEP_MINUTES` in `team.conf`) to `chatroom_archive.md`.

### Block Parsing

Messages are split into blocks using a pure bash `while read` loop (not awk with NUL delimiters) for compatibility with both gawk and mawk. Each block starts with a `**[` line and includes all subsequent lines until the next `**[`.

### Daemon

`chat-daemon` runs `archive` on a configurable interval (`DAEMON_INTERVAL` in `team.conf`). It uses a PID file with flock protection to prevent duplicate daemons.

## Fail-Fast on Missing Config

All scripts check for `team.conf` before sourcing it. If missing, they print an error and exit immediately rather than running with undefined variables.

## Web Chat Trust Model

The browser chat UI is still a trust-based local tool. Until authentication exists, treat it as the human operator's `User` channel rather than a verified multi-user identity system.

- Agents should use `./chat`, `./chat --sync`, `./send`, and `./notify` for routine team coordination.
- Do not use normal browser posts for agent-to-agent messaging.
- If browser-side debugging is unavoidable, label the post clearly, for example `[DEBUG Codex]`, so it cannot be mistaken for a normal user-authored message.
