#!/usr/bin/env python3
"""Lightweight web UI for the team chatroom."""
import cgi
import html
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
PROPOSAL = os.path.join(SCRIPT_DIR, "proposal.md")
DEMO = os.path.join(SCRIPT_DIR, "demo.md")
DECK = os.path.join(SCRIPT_DIR, "deck.md")
RECORDING = os.path.join(SCRIPT_DIR, "recording.md")
PRESENTATION_HTML = os.path.join(SCRIPT_DIR, "CareFlow_Presentation.html")
ACTIONS = os.path.join(SCRIPT_DIR, "actions.json")
UPLOADS_DIR = os.path.join(SCRIPT_DIR, "uploads")
CHAT_SCRIPT = os.path.join(SCRIPT_DIR, "chat")
SEND_SCRIPT = os.path.join(SCRIPT_DIR, "send")

os.makedirs(UPLOADS_DIR, exist_ok=True)


def _read_team_conf():
    """Parse team.conf for pane numbers and agent names."""
    conf = {}
    conf_path = os.path.join(SCRIPT_DIR, "team.conf")
    if os.path.exists(conf_path):
        with open(conf_path, encoding="utf-8") as f:
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
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
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
  .proposal { max-width: 980px; margin: 0 auto; line-height: 1.6; }
  .proposal h1, .proposal h2, .proposal h3 { color: #f8fafc; margin: 16px 0 8px; }
  .proposal h1 { font-size: 26px; color: #e94560; }
  .proposal h2 { font-size: 20px; color: #fbbf24; border-bottom: 1px solid #333; padding-bottom: 4px; }
  .proposal h3 { font-size: 16px; color: #7dd3fc; }
  .proposal p { margin: 10px 0; color: #e5e7eb; }
  .proposal ul, .proposal ol { margin: 8px 0 12px 22px; }
  .proposal li { margin: 4px 0; }
  .proposal hr { border: 0; border-top: 1px solid #333; margin: 18px 0; }
  .proposal code { background: #0f3460; color: #f8fafc; border-radius: 4px; padding: 1px 5px; }
  .proposal pre { background: #111827; border: 1px solid #334155; border-radius: 8px; padding: 12px; overflow-x: auto; margin: 12px 0; }
  .proposal pre code { background: transparent; padding: 0; }
  .proposal table { width: 100%; border-collapse: collapse; margin: 12px 0 18px; font-size: 13px; }
  .proposal th, .proposal td { border: 1px solid #334155; padding: 8px 10px; vertical-align: top; text-align: left; }
  .proposal th { background: #0f3460; color: #f8fafc; }
  .proposal tbody tr:nth-child(even) { background: rgba(15, 52, 96, 0.25); }
  .proposal a { color: #7dd3fc; }
  .proposal blockquote { border-left: 3px solid #e94560; margin: 12px 0; padding: 4px 0 4px 12px; color: #cbd5e1; }
  .proposal .mermaid-wrap { background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 12px; margin: 14px 0; overflow-x: auto; }
  .proposal .mermaid-fallback { white-space: pre-wrap; }
  .proposal img, .proposal-content img {
    display: block;
    width: 100%;
    max-width: 980px;
    height: auto;
    border-radius: 12px;
    border: 1px solid #334155;
    margin: 14px auto;
    background: #fff;
  }
  .slides-frame {
    width: 100%;
    height: calc(100vh - 120px);
    border: 0;
    background: #fff;
    border-radius: 10px;
  }

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

  /* Proposal tab rich markdown styles */
  .proposal-content { padding: 20px; max-width: 900px; margin: 0 auto; }
  .proposal-content h1 { color: #e94560; font-size: 24px; margin: 24px 0 12px; border-bottom: 2px solid #e94560; padding-bottom: 8px; }
  .proposal-content h2 { color: #7c83ff; font-size: 18px; margin: 20px 0 10px; border-bottom: 1px solid #333; padding-bottom: 6px; }
  .proposal-content h3 { color: #34d399; font-size: 15px; margin: 16px 0 8px; }
  .proposal-content p { margin: 8px 0; line-height: 1.7; }
  .proposal-content ul, .proposal-content ol { margin: 8px 0 8px 24px; line-height: 1.7; }
  .proposal-content li { margin: 4px 0; }
  .proposal-content table { border-collapse: collapse; width: 100%; margin: 12px 0; }
  .proposal-content th { background: #0f3460; color: #e94560; padding: 10px 14px; text-align: left; border: 1px solid #333; font-size: 13px; }
  .proposal-content td { padding: 8px 14px; border: 1px solid #333; font-size: 13px; }
  .proposal-content tr:nth-child(even) { background: #16213e; }
  .proposal-content code { background: #0f3460; padding: 2px 6px; border-radius: 3px; font-size: 13px; color: #fbbf24; }
  .proposal-content pre { background: #0a0a1a; padding: 16px; border-radius: 8px; overflow-x: auto; margin: 12px 0; border: 1px solid #333; }
  .proposal-content pre code { background: none; padding: 0; color: #e0e0e0; }
  .proposal-content blockquote { border-left: 3px solid #e94560; padding: 8px 16px; margin: 12px 0; background: #16213e; border-radius: 0 4px 4px 0; }
  .proposal-content hr { border: none; border-top: 1px solid #333; margin: 20px 0; }
  .proposal-content strong { color: #f0f0f0; }
  .proposal-content .mermaid { background: #f8f8f8; border-radius: 8px; padding: 16px; margin: 16px 0; text-align: center; }
  .proposal-content .mermaid svg { max-width: 100%; }

  /* Actions tab styles */
  .actions-wrap { padding: 20px; max-width: 700px; margin: 0 auto; }
  .actions-wrap h1 { color: #e94560; font-size: 22px; margin: 0 0 6px; }
  .actions-wrap .subtitle { color: #888; font-size: 13px; margin-bottom: 20px; }
  .actions-section { margin-bottom: 24px; }
  .actions-section h2 { color: #7c83ff; font-size: 16px; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 1px solid #333; }
  .actions-section .deadline { color: #fbbf24; font-size: 12px; margin-left: 8px; }
  .action-item { display: flex; align-items: flex-start; gap: 12px; padding: 10px 14px; margin: 6px 0; background: #16213e; border-radius: 6px; border: 1px solid #333; cursor: pointer; transition: all 0.15s; }
  .action-item:hover { border-color: #7c83ff; background: #1a2540; }
  .action-item.done { opacity: 0.5; border-color: #34d399; }
  .action-item.done .action-text { text-decoration: line-through; }
  .action-item input[type=checkbox] { margin-top: 3px; accent-color: #34d399; width: 18px; height: 18px; cursor: pointer; flex-shrink: 0; }
  .action-text { flex: 1; }
  .action-text .title { font-size: 14px; color: #e0e0e0; font-weight: 600; }
  .action-text .detail { font-size: 12px; color: #888; margin-top: 4px; line-height: 1.5; }
  .action-text .steps { margin: 8px 0 0 18px; color: #b8c4d3; font-size: 12px; line-height: 1.6; }
  .action-text .steps li { margin: 3px 0; }
  .action-text .time { display: inline-block; background: #0f3460; color: #7dd3fc; font-size: 11px; padding: 2px 8px; border-radius: 10px; margin-top: 4px; }
  .action-text .tag { display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 10px; margin-top: 4px; margin-left: 4px; }
  .tag.now { background: #e94560; color: #fff; }
  .tag.later { background: #0f3460; color: #fbbf24; }
  .tag.optional { background: #1a1a2e; color: #888; border: 1px solid #333; }
  .actions-progress { background: #0a0a1a; border-radius: 8px; padding: 16px; margin-bottom: 20px; border: 1px solid #333; }
  .actions-progress .bar-bg { background: #16213e; height: 12px; border-radius: 6px; overflow: hidden; margin-top: 8px; }
  .actions-progress .bar-fill { background: linear-gradient(90deg, #34d399, #7c83ff); height: 100%; border-radius: 6px; transition: width 0.3s; }
  .actions-progress .label { font-size: 13px; color: #e0e0e0; }

  /* Action modal overlay */
  .action-modal-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 100; justify-content: center; align-items: center; padding: 20px; }
  .action-modal-overlay.open { display: flex; }
  .action-modal { background: #16213e; border: 1px solid #7c83ff; border-radius: 12px; max-width: 600px; width: 100%; max-height: 80vh; overflow-y: auto; padding: 24px; box-shadow: 0 8px 32px rgba(0,0,0,0.5); }
  .action-modal h2 { color: #e94560; font-size: 18px; margin-bottom: 4px; }
  .action-modal .modal-deadline { color: #fbbf24; font-size: 12px; margin-bottom: 16px; }
  .action-modal .modal-steps { font-size: 14px; line-height: 2; color: #e0e0e0; user-select: text; }
  .action-modal .modal-steps a { color: #7dd3fc; text-decoration: underline; }
  .action-modal .modal-steps a:hover { color: #fff; }
  .action-modal .modal-tags { margin-top: 16px; }
  .action-modal .modal-footer { display: flex; gap: 10px; margin-top: 20px; justify-content: flex-end; }
  .action-modal .modal-footer button { font-size: 13px; padding: 8px 16px; }
  .action-modal .btn-done { background: #34d399; color: #000; }
  .action-modal .btn-done:hover { background: #2ab88a; }
  .action-modal .btn-close { background: #333; color: #e0e0e0; }
  .action-modal .btn-close:hover { background: #444; }
</style>
</head>
<body>
<header>
  <h1>Team Chat</h1>
  <div class="tab-bar">
    <div class="tab active" onclick="switchTab('live')">Live</div>
    <div class="tab" onclick="switchTab('archive')">Archive</div>
    <div class="tab" onclick="switchTab('proposal')">Proposal</div>
    <div class="tab" onclick="switchTab('demo')">Demo</div>
    <div class="tab" onclick="switchTab('deck')">Deck</div>
    <div class="tab" onclick="switchTab('slides')">Slides</div>
    <div class="tab" onclick="switchTab('recording')">Recording</div>
    <div class="tab" onclick="switchTab('actions')">Actions for User</div>
  </div>
  <div class="status" id="status">Connecting...</div>
  <div class="status" id="tmux-info" style="font-size:11px;color:#888;"></div>
</header>
<div id="chat"></div>
<div class="action-modal-overlay" id="action-modal" onclick="if(event.target===this)closeModal()">
  <div class="action-modal">
    <h2 id="modal-title"></h2>
    <div class="modal-deadline" id="modal-deadline"></div>
    <div class="modal-steps" id="modal-steps"></div>
    <div class="modal-tags" id="modal-tags"></div>
    <div class="modal-footer">
      <button class="btn-done" id="modal-copy-btn" onclick="">Copy Details</button>
      <button class="btn-close" onclick="closeModal()">Close</button>
    </div>
  </div>
</div>
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
let mermaidApi = null;

(async function initMermaid() {
  try {
    const mod = await import('https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs');
    mermaidApi = mod.default;
    mermaidApi.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      theme: 'dark',
      themeVariables: {
        primaryColor: '#0f3460',
        primaryTextColor: '#e5e7eb',
        lineColor: '#7dd3fc',
        secondaryColor: '#1f2937',
        tertiaryColor: '#111827',
      },
    });
    if (currentTab === 'proposal') refresh();
  } catch (e) {
    console.warn('Mermaid failed to load', e);
  }
})();

function applyDeliveryStatus(data) {
  const delivered = (data.delivered_targets || []).join(', ');
  const failed = (data.failed_targets || []).map(item => item.target).join(', ');
  if (data.partial) {
    let text = delivered ? `Partial delivery: ${delivered}` : 'Saved to chatroom only';
    if (failed) text += `; skipped ${failed}`;
    document.getElementById('status').textContent = text;
  } else if (delivered) {
    document.getElementById('status').textContent = `Delivered: ${delivered}`;
  }
}

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

function renderInline(text) {
  let out = esc(text);
  out = out.replace(/!\[([^\]]*)\]\((uploads\/[^)\s]+)\)/g, '<img src="/$2" alt="$1">');
  out = out.replace(/`([^`]+)`/g, '<code>$1</code>');
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  out = out.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  out = out.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
  return out;
}

function splitTableRow(line) {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map(cell => cell.trim());
}

function renderProposal(md) {
  const chat = document.getElementById('chat');
  const wasAtBottom = chat.scrollHeight - chat.scrollTop - chat.clientHeight < 50;
  const lines = md.split('\n');
  let html = '<div class="proposal">';
  let paragraph = [];
  let listType = null;
  let inCode = false;
  let codeLang = '';
  let codeLines = [];
  let tableLines = [];

  function flushParagraph() {
    if (!paragraph.length) return;
    html += `<p>${renderInline(paragraph.join(' '))}</p>`;
    paragraph = [];
  }

  function flushList() {
    if (!listType) return;
    html += `</${listType}>`;
    listType = null;
  }

  function flushTable() {
    if (!tableLines.length) return;
    const rows = tableLines.map(splitTableRow);
    tableLines = [];
    if (!rows.length) return;
    const header = rows[0];
    const body = rows.slice(1).filter(row => !row.every(cell => /^:?-{3,}:?$/.test(cell)));
    html += '<table><thead><tr>';
    for (const cell of header) html += `<th>${renderInline(cell)}</th>`;
    html += '</tr></thead><tbody>';
    for (const row of body) {
      html += '<tr>';
      for (const cell of row) html += `<td>${renderInline(cell)}</td>`;
      html += '</tr>';
    }
    html += '</tbody></table>';
  }

  function flushCode() {
    if (!inCode) return;
    const code = codeLines.join('\n');
    if (codeLang === 'mermaid') {
      if (mermaidApi) {
        html += `<div class="mermaid-wrap"><pre class="mermaid">${esc(code)}</pre></div>`;
      } else {
        html += `<div class="mermaid-wrap"><pre class="mermaid-fallback"><code>${esc(code)}</code></pre></div>`;
      }
    } else {
      html += `<pre><code>${esc(code)}</code></pre>`;
    }
    inCode = false;
    codeLang = '';
    codeLines = [];
  }

  for (const line of lines) {
    if (inCode) {
      if (line.startsWith('```')) {
        flushCode();
      } else {
        codeLines.push(line);
      }
      continue;
    }

    if (line.startsWith('```')) {
      flushParagraph();
      flushList();
      flushTable();
      inCode = true;
      codeLang = line.slice(3).trim().toLowerCase();
      codeLines = [];
      continue;
    }

    if (line.trim() === '') {
      flushParagraph();
      flushList();
      flushTable();
      continue;
    }

    if (line.startsWith('|')) {
      flushParagraph();
      flushList();
      tableLines.push(line);
      continue;
    }
    flushTable();

    const heading = line.match(/^(#{1,3})\s+(.*)$/);
    if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1].length;
      html += `<h${level}>${renderInline(heading[2])}</h${level}>`;
      continue;
    }

    if (line.startsWith('---')) {
      flushParagraph();
      flushList();
      html += '<hr>';
      continue;
    }

    if (line.startsWith('> ')) {
      flushParagraph();
      flushList();
      html += `<blockquote>${renderInline(line.slice(2))}</blockquote>`;
      continue;
    }

    const bullet = line.match(/^\s*-\s+(.*)$/);
    if (bullet) {
      flushParagraph();
      if (listType !== 'ul') {
        flushList();
        html += '<ul>';
        listType = 'ul';
      }
      html += `<li>${renderInline(bullet[1])}</li>`;
      continue;
    }

    const numbered = line.match(/^\s*\d+\.\s+(.*)$/);
    if (numbered) {
      flushParagraph();
      if (listType !== 'ol') {
        flushList();
        html += '<ol>';
        listType = 'ol';
      }
      html += `<li>${renderInline(numbered[1])}</li>`;
      continue;
    }

    flushList();
    paragraph.push(line.trim());
  }

  flushParagraph();
  flushList();
  flushTable();
  flushCode();
  html += '</div>';
  chat.innerHTML = html;
  if (mermaidApi) {
    mermaidApi.run({ querySelector: '.mermaid' }).catch(err => console.warn('Mermaid render failed', err));
  }
  if (wasAtBottom) chat.scrollTop = chat.scrollHeight;
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

let actionsData = [];
let activeActionId = null;

async function toggleAction(id) {
  await fetch('/api/actions/toggle', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({id})
  });
  lastContent = '';
  refresh();
}

function linkify(text) {
  return text.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noreferrer">$1</a>');
}

function openActionModal(id) {
  const item = actionsData.find(i => i.id === id);
  if (!item) return;
  activeActionId = id;
  document.getElementById('modal-title').textContent = item.title;
  document.getElementById('modal-deadline').textContent = item.deadline || '';
  let stepsHtml = '';
  if (item.detail) {
    stepsHtml += `<p>${item.detail.split('\n').map(l => linkify(esc(l))).join('<br>')}</p>`;
  }
  if (item.steps && item.steps.length) {
    stepsHtml += '<ol>';
    for (const step of item.steps) {
      stepsHtml += `<li>${linkify(renderInline(step))}</li>`;
    }
    stepsHtml += '</ol>';
  }
  document.getElementById('modal-steps').innerHTML = stepsHtml;
  let tagsHtml = '';
  if (item.time) tagsHtml += `<span class="time">${esc(item.time)}</span>`;
  if (item.priority) tagsHtml += `<span class="tag ${item.priority}">${esc(item.priority)}</span>`;
  document.getElementById('modal-tags').innerHTML = tagsHtml;
  const copyBtn = document.getElementById('modal-copy-btn');
  copyBtn.textContent = 'Copy Details';
  copyBtn.onclick = async () => {
    const lines = [item.title];
    if (item.deadline) lines.push(`Deadline: ${item.deadline}`);
    if (item.detail) lines.push(item.detail);
    if (item.steps && item.steps.length) {
      lines.push('Steps:');
      item.steps.forEach((step, idx) => lines.push(`${idx + 1}. ${step}`));
    }
    try {
      await navigator.clipboard.writeText(lines.join('\n'));
      document.getElementById('status').textContent = 'Action copied';
    } catch (e) {
      document.getElementById('status').textContent = 'Copy failed';
    }
  };
  document.getElementById('action-modal').classList.add('open');
}

function closeModal() {
  activeActionId = null;
  document.getElementById('action-modal').classList.remove('open');
}

function renderActions(data) {
  const chat = document.getElementById('chat');
  const items = data.items || [];
  actionsData = items;
  const done = items.filter(i => i.done).length;
  const total = items.length;
  const pct = total ? Math.round(done / total * 100) : 0;

  let html = '<div class="actions-wrap">';
  html += '<h1>Action Items for User</h1>';
  html += '<div class="subtitle">Click checkbox to mark done. Click the card to open details with copyable links.</div>';

  html += '<div class="actions-progress">';
  html += `<div class="label">${done} of ${total} complete (${pct}%)</div>`;
  html += `<div class="bar-bg"><div class="bar-fill" style="width:${pct}%"></div></div>`;
  html += '</div>';

  let currentSection = '';
  for (const item of items) {
    if (item.section !== currentSection) {
      if (currentSection) html += '</div>';
      currentSection = item.section;
      html += '<div class="actions-section">';
      html += `<h2>${esc(item.section)}`;
      if (item.deadline) html += `<span class="deadline">${esc(item.deadline)}</span>`;
      html += '</h2>';
    }
    const doneClass = item.done ? ' done' : '';
    const checked = item.done ? ' checked' : '';
    html += `<div class="action-item${doneClass}" onclick="openActionModal('${esc(item.id)}')">`;
    html += `<input type="checkbox"${checked} onclick="event.stopPropagation(); toggleAction('${esc(item.id)}')">`;
    html += '<div class="action-text">';
    html += `<div class="title">${renderInline(item.title)}</div>`;
    let tags = '';
    if (item.time) tags += `<span class="time">${esc(item.time)}</span>`;
    if (item.priority) tags += `<span class="tag ${item.priority}">${esc(item.priority)}</span>`;
    if (tags) html += `<div>${tags}</div>`;
    html += '</div></div>';
  }
  if (currentSection) html += '</div>';
  html += '</div>';
  chat.innerHTML = html;
}

async function refresh() {
  try {
    if (currentTab === 'slides') {
      const chat = document.getElementById('chat');
      const html = '<iframe class="slides-frame" src="/slides"></iframe>';
      if (lastContent !== html) {
        lastContent = html;
        chat.innerHTML = html;
      }
      document.getElementById('status').textContent = `Slides • ${new Date().toLocaleTimeString()}`;
      return;
    }

    if (currentTab === 'actions') {
      const r = await fetch('/api/actions');
      const data = await r.json();
      const sig = JSON.stringify(data);
      if (sig !== lastContent) {
        lastContent = sig;
        renderActions(data);
      }
      document.getElementById('status').textContent = `Actions • ${new Date().toLocaleTimeString()}`;
      return;
    }

    let endpoint = '/api/chat';
    if (currentTab === 'archive') endpoint = '/api/archive';
    if (currentTab === 'proposal') endpoint = '/api/proposal';
    if (currentTab === 'demo') endpoint = '/api/demo';
    if (currentTab === 'deck') endpoint = '/api/deck';
    if (currentTab === 'recording') endpoint = '/api/recording';

    const r = await fetch(endpoint);
    const data = await r.json();
    if (data.content !== lastContent) {
      lastContent = data.content;
      if (currentTab === 'proposal' || currentTab === 'demo' || currentTab === 'deck' || currentTab === 'recording') {
        renderProposal(data.content);
      } else {
        renderChat(data.content);
      }
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
    const r = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });
    const data = await r.json();
    if (!data.ok) {
      alert("Upload failed: " + (data.error || "unknown error"));
      return;
    }
    applyDeliveryStatus(data);
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
  applyDeliveryStatus(data);
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

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
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

fetch('/api/tmux').then(r => r.json()).then(data => {
  const el = document.getElementById('tmux-info');
  const paneStr = Object.entries(data.panes || {}).map(([p, name]) => `${name}:${p}`).join(' | ');
  el.textContent = `tmux ${data.target} [ ${paneStr} ]`;
});

setInterval(refresh, 2000);
refresh();
</script>
</body>
</html>"""


class ChatHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML.encode())
        elif self.path == "/api/chat":
            self._serve_file(CHATROOM)
        elif self.path == "/api/archive":
            self._serve_file(ARCHIVE)
        elif self.path == "/api/proposal":
            self._serve_file(PROPOSAL)
        elif self.path == "/api/demo":
            self._serve_file(DEMO)
        elif self.path == "/api/deck":
            self._serve_file(DECK)
        elif self.path == "/slides":
            self._serve_static(PRESENTATION_HTML)
        elif self.path == "/api/recording":
            self._serve_file(RECORDING)
        elif self.path == "/api/actions":
            try:
                with open(ACTIONS, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = {"items": []}
            self._send_json(data)
        elif self.path == "/api/agents":
            conf = _read_team_conf()
            agents = [v for k, v in sorted(conf.items()) if k.startswith("AGENT_")]
            self._send_json({"agents": agents})
        elif self.path == "/api/tmux":
            conf = _read_team_conf()
            target = conf.get("TMUX_TARGET", "unknown")
            panes = {}
            for k, v in sorted(conf.items()):
                if k.startswith("PANE_") and not k.startswith("PANE_LIST"):
                    agent_key = "AGENT_" + k[5:]
                    agent_name = conf.get(agent_key, k[5:])
                    panes[v] = agent_name
            self._send_json({"target": target, "panes": panes})
        elif self.path == "/raw/devpost_story.md":
            story_path = os.path.join(SCRIPT_DIR, "devpost_story.md")
            try:
                with open(story_path, "r") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode())
            except FileNotFoundError:
                self.send_error(404)
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
        elif self.path == "/api/actions/toggle":
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length <= 0 or length > MAX_JSON_BYTES:
                self._send_json({"ok": False, "error": "Invalid request"}, 400)
                return
            try:
                body = json.loads(self.rfile.read(length))
            except json.JSONDecodeError:
                self._send_json({"ok": False, "error": "Invalid JSON"}, 400)
                return
            item_id = str(body.get("id", ""))
            try:
                with open(ACTIONS, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = {"items": []}
            for item in data.get("items", []):
                if item.get("id") == item_id:
                    item["done"] = not item.get("done", False)
                    break
            with open(ACTIONS, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._send_json({"ok": True})
        elif self.path == "/api/upload":
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
                name = name.decode("utf-8")
            if isinstance(message, bytes):
                message = message.decode("utf-8")

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
            with open(filepath, "wb") as f:
                f.write(image_data)

            image_markup = f"![screenshot](uploads/{filename})"
            combined_message = image_markup if not message else f"{message} {image_markup}"
            self._process_message(name, combined_message)
        else:
            self.send_error(404)

    def _process_message(self, name, message):
        error = None
        delivered_targets = []
        failed_targets = []
        # Pass our own TMUX environment to the scripts so they can detect our location.
        env = os.environ.copy()
        if message:
            res = subprocess.run([CHAT_SCRIPT, name, message], capture_output=True, text=True, env=env)
            if res.returncode != 0:
                error = f"Chat script failed: {res.stderr}"

            if not error and name == "User":
                conf = _read_team_conf()
                panes = self._pane_list(conf)
                for pane in panes:
                    target = self._format_target(conf, pane)
                    res = subprocess.run(
                        [SEND_SCRIPT, "--no-log", "--from", name, pane, message],
                        capture_output=True,
                        text=True,
                        env=env,
                    )
                    if res.returncode == 0:
                        delivered_targets.append(target)
                    else:
                        detail = res.stderr.strip() or res.stdout.strip()
                        failed_targets.append({"target": target, "error": detail})

        if error:
            self._send_json({"ok": False, "error": error}, 500)
        elif failed_targets:
            self._send_json(
                {
                    "ok": True,
                    "partial": True,
                    "delivered_targets": delivered_targets,
                    "failed_targets": failed_targets,
                },
                200,
            )
        else:
            payload = {"ok": True}
            if delivered_targets:
                payload["delivered_targets"] = delivered_targets
            self._send_json(payload, 200)

    def _pane_list(self, conf):
        pane_list = conf.get("PANE_LIST", "").strip()
        if pane_list:
            return pane_list.split()
        return [v for k, v in sorted(conf.items()) if k.startswith("PANE_")]

    def _format_target(self, conf, pane):
        tmux_target = conf.get("TMUX_TARGET", "?")
        return f"{tmux_target}.{pane}"

    def _serve_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = "(empty)"
        self._send_json({"content": content})

    def _serve_static(self, path):
        if not os.path.exists(path):
            self.send_error(404)
            return

        ext = os.path.splitext(path)[1].lower()
        mime = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
        }.get(ext, "application/octet-stream")

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.end_headers()
        with open(path, "rb") as f:
            self.wfile.write(f.read())

    def _send_json(self, payload, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())


if __name__ == "__main__":
    server = http.server.HTTPServer((BIND_ADDR, PORT), ChatHandler)
    print(f"Team Chat running at http://{BIND_ADDR}:{PORT}")
    server.serve_forever()
