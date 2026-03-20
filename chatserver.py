#!/usr/bin/env python3
"""Lightweight web UI for the team chatroom."""

import cgi
import http.server
import imghdr
import json
import os
import subprocess
import uuid

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("CHATSERVER_PORT", 9091))
BIND_ADDR = os.environ.get("CHATSERVER_BIND", "127.0.0.1")
MAX_JSON_BYTES = int(os.environ.get("CHATSERVER_MAX_JSON_BYTES", 262144))
MAX_UPLOAD_BYTES = int(os.environ.get("CHATSERVER_MAX_UPLOAD_BYTES", 8 * 1024 * 1024))
CHATROOM = os.path.join(SCRIPT_DIR, "chatroom.md")
ARCHIVE = os.path.join(SCRIPT_DIR, "chatroom_archive.md")
UPLOADS_DIR = os.path.join(SCRIPT_DIR, "uploads")
CHAT_SCRIPT = os.path.join(SCRIPT_DIR, "chat")
SEND_SCRIPT = os.path.join(SCRIPT_DIR, "send")

os.makedirs(UPLOADS_DIR, exist_ok=True)


def _read_team_conf():
    """Parse team.conf for pane numbers and agent names."""
    conf = {}
    conf_path = os.path.join(SCRIPT_DIR, "team.conf")
    if os.path.exists(conf_path):
        with open(conf_path, encoding="utf-8") as handle:
            for line in handle:
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
  header { background: #16213e; padding: 12px 20px; border-bottom: 1px solid #0f3460; display: flex; justify-content: space-between; align-items: center; }
  header h1 { font-size: 16px; color: #e94560; }
  header .status { font-size: 12px; color: #888; }
  .tab-bar { display: flex; gap: 4px; }
  .tab { padding: 6px 12px; cursor: pointer; border-radius: 4px 4px 0 0; font-size: 12px; }
  .tab.active { background: #1a1a2e; color: #e94560; }
  .tab:not(.active) { background: #0f3460; color: #888; }
  #chat { flex: 1; overflow-y: auto; padding: 16px 20px; }
  .msg { margin-bottom: 12px; line-height: 1.5; }
  .msg strong { color: #e94560; }
  .msg .claude { color: #7c83ff; }
  .msg .gemini { color: #34d399; }
  .msg .codex { color: #fbbf24; }
  .msg .user { color: #f472b6; }
  .msg.user-msg { background: #2d1b3d; border-left: 3px solid #f472b6; padding: 8px 12px; border-radius: 4px; margin: 8px 0; }
  .msg .ts { color: #666; font-size: 11px; }
  .msg img { max-width: 100%; max-height: 420px; border-radius: 8px; margin-top: 8px; border: 1px solid #333; display: block; }
  .separator { border-top: 1px solid #333; margin: 16px 0; padding-top: 8px; color: #555; font-size: 12px; }
  #input-area { background: #16213e; padding: 12px 20px; border-top: 1px solid #0f3460; display: flex; flex-direction: column; gap: 8px; }
  #composer-row { display: flex; gap: 8px; align-items: center; }
  #msg-input { flex: 1; background: #0f3460; border: 1px solid #333; color: #e0e0e0; padding: 10px 14px; border-radius: 6px; font-size: 14px; font-family: inherit; }
  #msg-input:focus { outline: none; border-color: #e94560; }
  #name-select { background: #0f3460; border: 1px solid #333; color: #e0e0e0; padding: 10px; border-radius: 6px; font-size: 14px; }
  button { background: #e94560; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold; }
  button:hover { background: #c73651; }
  .secondary-btn { background: #0f3460; border: 1px solid #333; }
  .secondary-btn:hover { background: #173d69; }
  .hint { font-size: 11px; color: #666; }
  #file-input { display: none; }
  #pending-image { display: none; border: 1px solid #333; border-radius: 8px; padding: 10px; background: #0f3460; }
  #pending-image.visible { display: flex; gap: 12px; align-items: flex-start; }
  #pending-image img { max-width: 220px; max-height: 180px; border-radius: 6px; border: 1px solid #333; }
  #pending-image-meta { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
  #pending-image-name { font-size: 12px; color: #aaa; word-break: break-all; }
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
  <div id="pending-image">
    <img id="pending-image-preview" alt="Pending image preview">
    <div id="pending-image-meta">
      <div id="pending-image-name"></div>
      <div class="hint">Paste anywhere in the page or click Image, then click Send.</div>
      <div><button class="secondary-btn" onclick="clearPendingImage()">Remove</button></div>
    </div>
  </div>
  <div id="composer-row">
    <select id="name-select">
      <option value="User">User</option>
    </select>
    <input id="msg-input" placeholder="Type a message or attach a screenshot..." onkeydown="if(event.key==='Enter')sendMsg()">
    <input id="file-input" type="file" accept="image/*">
    <button class="secondary-btn" onclick="openImagePicker()">Image</button>
    <button onclick="sendMsg()">Send</button>
  </div>
  <div class="hint">Paste screenshot with Ctrl+V / Cmd+V, or use Image.</div>
</div>

<script>
let currentTab = 'live';
let lastContent = '';
let pendingImage = null;

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

function renderMessageContent(content) {
  const imageRe = /!\[(.*?)\]\((uploads\/[^)\s]+)\)/g;
  let rendered = '';
  let cursor = 0;
  let match;

  while ((match = imageRe.exec(content)) !== null) {
    rendered += esc(content.slice(cursor, match.index));
    rendered += `<img src="/${match[2]}" alt="${esc(match[1])}">`;
    cursor = match.index + match[0].length;
  }

  rendered += esc(content.slice(cursor));
  return rendered;
}

function renderChat(md) {
  const chat = document.getElementById('chat');
  const wasAtBottom = chat.scrollHeight - chat.scrollTop - chat.clientHeight < 50;
  let html = '';
  for (const line of md.split('\n')) {
    const m = line.match(/^\*\*\[(.+?)\]\*\*\s*\(([^)]+)\):\s*(.*)/);
    if (m) {
      const cls = colorName(m[1]);
      const isUser = m[1] === 'User';
      const name = esc(m[1]);
      const ts = esc(m[2]);
      const content = renderMessageContent(m[3]);
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

function currentTabLabel() {
  return currentTab.charAt(0).toUpperCase() + currentTab.slice(1);
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
    document.getElementById('status').textContent = `${currentTabLabel()} • ${new Date().toLocaleTimeString()}`;
  } catch (e) {
    document.getElementById('status').textContent = 'Disconnected';
  }
}

function switchTab(tab) {
  currentTab = tab;
  lastContent = '';
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  const targetTab = Array.from(document.querySelectorAll('.tab')).find(t => t.textContent.toLowerCase().includes(tab));
  if (targetTab) targetTab.classList.add('active');
  refresh();
}

function setPendingImage(file, dataUrl) {
  pendingImage = { file, dataUrl };
  document.getElementById('pending-image-preview').src = dataUrl;
  document.getElementById('pending-image-name').textContent = `${file.name || 'pasted-image'} • ${Math.round(file.size / 1024)} KB`;
  document.getElementById('pending-image').classList.add('visible');
}

function clearPendingImage() {
  pendingImage = null;
  document.getElementById('pending-image').classList.remove('visible');
  document.getElementById('pending-image-preview').removeAttribute('src');
  document.getElementById('pending-image-name').textContent = '';
  document.getElementById('file-input').value = '';
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('Could not read image'));
    reader.readAsDataURL(file);
  });
}

async function queueImageFile(file) {
  if (!file || !file.type.startsWith('image/')) return;
  const dataUrl = await fileToDataUrl(file);
  setPendingImage(file, dataUrl);
  document.getElementById('status').textContent = 'Image attached';
}

function openImagePicker() {
  document.getElementById('file-input').click();
}

async function sendMsg() {
  const input = document.getElementById('msg-input');
  const name = document.getElementById('name-select').value;
  const msg = input.value.trim();
  if (!msg && !pendingImage) return;

  if (pendingImage) {
    const formData = new FormData();
    formData.append('image', pendingImage.file, pendingImage.file.name || 'pasted-image.png');
    formData.append('name', name);
    formData.append('message', msg);
    document.getElementById('status').textContent = 'Uploading image...';
    const r = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await r.json();
    if (!data.ok) {
      alert("Upload failed: " + (data.error || "unknown error"));
      return;
    }
    input.value = '';
    clearPendingImage();
    setTimeout(refresh, 500);
    return;
  }

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

document.getElementById('file-input').addEventListener('change', async (e) => {
  const [file] = e.target.files;
  if (file) {
    await queueImageFile(file);
  }
});

document.addEventListener('paste', async (e) => {
  const clipboardItems = Array.from((e.clipboardData || window.clipboardData || {}).items || []);
  for (const item of clipboardItems) {
    if (item.type && item.type.startsWith('image/')) {
      e.preventDefault();
      const file = item.getAsFile();
      if (file) {
        await queueImageFile(file);
      }
      break;
    }
  }
});

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
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
        elif self.path == "/api/chat":
            self._serve_file(CHATROOM)
        elif self.path == "/api/archive":
            self._serve_file(ARCHIVE)
        elif self.path == "/api/agents":
            conf = _read_team_conf()
            agents = [v for k, v in sorted(conf.items()) if k.startswith("AGENT_")]
            self._send_json({"agents": agents})
        elif self.path.startswith("/uploads/"):
            filename = os.path.basename(self.path[len("/uploads/"):])
            self._serve_static(os.path.join(UPLOADS_DIR, filename))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/send":
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length <= 0 or length > MAX_JSON_BYTES:
                self._send_json({"ok": False, "error": "Invalid request size"}, 400)
                return
            try:
                body = json.loads(self.rfile.read(length))
            except json.JSONDecodeError:
                self._send_json({"ok": False, "error": "Invalid JSON"}, 400)
                return
            name = str(body.get("name", "User"))
            message = str(body.get("message", ""))
            self._process_message(name, message)
        elif self.path == "/api/upload":
            self._handle_upload()
        else:
            self.send_error(404)

    def _handle_upload(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            self._send_json({"ok": False, "error": "Empty upload"}, 400)
            return
        if length > MAX_UPLOAD_BYTES:
            self._send_json({"ok": False, "error": "Upload exceeds size limit"}, 413)
            return

        ctype, pdict = cgi.parse_header(self.headers.get("Content-Type", ""))
        if ctype != "multipart/form-data" or "boundary" not in pdict:
            self._send_json({"ok": False, "error": "Expected multipart/form-data"}, 400)
            return

        pdict["boundary"] = pdict["boundary"].encode()
        fields = cgi.parse_multipart(self.rfile, pdict)
        image_items = fields.get("image")
        if not image_items:
            self._send_json({"ok": False, "error": "No image uploaded"}, 400)
            return

        image_data = image_items[0]
        name = fields.get("name", ["User"])[0]
        message = fields.get("message", [""])[0]
        if isinstance(name, bytes):
            name = name.decode("utf-8", "replace")
        if isinstance(message, bytes):
            message = message.decode("utf-8", "replace")

        image_kind = imghdr.what(None, image_data)
        ext = {
            "jpeg": "jpg",
            "png": "png",
            "gif": "gif",
            "webp": "webp",
        }.get(image_kind)
        if ext is None:
            self._send_json({"ok": False, "error": "Unsupported image format"}, 400)
            return

        filename = f"ss_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(UPLOADS_DIR, filename)
        with open(filepath, "wb") as handle:
            handle.write(image_data)

        image_markup = f"![screenshot](uploads/{filename})"
        combined_message = image_markup if not message else f"{message} {image_markup}"
        self._process_message(str(name), combined_message)

    def _process_message(self, name, message):
        error = None
        if message:
            res = subprocess.run([CHAT_SCRIPT, name, message], capture_output=True, text=True, check=False)
            if res.returncode != 0:
                error = f"Chat script failed: {res.stderr.strip()}"

            if not error and name == "User":
                res = subprocess.run(
                    [SEND_SCRIPT, "--all", f"[{name}]: {message}"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res.returncode != 0:
                    detail = res.stderr.strip() or res.stdout.strip()
                    error = f"Send script failed: {detail}"

        if error:
            self._send_json({"ok": False, "error": error}, 500)
        else:
            self._send_json({"ok": True}, 200)

    def _serve_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
        except FileNotFoundError:
            content = "(empty)"
        self._send_json({"content": content})

    def _serve_static(self, path):
        if not os.path.exists(path):
            self.send_error(404)
            return

        ext = os.path.splitext(path)[1].lower()
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(ext, "application/octet-stream")

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.end_headers()
        with open(path, "rb") as handle:
            self.wfile.write(handle.read())

    def _send_json(self, payload, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer((BIND_ADDR, PORT), ChatHandler)
    print(f"Team Chat running at http://{BIND_ADDR}:{PORT}")
    server.serve_forever()
