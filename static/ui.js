/**
 * hermes-webui-wrap — Frontend UI Logic
 */

(function () {
  'use strict';

  const API_BASE = '';
  let currentSessionId = null;
  let sessions = [];

  // ---- DOM refs ----
  const $msgInput = document.getElementById('msg-input');
  const $btnSend = document.getElementById('btn-send');
  const $messages = document.getElementById('messages');
  const $sessionList = document.getElementById('session-list');
  const $typingIndicator = document.getElementById('typing-indicator');
  const $tokenCount = document.getElementById('token-count');
  const $modelInfo = document.getElementById('model-info');
  const $workspacePanel = document.getElementById('workspace-panel');
  const $fileTree = document.getElementById('file-tree');

  // ---- API helpers ----
  async function api(method, path, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const resp = await fetch(API_BASE + path, opts);
    if (!resp.ok) throw new Error(`API error ${resp.status}: ${await resp.text()}`);
    return resp.json();
  }

  async function apiStream(method, path, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const resp = await fetch(API_BASE + path, opts);
    if (!resp.ok) throw new Error(`API error ${resp.status}`);
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let done = false;
    while (!done) {
      const { value, done: d } = await reader.read();
      done = d;
      if (value) {
        const text = decoder.decode(value, { stream: !done });
        const lines = text.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.token && data.token !== '[DONE]') yield data.token;
            } catch (_) {}
          }
        }
      }
    }
  }

  // ---- Session management ----
  async function loadSessions() {
    try {
      const data = await api('GET', '/api/sessions');
      sessions = data.sessions || [];
      renderSessionList();
    } catch (e) {
      console.error('Failed to load sessions:', e);
    }
  }

  function renderSessionList() {
    $sessionList.innerHTML = '';
    sessions.forEach(s => {
      const el = document.createElement('div');
      el.className = 'session-item' + (s.id === currentSessionId ? ' active' : '');
      el.textContent = s.title || 'Untitled';
      el.addEventListener('click', () => selectSession(s.id));
      $sessionList.appendChild(el);
    });
  }

  async function selectSession(id) {
    currentSessionId = id;
    renderSessionList();
    await loadMessages(id);
  }

  async function loadMessages(sessionId) {
    try {
      const data = await api('GET', `/api/sessions/${sessionId}`);
      $messages.innerHTML = '';
      (data.messages || []).forEach(m => appendMessage(m.role, m.content));
    } catch (e) {
      console.error('Failed to load messages:', e);
    }
  }

  async function createNewSession() {
    try {
      const data = await api('POST', '/api/sessions', { title: 'New Chat' });
      sessions.unshift(data);
      renderSessionList();
      await selectSession(data.id);
    } catch (e) {
      console.error('Failed to create session:', e);
    }
  }

  // ---- Message rendering ----
  function appendMessage(role, content) {
    const el = document.createElement('div');
    el.className = `msg ${role}`;
    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.textContent = content;
    const time = document.createElement('div');
    time.className = 'msg-time';
    time.textContent = new Date().toLocaleTimeString();
    el.appendChild(bubble);
    el.appendChild(time);
    $messages.appendChild(el);
    $messages.scrollTop = $messages.scrollHeight;
    return el;
  }

  function appendStreamingMessage(role) {
    const el = document.createElement('div');
    el.className = `msg ${role}`;
    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    const time = document.createElement('div');
    time.className = 'msg-time';
    time.textContent = new Date().toLocaleTimeString();
    el.appendChild(bubble);
    el.appendChild(time);
    $messages.appendChild(el);
    return bubble;
  }

  // ---- Send message ----
  async function sendMessage(text) {
    if (!text.trim()) return;
    if (!currentSessionId) await createNewSession();

    const sessionId = currentSessionId;
    appendMessage('user', text);
    $msgInput.value = '';
    $typingIndicator.classList.remove('hidden');

    try {
      const bubble = appendStreamingMessage('assistant');
      let response = '';

      for await (const token of apiStream('POST', '/api/chat', {
        message: text,
        session_id: sessionId
      })) {
        bubble.textContent += token;
        response += token;
        $messages.scrollTop = $messages.scrollHeight;
      }

      // Update token count (rough estimate)
      const tokens = Math.ceil((text.length + response.length) / 4);
      $tokenCount.textContent = `Tokens: ~${tokens}`;

    } catch (e) {
      console.error('Send error:', e);
      appendMessage('assistant', `Error: ${e.message}`);
    } finally {
      $typingIndicator.classList.add('hidden');
    }
  }

  // ---- Workspace ----
  async function loadWorkspace(path = '/') {
    try {
      const data = await api('GET', `/api/workspace/ls?path=${encodeURIComponent(path)}`);
      $fileTree.innerHTML = '';
      (data.files || []).forEach(f => {
        const el = document.createElement('div');
        el.className = 'file-item' + (f.is_dir ? ' dir' : '');
        el.dataset.icon = f.is_dir ? '📁' : '📄';
        el.textContent = f.name;
        if (f.is_dir) {
          el.addEventListener('dblclick', () => loadWorkspace(f.path));
        }
        $fileTree.appendChild(el);
      });
    } catch (e) {
      console.error('Workspace error:', e);
    }
  }

  // ---- Toolbar commands ----
  async function handleCommand(cmd) {
    const parts = cmd.trim().split(' ');
    const command = parts[0].toLowerCase();
    const arg = parts.slice(1).join(' ');

    switch (command) {
      case '/help':
        appendMessage('assistant', 'Available commands:\n/help — this help\n/clear — clear chat\n/mode <name> — switch model\n/workspace — toggle workspace panel');
        break;
      case '/clear':
        $messages.innerHTML = '';
        break;
      case '/mode':
        $modelInfo.textContent = `Model: ${arg || '(current)'}`;
        break;
      case '/workspace':
        $workspacePanel.classList.toggle('hidden');
        if (!$workspacePanel.classList.contains('hidden')) loadWorkspace();
        break;
      default:
        appendMessage('assistant', `Unknown command: ${command}`);
    }
  }

  // ---- Event listeners ----
  $btnSend.addEventListener('click', () => {
    const text = $msgInput.value;
    if (text.startsWith('/')) {
      handleCommand(text);
      $msgInput.value = '';
      return;
    }
    sendMessage(text);
  });

  $msgInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      $btnSend.click();
    }
  });

  document.getElementById('btn-new-chat').addEventListener('click', createNewSession);
  document.getElementById('btn-close-workspace').addEventListener('click', () => {
    $workspacePanel.classList.add('hidden');
  });

  document.querySelectorAll('.tool-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const cmd = btn.dataset.cmd;
      if (cmd) {
        handleCommand('/' + cmd);
      }
    });
  });

  // Auto-resize textarea
  $msgInput.addEventListener('input', () => {
    $msgInput.style.height = 'auto';
    $msgInput.style.height = Math.min($msgInput.scrollHeight, 200) + 'px';
  });

  // ---- Init ----
  async function init() {
    try {
      const health = await api('GET', '/health');
      $modelInfo.textContent = `Wrap: ${health.wrap} v${health.version}`;
    } catch (e) {
      console.warn('Health check failed:', e);
    }

    await loadSessions();
    if (sessions.length > 0) {
      await selectSession(sessions[0].id);
    } else {
      await createNewSession();
    }
  }

  init();
})();