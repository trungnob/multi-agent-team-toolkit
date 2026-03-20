#!/usr/bin/env python3
"""Lightweight web UI for the team chatroom. Run on port 9091."""
import http.server
import json
import os
import subprocess
import html

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("CHATSERVER_PORT", 9091))
# Default to 127.0.0.1 for safety; allow override for trusted networks
BIND_ADDR = os.environ.get("CHATSERVER_BIND", "127.0.0.1")
CHATROOM = os.path.join(SCRIPT_DIR, "chatroom.md")
ARCHIVE = os.path.join(SCRIPT_DIR, "chatroom_archive.md")
CHAT_SCRIPT = os.path.join(SCRIPT_DIR, "chat")
SEND_SCRIPT = os.path.join(SCRIPT_DIR, "send")

# Read team.conf to get pane list
def _read_team_conf():
    """Parse team.conf for pane numbers."""
    conf = {}
    conf_path = os.path.join(SCRIPT_DIR, "team.conf")
    if os.path.exists(conf_path):
        with open(conf_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    conf[key.strip()] = val.strip().strip('"').strip("'")
    return conf

HTML = r"""<!DOCTYPE html>
<html>
<head>
<title>Team Chat</title>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace; background: #1a1a2e; color: #e0e0e0; height: 100vh; display: flex; flex-direction: column; }

  /* Header */
  header { background: #16213e; padding: 12px 20px; border-bottom: 1px solid #0f3460; display: flex; justify-content: space-between; align-items: center; }
  header h1 { font-size: 16px; color: #e94560; }
  header .status { font-size: 12px; color: #888; }
  .tab-bar { display: flex; gap: 4px; }
  .tab { padding: 6px 12px; cursor: pointer; border-radius: 4px 4px 0 0; font-size: 12px; }
  .tab.active { background: #1a1a2e; color: #e94560; }
  .tab:not(.active) { background: #0f3460; color: #888; }

  /* Chat area */
  #chat { flex: 1; overflow-y: auto; padding: 16px 20px; }
  .msg { margin-bottom: 12px; line-height: 1.5; }
  .msg strong { color: #e94560; }
  .msg .claude { color: #7c83ff; }
  .msg .gemini { color: #34d399; }
  .msg .codex { color: #fbbf24; }
  .msg .user { color: #f472b6; }
  .msg.user-msg { background: #2d1b3d; border-left: 3px solid #f472b6; padding: 8px 12px; border-radius: 4px; margin: 8px 0; }
  .msg .ts { color: #666; font-size: 11px; }
  .separator { border-top: 1px solid #333; margin: 16px 0; padding-top: 8px; color: #555; font-size: 12px; }

  /* Input area */
  #input-area { background: #16213e; padding: 12px 20px; border-top: 1px solid #0f3460; display: flex; gap: 8px; }
  #msg-input { flex: 1; background: #0f3460; border: 1px solid #333; color: #e0e0e0; padding: 10px 14px; border-radius: 6px; font-size: 14px; font-family: inherit; }
  #msg-input:focus { outline: none; border-color: #e94560; }
  #name-select { background: #0f3460; border: 1px solid #333; color: #e0e0e0; padding: 10px; border-radius: 6px; font-size: 14px; }
  button { background: #e94560; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold; }
  button:hover { background: #c73651; }
</style>
</head>
<body>
<header>
  <h1>Team Chat</h1>
  <div class="tab-bar">
    <div class="tab active" onclick="switchTab('live')">Live</div>
    <div class="tab" onclick="switchTab('archive')">Archive</div>
  </div>
  <div class="status" id="status">Connecting...</div>
</header>
<div id="chat"></div>
<div id="input-area">
  <select id="name-select">
    <option value="User">User</option>
  </select>
  <input id="msg-input" placeholder="Type a message..." onkeydown="if(event.key==='Enter')sendMsg()">
  <button onclick="sendMsg()">Send</button>
</div>

<script>
let currentTab = 'live';
let lastContent = '';

function colorName(name) {
  const n = name.toLowerCase();
  if (n.includes('claude')) return 'claude';
  if (n.includes('gemini')) return 'gemini';
  if (n.includes('codex')) return 'codex';
  if (n.includes('user')) return 'user';
  return '';
}

function esc(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function renderChat(md) {
  const chat = document.getElementById('chat');
  const wasAtBottom = chat.scrollHeight - chat.scrollTop - chat.clientHeight < 50;
  let html = '';
  for (const line of md.split('\n')) {
    const m = line.match(/^\*\*\[(.+?)\]\*\*\s*\(([^)]+)\):\s*(.+)/);
    if (m) {
      const cls = colorName(m[1]);
      const isUser = m[1] === 'User';
      const name = esc(m[1]);
      const ts = esc(m[2]);
      const content = esc(m[3]);
      html += `<div class="msg${isUser ? ' user-msg' : ''}"><strong class="${cls}">[${name}]</strong> <span class="ts">(${ts})</span>: ${content}</div>`;
    } else if (line.startsWith('### ')) {
      html += `<div class="separator">${esc(line.replace('### ', ''))}</div>`;
    } else if (line.startsWith('# ') || line.startsWith('## ')) {
      html += `<div style="color:#e94560;font-size:14px;font-weight:bold;margin:12px 0 6px">${esc(line.replace(/^#+\s*/, ''))}</div>`;
    } else if (line.startsWith('---')) {
      html += '<hr style="border-color:#333;margin:8px 0">';
    } else if (line.trim() && !line.startsWith('- ')) {
      html += `<div class="msg">${esc(line)}</div>`;
    } else if (line.startsWith('- ')) {
      html += `<div style="margin:2px 0 2px 16px;font-size:13px">&bull; ${esc(line.slice(2))}</div>`;
    }
  }
  chat.innerHTML = html;
  if (wasAtBottom) chat.scrollTop = chat.scrollHeight;
}

async function refresh() {
  try {
    const endpoint = currentTab === 'archive' ? '/api/archive' : '/api/chat';
    const r = await fetch(endpoint);
    const data = await r.json();
    if (data.content !== lastContent) {
      lastContent = data.content;
      renderChat(data.content);
    }
    document.getElementById('status').textContent = `Live \u2022 ${new Date().toLocaleTimeString()}`;
  } catch(e) {
    document.getElementById('status').textContent = 'Disconnected';
  }
}

function switchTab(tab) {
  currentTab = tab;
  lastContent = '';
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`.tab[onclick*="${tab}"]`).classList.add('active');
  refresh();
}

async function sendMsg() {
  const input = document.getElementById('msg-input');
  const name = document.getElementById('name-select').value;
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  const r = await fetch('/api/send', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name, message: msg})
  });
  const data = await r.json();
  if (!data.ok) {
    alert("Error sending message: " + (data.error || "unknown error"));
  }
  setTimeout(refresh, 500);
}

// Load agent names from team.conf into the name selector
fetch('/api/agents').then(r => r.json()).then(data => {
  const sel = document.getElementById('name-select');
  for (const name of data.agents || []) {
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name;
    sel.appendChild(opt);
  }
});

setInterval(refresh, 2000);
refresh();
</script>
</body>
</html>"""


class ChatHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress logs

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
        elif self.path == '/api/chat':
            self._serve_file(CHATROOM)
        elif self.path == '/api/archive':
            self._serve_file(ARCHIVE)
        elif self.path == '/api/agents':
            conf = _read_team_conf()
            agents = [v for k, v in sorted(conf.items()) if k.startswith("AGENT_")]
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"agents": agents}).encode())
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/api/send':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            name = body.get('name', 'User')
            message = body.get('message', '')
            
            error = None
            if message:
                # 1. Post to chatroom
                res = subprocess.run([CHAT_SCRIPT, name, message], capture_output=True, text=True)
                if res.returncode != 0:
                    error = f"Chat script failed: {res.stderr}"
                
                # 2. If User posts, broadcast directly to all agent panes
                if not error and name == 'User':
                    conf = _read_team_conf()
                    panes = [v for k, v in sorted(conf.items()) if k.startswith("PANE_")]
                    for pane in panes:
                        res = subprocess.run(
                            [SEND_SCRIPT, "--from", name, pane, message],
                            capture_output=True,
                            text=True
                        )
                        if res.returncode != 0:
                            error = f"Send script failed for pane {pane}: {res.stderr}"
                            break

            if error:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": error}).encode())
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"ok":true}')
        else:
            self.send_error(404)

    def _serve_file(self, path):
        try:
            with open(path, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            content = "(empty)"
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"content": content}).encode())


if __name__ == '__main__':
    server = http.server.HTTPServer((BIND_ADDR, PORT), ChatHandler)
    print(f"Team Chat running at http://{BIND_ADDR}:{PORT}")
    server.serve_forever()
