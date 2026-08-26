/* ============================================================
   Agent Eval Platform — Frontend Application
   Vanilla JS connecting to the FastAPI backend
   ============================================================ */

(function () {
  'use strict';

  // ── API helpers ──────────────────────────────────────────
  const API = '';

  async function api(method, path, body) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API}${path}`, opts);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    return res.json();
  }

  // ── Toast ────────────────────────────────────────────────
  const toastBox = document.getElementById('toast-container');

  function toast(msg, type = 'info') {
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    const icons = { success: '✓', error: '✕', info: 'i' };
    el.innerHTML = `<span>${icons[type] || ''}</span><span>${msg}</span>`;
    toastBox.appendChild(el);
    setTimeout(() => {
      el.style.animation = 'toastOut 0.3s var(--ease-out) forwards';
      el.addEventListener('animationend', () => el.remove());
    }, 4000);
  }

  // ── Navigation ───────────────────────────────────────────
  const navItems = document.querySelectorAll('.nav-item[data-view]');
  const viewPanels = document.querySelectorAll('.view-panel');
  const pageTitle = document.getElementById('page-title');
  const pageSub = document.getElementById('page-subtitle');

  const viewMeta = {
    dashboard:     { title: 'Dashboard',   sub: 'Overview of your agent\'s performance' },
    'test-runner': { title: 'Test Runner', sub: 'Evaluate your AI agent in 3 easy steps' },
    agents:        { title: 'Agents',      sub: 'Register and manage your external AI agents' },
    tasks:         { title: 'Test Cases',  sub: 'Create and manage benchmark questions' },
    history:       { title: 'History',     sub: 'Browse all past evaluation results' },
  };

  function switchView(name) {
    navItems.forEach(n => n.classList.toggle('active', n.dataset.view === name));
    viewPanels.forEach(p => p.classList.toggle('active', p.id === `view-${name}`));
    const meta = viewMeta[name] || {};
    pageTitle.textContent = meta.title || '';
    pageSub.textContent = meta.sub || '';

    // Close sidebar on mobile
    document.getElementById('sidebar').classList.remove('open');

    // Load data for the view
    if (name === 'dashboard') loadDashboard();
    if (name === 'agents') loadAgents();
    if (name === 'tasks') loadTasks();
    if (name === 'history') loadHistory();
  }

  navItems.forEach(n => n.addEventListener('click', () => switchView(n.dataset.view)));

  // Mobile menu
  document.getElementById('mobile-menu-btn').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('open');
  });

  // ── Dashboard ────────────────────────────────────────────
  async function loadDashboard() {
    try {
      const summary = await api('GET', '/evaluations/summary');
      document.getElementById('stat-total-evals').textContent = summary.total_evaluations;

      const acc = summary.avg_correctness;
      const accEl = document.getElementById('stat-accuracy');
      accEl.textContent = `${(acc * 100).toFixed(1)}%`;
      accEl.className = 'stat-value' + (acc >= 0.7 ? '' : acc >= 0.4 ? '' : '');

      const hall = summary.avg_hallucination_rate;
      const hallEl = document.getElementById('stat-hallucination');
      hallEl.textContent = `${(hall * 100).toFixed(1)}%`;

      const lat = summary.avg_latency_ms;
      document.getElementById('stat-latency').textContent = lat > 1000 ? `${(lat / 1000).toFixed(1)}s` : `${Math.round(lat)}ms`;
    } catch (e) {
      // Silently use defaults
    }

    // Recent evaluations
    try {
      const evals = await api('GET', '/evaluations?limit=5');
      const tasks = await api('GET', '/tasks');
      const taskMap = {};
      tasks.forEach(t => { taskMap[t.id] = t; });

      const tbody = document.getElementById('dash-recent-tbody');
      if (evals.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6"><div class="table-empty"><div class="empty-icon">📭</div>No evaluations yet. Launch the Test Runner to get started.</div></td></tr>`;
        return;
      }
      tbody.innerHTML = evals.map(e => {
        const scores = e.scores || {};
        const corr = scores.correctness ?? 0;
        const hall = scores.hallucination_rate ?? 0;
        const lat = e.latency_ms || 0;
        const pass = corr > 0.7;
        const task = taskMap[e.task_id];
        const q = task ? truncate(task.question, 50) : `Task #${e.task_id}`;
        return `<tr class="clickable-row" data-eval='${escAttr(JSON.stringify(e))}' data-task='${escAttr(JSON.stringify(task || {}))}'>
          <td>${e.id}</td>
          <td>${esc(q)}</td>
          <td>${scoreCell(corr)}</td>
          <td>${hallCell(hall)}</td>
          <td>${formatLatency(lat)}</td>
          <td>${pass ? '<span class="badge badge-pass">Pass</span>' : '<span class="badge badge-fail">Fail</span>'}</td>
        </tr>`;
      }).join('');

      tbody.querySelectorAll('.clickable-row').forEach(row => {
        row.addEventListener('click', () => openDetailModal(JSON.parse(row.dataset.eval), JSON.parse(row.dataset.task)));
      });
    } catch (e) { /* keep empty state */ }
  }

  document.getElementById('dash-launch-btn').addEventListener('click', () => switchView('test-runner'));
  document.getElementById('dash-view-all').addEventListener('click', () => switchView('history'));

  // ── Agents ───────────────────────────────────────────────
  async function loadAgents() {
    try {
      const agents = await api('GET', '/agents');
      const tbody = document.getElementById('agents-tbody');
      if (agents.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5"><div class="table-empty"><div class="empty-icon">🤖</div>No agents registered yet.</div></td></tr>`;
        return;
      }
      tbody.innerHTML = agents.map(a => `<tr>
        <td>${a.id}</td>
        <td style="color:var(--text-primary);font-weight:500;">${esc(a.name)}</td>
        <td>${esc(a.description || '—')}</td>
        <td><code style="font-size:0.78rem;color:var(--accent-hover);">${esc(truncate(a.endpoint_url, 48))}</code></td>
        <td>—</td>
      </tr>`).join('');
    } catch (e) {
      toast('Failed to load agents', 'error');
    }
  }

  document.getElementById('register-agent-btn').addEventListener('click', async () => {
    const name = document.getElementById('agent-name').value.trim();
    const url = document.getElementById('agent-url').value.trim();
    const desc = document.getElementById('agent-desc').value.trim();
    if (!name || !url) {
      toast('Agent name and endpoint URL are required.', 'error');
      return;
    }
    try {
      await api('POST', '/agents', { name, endpoint_url: url, description: desc });
      toast('Agent registered successfully!', 'success');
      document.getElementById('agent-name').value = '';
      document.getElementById('agent-url').value = '';
      document.getElementById('agent-desc').value = '';
      loadAgents();
    } catch (e) {
      toast(`Error: ${e.message}`, 'error');
    }
  });

  // ── Tasks ────────────────────────────────────────────────
  async function loadTasks() {
    try {
      const tasks = await api('GET', '/tasks');
      const tbody = document.getElementById('tasks-tbody');
      if (tasks.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5"><div class="table-empty"><div class="empty-icon">📝</div>No test cases yet. Add your first one above.</div></td></tr>`;
        return;
      }
      tbody.innerHTML = tasks.map(t => `<tr>
        <td>${t.id}</td>
        <td style="color:var(--text-primary);font-weight:500;">${esc(truncate(t.question, 60))}</td>
        <td>${esc(truncate(t.expected_answer, 60))}</td>
        <td>${(t.required_tools || []).map(tool => `<span class="badge badge-neutral">${esc(tool)}</span>`).join(' ') || '—'}</td>
        <td><button class="btn btn-danger btn-sm delete-task-btn" data-id="${t.id}">Delete</button></td>
      </tr>`).join('');

      tbody.querySelectorAll('.delete-task-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          e.stopPropagation();
          if (!confirm('Delete this test case?')) return;
          try {
            await api('DELETE', `/tasks/${btn.dataset.id}`);
            toast('Test case deleted.', 'success');
            loadTasks();
          } catch (err) {
            toast(`Error: ${err.message}`, 'error');
          }
        });
      });
    } catch (e) {
      toast('Failed to load test cases', 'error');
    }
  }

  document.getElementById('create-task-btn').addEventListener('click', async () => {
    const question = document.getElementById('task-question').value.trim();
    const answer = document.getElementById('task-answer').value.trim();
    const toolsRaw = document.getElementById('task-tools').value.trim();
    if (!question || !answer) {
      toast('Question and expected answer are required.', 'error');
      return;
    }
    const tools = toolsRaw ? toolsRaw.split(',').map(s => s.trim()).filter(Boolean) : [];
    try {
      await api('POST', '/tasks', { question, expected_answer: answer, required_tools: tools });
      toast('Test case added!', 'success');
      document.getElementById('task-question').value = '';
      document.getElementById('task-answer').value = '';
      document.getElementById('task-tools').value = '';
      loadTasks();
    } catch (e) {
      toast(`Error: ${e.message}`, 'error');
    }
  });

  // ── History ──────────────────────────────────────────────
  async function loadHistory() {
    try {
      const evals = await api('GET', '/evaluations?limit=200');
      const tasks = await api('GET', '/tasks');
      const taskMap = {};
      tasks.forEach(t => { taskMap[t.id] = t; });

      const tbody = document.getElementById('history-tbody');
      if (evals.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7"><div class="table-empty"><div class="empty-icon">📜</div>No evaluation history yet.</div></td></tr>`;
        return;
      }
      tbody.innerHTML = evals.map(e => {
        const s = e.scores || {};
        const task = taskMap[e.task_id];
        const q = task ? truncate(task.question, 40) : `Task #${e.task_id}`;
        const date = e.created_at ? new Date(e.created_at).toLocaleDateString() : '—';
        return `<tr class="clickable-row" data-eval='${escAttr(JSON.stringify(e))}' data-task='${escAttr(JSON.stringify(task || {}))}'>
          <td>${e.id}</td>
          <td>${esc(q)}</td>
          <td>${esc(truncate(e.agent_output || '', 40))}</td>
          <td>${scoreCell(s.correctness ?? 0)}</td>
          <td>${hallCell(s.hallucination_rate ?? 0)}</td>
          <td>${formatLatency(e.latency_ms || 0)}</td>
          <td>${date}</td>
        </tr>`;
      }).join('');

      tbody.querySelectorAll('.clickable-row').forEach(row => {
        row.addEventListener('click', () => openDetailModal(JSON.parse(row.dataset.eval), JSON.parse(row.dataset.task)));
      });
    } catch (e) {
      toast('Failed to load history', 'error');
    }
  }

  // ── Wizard Logic ─────────────────────────────────────────
  let wizStep = 1;
  let wizAgentType = 'builtin';    // 'builtin' | 'external'
  let wizAgentId = null;
  let wizSelectedTasks = [];
  let wizResults = [];

  function setWizStep(step) {
    wizStep = step;
    document.querySelectorAll('.wizard-step').forEach(s => {
      const n = +s.dataset.step;
      s.classList.toggle('active', n === step);
      s.classList.toggle('completed', n < step);
    });
    document.querySelectorAll('.wizard-panel').forEach((p, i) => {
      p.classList.toggle('active', i + 1 === step);
    });
  }

  // Step 1 — Agent selection
  document.querySelectorAll('.agent-option').forEach(opt => {
    opt.addEventListener('click', () => {
      document.querySelectorAll('.agent-option').forEach(o => o.classList.remove('selected'));
      opt.classList.add('selected');
      wizAgentType = opt.dataset.agent;
      const form = document.getElementById('external-agent-form');
      if (wizAgentType === 'external') {
        form.classList.remove('hidden');
        loadAgentSelect();
      } else {
        form.classList.add('hidden');
        wizAgentId = null;
      }
    });
  });

  async function loadAgentSelect() {
    try {
      const agents = await api('GET', '/agents');
      const sel = document.getElementById('ext-agent-select');
      sel.innerHTML = '<option value="">— Choose an agent —</option>' +
        agents.map(a => `<option value="${a.id}">${esc(a.name)} — ${esc(truncate(a.endpoint_url, 40))}</option>`).join('');
    } catch (e) { /* ignore */ }
  }

  document.getElementById('ext-agent-select').addEventListener('change', function () {
    wizAgentId = this.value ? +this.value : null;
    document.getElementById('test-conn-btn').disabled = !wizAgentId;
    document.getElementById('conn-status').classList.add('hidden');
  });

  document.getElementById('test-conn-btn').addEventListener('click', async () => {
    const statusEl = document.getElementById('conn-status');
    statusEl.className = 'conn-status testing';
    statusEl.textContent = 'Testing…';
    statusEl.classList.remove('hidden');
    try {
      await api('POST', '/agents/check-health', { agent_id: wizAgentId });
      statusEl.className = 'conn-status live';
      statusEl.textContent = 'Connected';
    } catch (e) {
      statusEl.className = 'conn-status failed';
      statusEl.textContent = 'Unreachable';
    }
  });

  document.getElementById('wiz-next-1').addEventListener('click', async () => {
    if (wizAgentType === 'external' && !wizAgentId) {
      toast('Please select an agent first.', 'error');
      return;
    }
    // Load tasks for step 2
    await loadWizardTasks();
    setWizStep(2);
  });

  // Step 2 — Task selection
  async function loadWizardTasks() {
    try {
      const tasks = await api('GET', '/tasks');
      const container = document.getElementById('task-check-list');
      if (tasks.length === 0) {
        container.innerHTML = `<div class="table-empty"><div class="empty-icon">—</div>No test cases found. Add some from the Test Cases page first.</div>`;
        return;
      }
      wizSelectedTasks = tasks.map(t => t.id); // default: all selected
      container.innerHTML = tasks.map(t => `
        <label class="task-check-item selected" data-id="${t.id}">
          <input type="checkbox" checked data-id="${t.id}" />
          <div>
            <div class="task-q">${esc(t.question)}</div>
            <div class="task-a">Expected: ${esc(truncate(t.expected_answer, 80))}</div>
          </div>
        </label>
      `).join('');

      container.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        cb.addEventListener('change', () => {
          const id = +cb.dataset.id;
          const item = cb.closest('.task-check-item');
          if (cb.checked) {
            wizSelectedTasks.push(id);
            item.classList.add('selected');
          } else {
            wizSelectedTasks = wizSelectedTasks.filter(x => x !== id);
            item.classList.remove('selected');
          }
        });
      });
    } catch (e) {
      toast('Failed to load test cases', 'error');
    }
  }

  document.getElementById('select-all-tasks').addEventListener('click', () => {
    const checks = document.querySelectorAll('#task-check-list input[type="checkbox"]');
    const allChecked = [...checks].every(c => c.checked);
    checks.forEach(c => {
      c.checked = !allChecked;
      c.dispatchEvent(new Event('change'));
    });
  });

  document.getElementById('wiz-prev-2').addEventListener('click', () => setWizStep(1));

  document.getElementById('wiz-next-2').addEventListener('click', async () => {
    if (wizSelectedTasks.length === 0) {
      toast('Select at least one test case.', 'error');
      return;
    }
    setWizStep(3);
    document.getElementById('wiz-running').classList.remove('hidden');
    document.getElementById('wiz-results').classList.add('hidden');

    try {
      const body = wizAgentType === 'external' ? { agent_id: wizAgentId } : {};
      const data = await api('POST', '/evaluations/run', body);
      wizResults = data.results || [];
      renderWizResults();
    } catch (e) {
      toast(`Evaluation failed: ${e.message}`, 'error');
      document.getElementById('wiz-running').innerHTML = `
        <div class="run-progress-wrap">
          <div style="font-size:2rem;margin-bottom:16px;font-weight:bold;color:var(--danger);">✕</div>
          <div class="run-text">Evaluation Failed</div>
          <div class="run-sub">${esc(e.message)}</div>
          <button class="btn btn-secondary mt-24" onclick="document.getElementById('wiz-restart').click()">← Try Again</button>
        </div>`;
    }
  });

  function renderWizResults() {
    document.getElementById('wiz-running').classList.add('hidden');
    document.getElementById('wiz-results').classList.remove('hidden');

    // Summary cards
    const total = wizResults.length;
    const avgCorr = wizResults.reduce((s, r) => s + (r.scores?.correctness ?? 0), 0) / (total || 1);
    const avgHall = wizResults.reduce((s, r) => s + (r.scores?.hallucination_rate ?? 0), 0) / (total || 1);
    const avgLat = wizResults.reduce((s, r) => s + (r.scores?.latency_ms ?? 0), 0) / (total || 1);
    const passed = wizResults.filter(r => (r.scores?.correctness ?? 0) > 0.7).length;

    const summaryEl = document.getElementById('result-summary-grid');
    summaryEl.innerHTML = `
      <div class="result-stat">
        <div class="rs-value">${total}</div>
        <div class="rs-label">Tests Run</div>
      </div>
      <div class="result-stat">
        <div class="rs-value good">${passed}/${total}</div>
        <div class="rs-label">Passed</div>
      </div>
      <div class="result-stat">
        <div class="rs-value ${avgCorr >= 0.7 ? 'good' : avgCorr >= 0.4 ? 'warn' : 'bad'}">${(avgCorr * 100).toFixed(1)}%</div>
        <div class="rs-label">Avg Accuracy</div>
      </div>
      <div class="result-stat">
        <div class="rs-value ${avgHall <= 0.2 ? 'good' : avgHall <= 0.5 ? 'warn' : 'bad'}">${(avgHall * 100).toFixed(1)}%</div>
        <div class="rs-label">Hallucination</div>
      </div>
      <div class="result-stat">
        <div class="rs-value">${formatLatency(avgLat)}</div>
        <div class="rs-label">Avg Speed</div>
      </div>
    `;

    // Results table
    const tbody = document.getElementById('results-tbody');
    tbody.innerHTML = wizResults.map(r => {
      const s = r.scores || {};
      const corr = s.correctness ?? 0;
      const hall = s.hallucination_rate ?? 0;
      const lat = s.latency_ms ?? 0;
      const pass = corr > 0.7;
      return `<tr class="clickable-row" data-result='${escAttr(JSON.stringify(r))}'>
        <td style="color:var(--text-primary);font-weight:500;">${esc(truncate(r.question || '', 45))}</td>
        <td>${esc(truncate(r.agent_output || '', 45))}</td>
        <td>${scoreCell(corr)}</td>
        <td>${hallCell(hall)}</td>
        <td>${formatLatency(lat)}</td>
        <td>${pass ? '<span class="badge badge-pass">Pass</span>' : '<span class="badge badge-fail">Fail</span>'}</td>
      </tr>`;
    }).join('');

    tbody.querySelectorAll('.clickable-row').forEach(row => {
      row.addEventListener('click', () => {
        const r = JSON.parse(row.dataset.result);
        openDetailModal({
          agent_output: r.agent_output,
          scores: r.scores,
          latency_ms: r.scores?.latency_ms,
          token_count: r.metrics?.total_tokens,
        }, {
          question: r.question,
          expected_answer: '', // Not available directly — could be fetched
        });
      });
    });
  }

  document.getElementById('wiz-restart').addEventListener('click', () => {
    // Reset running state HTML in case of prior error
    document.getElementById('wiz-running').innerHTML = `
      <div class="run-progress-wrap">
        <div class="spinner-ring"></div>
        <div class="run-text">Evaluating your agent…</div>
        <div class="run-sub">This may take a moment — your agent is answering questions and we're scoring each response.</div>
      </div>`;
    setWizStep(1);
  });

  document.getElementById('wiz-go-dash').addEventListener('click', () => switchView('dashboard'));

  // ── Detail Modal ─────────────────────────────────────────
  function openDetailModal(evalData, taskData) {
    const body = document.getElementById('modal-body');
    const s = evalData.scores || {};
    const corr = s.correctness ?? 0;
    const hall = s.hallucination_rate ?? 0;
    const lat = evalData.latency_ms ?? s.latency_ms ?? 0;
    const tokens = evalData.token_count ?? s.total_tokens ?? 0;
    const rationale = s.correctness_rationale || 'No rationale available.';
    const unsupported = s.unsupported_claims || [];

    body.innerHTML = `
      <div class="detail-block">
        <div class="detail-block-title">Question</div>
        <div class="detail-block-content">${esc(taskData.question || 'N/A')}</div>
      </div>
      ${taskData.expected_answer ? `<div class="detail-block">
        <div class="detail-block-title">Expected Answer</div>
        <div class="detail-block-content">${esc(taskData.expected_answer)}</div>
      </div>` : ''}
      <div class="detail-block">
        <div class="detail-block-title">Agent's Answer</div>
        <div class="detail-block-content">${esc(evalData.agent_output || 'N/A')}</div>
      </div>
      <div class="detail-block">
        <div class="detail-block-title">Why It ${corr > 0.7 ? 'Passed' : 'Failed'}</div>
        <div class="detail-block-content rationale">${esc(rationale)}</div>
      </div>
      ${unsupported.length > 0 ? `<div class="detail-block">
        <div class="detail-block-title">Unsupported Claims (Hallucinations)</div>
        <div class="detail-block-content" style="color:var(--warning);">${unsupported.map(c => `• ${esc(c)}`).join('<br>')}</div>
      </div>` : ''}
      <div class="detail-block">
        <div class="detail-block-title">Performance</div>
        <div class="detail-metrics-row">
          <div class="detail-metric">
            <div class="dm-value" style="color:${corr >= 0.7 ? 'var(--success)' : 'var(--danger)'};">${(corr * 100).toFixed(1)}%</div>
            <div class="dm-label">Accuracy</div>
          </div>
          <div class="detail-metric">
            <div class="dm-value" style="color:${hall <= 0.2 ? 'var(--success)' : 'var(--warning)'};">${(hall * 100).toFixed(1)}%</div>
            <div class="dm-label">Hallucination</div>
          </div>
          <div class="detail-metric">
            <div class="dm-value">${formatLatency(lat)}</div>
            <div class="dm-label">Speed</div>
          </div>
          <div class="detail-metric">
            <div class="dm-value">${tokens}</div>
            <div class="dm-label">Tokens</div>
          </div>
        </div>
      </div>
    `;

    document.getElementById('modal-title').textContent = corr > 0.7 ? 'Test Passed' : 'Test Failed';
    document.getElementById('detail-modal').classList.add('open');
  }

  document.getElementById('modal-close-btn').addEventListener('click', closeModal);
  document.getElementById('modal-close-footer').addEventListener('click', closeModal);
  document.getElementById('detail-modal').addEventListener('click', (e) => {
    if (e.target.id === 'detail-modal') closeModal();
  });

  function closeModal() {
    document.getElementById('detail-modal').classList.remove('open');
  }

  // ── Helpers ──────────────────────────────────────────────
  function esc(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  function escAttr(str) {
    return str.replace(/'/g, '&#39;').replace(/"/g, '&quot;');
  }

  function truncate(str, len) {
    if (!str) return '';
    return str.length > len ? str.slice(0, len) + '…' : str;
  }

  function formatLatency(ms) {
    if (!ms && ms !== 0) return '—';
    if (ms > 1000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.round(ms)}ms`;
  }

  function scoreCell(val) {
    const pct = (val * 100).toFixed(0);
    const cls = val >= 0.7 ? 'good' : val >= 0.4 ? 'warn' : 'bad';
    return `<div class="score-bar"><div class="fill ${cls}" style="width:${pct}%"></div></div><span style="font-weight:600;font-size:0.82rem;">${pct}%</span>`;
  }

  function hallCell(val) {
    const pct = (val * 100).toFixed(0);
    const cls = val <= 0.2 ? 'good' : val <= 0.5 ? 'warn' : 'bad';
    return `<span class="badge badge-${val <= 0.2 ? 'pass' : val <= 0.5 ? 'warning' : 'fail'}">${pct}%</span>`;
  }

  // ── Init ─────────────────────────────────────────────────
  loadDashboard();
})();
