/**
 * KontentPyper — Dashboard Application Logic
 * Handles auth, navigation, data loading, and studio interactions.
 */

'use strict';

// ── Config ────────────────────────────────────────────────────────
const API    = '/api/v1';
const token  = localStorage.getItem('kp_token');

// Guard: redirect to login if unauthenticated
if (!token) window.location.replace('/dashboard/login');

// ── State ─────────────────────────────────────────────────────────
let currentUser     = null;
let enhancedContent = {};

function toggleSidebar() {
  if (window.innerWidth <= 960) {
    // Mobile mode
    document.body.classList.toggle('sidebar-open');
  } else {
    // Desktop mode
    document.body.classList.toggle('sidebar-collapsed');
  }
}

const PLATFORMS = [
  { id: 'twitter',  name: 'Twitter/X',  emoji: '🐦', color: '#1DA1F2' },
  { id: 'linkedin', name: 'LinkedIn',   emoji: '💼', color: '#0A66C2' },
  { id: 'youtube',  name: 'YouTube',    emoji: '▶',  color: '#FF0000' },
  { id: 'tiktok',   name: 'TikTok',     emoji: '♪',  color: '#69C9D0' },
];

const PAGE_TITLES = {
  overview:    'Overview',
  studio:      'Studio',
  connections: 'Connections',
  schedule:    'Schedule',
  campaigns:   'Campaigns',
  analytics:   'Analytics',
  posts:       'Post History',
};

// ── Helpers ───────────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  return fetch(`${API}${path}`, {
    ...opts,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type':  'application/json',
      ...(opts.headers || {}),
    },
  });
}

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// ── Toast ─────────────────────────────────────────────────────────
const toastStack = document.getElementById('toastStack');

function toast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  toastStack.appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

// ── Navigation ────────────────────────────────────────────────────
function navigate(pageId) {
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.page === pageId);
  });
  document.querySelectorAll('.page').forEach(p => {
    p.classList.toggle('active', p.id === `page-${pageId}`);
  });
  document.getElementById('topbarTitle').textContent = PAGE_TITLES[pageId] ?? pageId;

  // Auto-close sidebar on mobile
  if (window.innerWidth <= 960) {
    document.body.classList.remove('sidebar-open');
  }

  if (pageId === 'posts')       loadPostHistory();
  if (pageId === 'connections') renderPlatforms();
  if (pageId === 'analytics')   loadAnalytics();
}

// ── Auth & user ───────────────────────────────────────────────────
function logout() {
  localStorage.removeItem('kp_token');
  window.location.replace('/dashboard/login');
}

function renderUser(user) {
  document.getElementById('userName').textContent   = user.username;
  document.getElementById('userPlan').textContent   = user.plan.toUpperCase();
  document.getElementById('userInitials').textContent = user.username.slice(0, 2).toUpperCase();
}

// ── Boot ──────────────────────────────────────────────────────────
(async function boot() {
  try {
    const res = await apiFetch('/auth/me');
    if (!res.ok) { logout(); return; }
    currentUser = await res.json();
    renderUser(currentUser);
    loadOverview();
    renderPlatformToggles();
  } catch { logout(); }
})();

// ── Overview ──────────────────────────────────────────────────────
async function loadOverview() {
  // User-derived stats
  const used      = currentUser.posts_used  ?? 0;
  const limit     = currentUser.posts_limit ?? 10;
  const remaining = limit - used;

  document.getElementById('stat-posts').textContent     = used;
  document.getElementById('stat-remaining').textContent = remaining;
  document.getElementById('stat-plan').textContent      = `ON ${currentUser.plan.toUpperCase()} PLAN`;

  // Connections count
  try {
    const r = await apiFetch('/social/connections');
    if (r.ok) {
      const data = await r.json();
      document.getElementById('stat-platforms').textContent = data.length;
    }
  } catch { /* leave as - */ }

  renderBarChart();
  loadRecentPosts();
}

// Simple deterministic bar chart from a fixed seed
function renderBarChart() {
  const wrap = document.getElementById('chartBars');
  if (!wrap) return;
  // Simulated engagement values (replaced with real data in Phase 8)
  const vals = [38, 62, 44, 79, 55, 91, 48, 73, 87, 61, 95, 68];
  wrap.innerHTML = vals.map((h, i) =>
    `<div class="chart-bar" style="height:${h}%; animation-delay:${i * 0.04}s;"></div>`
  ).join('');
}

// ── Post feed helpers ─────────────────────────────────────────────
function buildPostCard(post) {
  const pl   = PLATFORMS.find(p => (post.platform ?? '').toLowerCase().includes(p.id));
  const icon = pl ? pl.emoji : '🌐';
  const clr  = pl ? pl.color : '#64748b';
  const st   = post.status === 'published' ? 'pub' : post.status === 'scheduled' ? 'sched' : 'fail';
  const lbl  = { pub:'PUBLISHED', sched:'SCHEDULED', fail:'FAILED' }[st];
  const when = post.created_at ? new Date(post.created_at).toLocaleDateString() : '';

  return `
    <div class="feed-item">
      <div class="feed-dot" style="background:${clr};"></div>
      <div class="feed-body">
        <div class="feed-text trunc">${esc(post.original_content ?? '')}</div>
        <div class="feed-meta">${pl?.name ?? post.platform ?? 'Unknown'} &nbsp;·&nbsp; ${when}</div>
      </div>
      <span class="feed-badge badge-${st}">${lbl}</span>
    </div>`;
}

async function loadRecentPosts() {
  const el = document.getElementById('recentFeed');
  try {
    const r = await apiFetch('/social/posts?limit=6');
    if (!r.ok) { el.innerHTML = `<div class="empty-state">No posts yet</div>`; return; }
    const posts = await r.json();
    el.innerHTML = posts.length
      ? posts.map(buildPostCard).join('')
      : `<div class="empty-state">No posts yet — head to the Studio</div>`;
  } catch {
    el.innerHTML = `<div class="empty-state">Could not load posts</div>`;
  }
}

async function loadPostHistory() {
  const el = document.getElementById('postHistoryFeed');
  if (!el) return;
  try {
    const r = await apiFetch('/social/posts?limit=50');
    if (!r.ok) { el.innerHTML = `<div class="empty-state">No posts yet</div>`; return; }
    const posts = await r.json();
    el.innerHTML = posts.length
      ? posts.map(buildPostCard).join('')
      : `<div class="empty-state">No posts yet</div>`;
  } catch {
    el.innerHTML = `<div class="empty-state">Could not load history</div>`;
  }
}

// ── Platform connections ──────────────────────────────────────────
async function renderPlatforms() {
  const grid = document.getElementById('platformsGrid');
  if (!grid) return;

  let connected = [];
  try {
    const r = await apiFetch('/social/connections');
    if (r.ok) connected = (await r.json()).map(c => c.platform?.toLowerCase() ?? '');
  } catch {}

  document.getElementById('stat-platforms').textContent = connected.length;

  grid.innerHTML = PLATFORMS.map(p => {
    const isOn = connected.some(c => c.includes(p.id));
    return `
      <div class="platform-tile ${isOn ? 'connected' : ''}" onclick="connectPlatform('${p.id}')">
        <div class="pt-icon">${p.emoji}</div>
        <div class="pt-name">${p.name}</div>
        <div class="pt-state ${isOn ? 'on' : ''}">${isOn ? '● CONNECTED' : '○ NOT CONNECTED'}</div>
      </div>`;
  }).join('');
}

async function connectPlatform(pid) {
  try {
    const r = await apiFetch(`/social/oauth/initiate/${pid}`);
    if (r.ok) {
      const data = await r.json();
      // Open OAuth in a centered popup window
      const w = 520, h = 650;
      const left = (screen.width / 2) - (w / 2);
      const top  = (screen.height / 2) - (h / 2);
      window.open(
        data.auth_url,
        'KontentPyper OAuth',
        `width=${w},height=${h},top=${top},left=${left},toolbar=no,menubar=no,scrollbars=yes`
      );
    } else {
      toast('Could not initiate OAuth -- check API keys in .env', 'error');
    }
  } catch (e) {
    toast('Connection error: ' + e.message, 'error');
  }
}

// Listen for postMessage from the OAuth popup when it completes
window.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'oauth_callback') {
    if (event.data.status === 'connected') {
      toast(`Connected to ${event.data.platform}!`, 'success');
    } else {
      toast(`Failed to connect ${event.data.platform}`, 'error');
    }
    // Refresh the connections grid and overview stats
    renderPlatforms();
    loadOverview();
  }
});

// ── Analytics & AI Reflection ─────────────────────────────────────
async function loadAnalytics() {
  try {
    // 1. Load Summary
    const sumRes = await apiFetch('/analytics/summary');
    if (sumRes.ok) {
      const summary = await sumRes.json();
      document.getElementById('analytics-views').textContent = summary.total_views || 0;
      document.getElementById('analytics-engagements').textContent = summary.total_engagements || 0;
      document.getElementById('analytics-top-platform').textContent = summary.top_platform || 'N/A';
    }

    // 2. Load Per-Post Metrics
    const feed = document.getElementById('analyticsFeed');
    feed.innerHTML = '<div class="skeleton"></div><div class="skeleton"></div>';
    const postsRes = await apiFetch('/analytics/posts?limit=10');
    if (postsRes.ok) {
      const posts = await postsRes.json();
      if (!posts.length) {
        feed.innerHTML = '<div class="empty-state">No metrics found. Try syncing first.</div>';
      } else {
        feed.innerHTML = posts.map(p => `
          <div class="feed-item" style="flex-direction: column; align-items: flex-start;">
            <div style="font-weight: 500; margin-bottom: 6px;">${p.platform} (Post #${p.post_id})</div>
            <div style="display: flex; gap: 15px; font-size: 13px; color: var(--text-2);">
              <span>👁 ${p.views}</span>
              <span>❤ ${p.likes}</span>
              <span>💬 ${p.comments}</span>
              <span>🔄 ${p.shares}</span>
            </div>
          </div>
        `).join('');
      }
    }
  } catch (e) {
    console.error('Analytics load error', e);
  }
}

async function runReflection() {
  const btn = document.getElementById('reflectBtn');
  const resDiv = document.getElementById('reflectionResult');
  
  btn.disabled = true;
  btn.textContent = 'ANALYZING...';
  resDiv.innerHTML = '<div class="empty-state">Agent is reviewing your metrics to formulate a new strategy...</div>';
  
  try {
    const r = await apiFetch('/analytics/reflect', { method: 'POST' });
    if (!r.ok) {
      const err = await r.json();
      throw new Error(err.detail || 'Reflection failed');
    }
    
    const data = await r.json();
    
    resDiv.innerHTML = `
      <div style="margin-bottom: 16px;">
        <div style="font-size: 12px; color: var(--primary); text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">What Worked</div>
        <div style="color: var(--text-2); font-size: 14px; line-height: 1.5;">${esc(data.what_worked)}</div>
      </div>
      <div style="margin-bottom: 16px;">
        <div style="font-size: 12px; color: #ff4d4f; text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">What Failed</div>
        <div style="color: var(--text-2); font-size: 14px; line-height: 1.5;">${esc(data.what_failed)}</div>
      </div>
      <div>
        <div style="font-size: 12px; color: #52c41a; text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">New AI Rules (Saved)</div>
        <div style="padding: 10px; background: rgba(255,255,255,0.03); border-radius: 6px; font-family: monospace; font-size: 13px; color: var(--text-1);">
          ${esc(data.new_rules).replace(/\n/g, '<br>')}
        </div>
      </div>
    `;
    toast('AI strategy updated!', 'success');
  } catch(e) {
    resDiv.innerHTML = `<div class="empty-state" style="color: #ff4d4f;">${esc(e.message)}</div>`;
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '✦ RE-RUN ANALYSIS';
  }
}

// ── Studio: platform toggles ──────────────────────────────────────
function renderPlatformToggles() {
  const container = document.getElementById('platformToggles');
  if (!container) return;
  container.innerHTML = PLATFORMS.map(p =>
    `<span class="ptoggle" data-platform="${p.id}">${p.emoji} ${p.name}</span>`
  ).join('');
  container.querySelectorAll('.ptoggle').forEach(el => {
    el.addEventListener('click', () => el.classList.toggle('on'));
  });
}

function getSelectedPlatforms() {
  return [...document.querySelectorAll('.ptoggle.on')].map(e => e.dataset.platform);
}

// ── Studio: enhance ───────────────────────────────────────────────
async function enhanceContent() {
  const raw = document.getElementById('studioInput')?.value.trim();
  if (!raw) { toast('Write some content first', 'error'); return; }

  const selected = getSelectedPlatforms();
  if (!selected.length) { toast('Select at least one platform', 'error'); return; }

  const btn = document.getElementById('enhanceBtn');
  btn.disabled = true;
  btn.textContent = 'ENHANCING...';

  try {
    const r = await apiFetch('/studio/draft', {
      method: 'POST',
      body:   JSON.stringify({ content: raw, platforms: selected }),
    });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail ?? 'Enhancement failed'); }
    const data = await r.json();
    enhancedContent = data.enhanced ?? {};
    renderPreview(selected[0]);
    document.getElementById('publishBtn').disabled = false;
    toast('Content enhanced', 'success');
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '✦ ENHANCE WITH AI';
  }
}

// ── Studio: preview ───────────────────────────────────────────────
function renderPreview(activePlatform) {
  const tabs = document.getElementById('previewTabs');
  const box  = document.getElementById('previewContent');
  if (!tabs || !box) return;

  const selected = getSelectedPlatforms();
  tabs.innerHTML = selected.map(pid => {
    const p = PLATFORMS.find(x => x.id === pid);
    return `<button class="preview-tab ${pid === activePlatform ? 'active' : ''}"
             onclick="switchTab('${pid}')">${p?.emoji ?? ''} ${p?.name ?? pid}</button>`;
  }).join('');

  box.textContent = enhancedContent[activePlatform] ?? '(No output for this platform)';
}

function switchTab(pid) {
  document.querySelectorAll('.preview-tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
  const box = document.getElementById('previewContent');
  if (box) box.textContent = enhancedContent[pid] ?? '(No output for this platform)';
}

// ── Studio: publish ───────────────────────────────────────────────
async function publishContent() {
  const selected = getSelectedPlatforms();
  if (!selected.length || !Object.keys(enhancedContent).length) return;

  const btn = document.getElementById('publishBtn');
  btn.disabled = true;
  btn.textContent = 'PUBLISHING...';

  try {
    const r = await apiFetch('/studio/publish', {
      method: 'POST',
      body:   JSON.stringify({ platform_specific_content: enhancedContent, platforms: selected }),
    });
    const data = await r.json();
    if (r.ok) {
      toast(`Published to ${data.successful}/${data.total_platforms} platforms`, 'success');
      enhancedContent = {};
      document.getElementById('studioInput').value = '';
      document.getElementById('previewContent').textContent = 'Enhanced content will appear here...';
      document.getElementById('previewTabs').innerHTML = '';
      loadOverview();
    } else {
      toast(data.detail ?? 'Publish failed', 'error');
    }
  } catch (e) {
    toast('Error: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '↑ PUBLISH NOW';
  }
}

// ── Studio: agent chat ────────────────────────────────────────────
async function agentChat() {
  const input = document.getElementById('chatInput');
  const reply = document.getElementById('agentReply');
  const msg   = input?.value.trim();
  if (!msg || !reply) return;

  reply.style.display = 'block';
  reply.textContent   = 'Agent computing...';

  try {
    const r = await apiFetch('/studio/chat', {
      method: 'POST',
      body:   JSON.stringify({ message: msg, context: document.getElementById('studioInput')?.value }),
    });
    const data = await r.json();
    reply.textContent = data.reply ?? 'No response from agent.';
  } catch {
    reply.textContent = 'Agent unreachable.';
  }
}

// ── Media upload ──────────────────────────────────────────────────
function handleMediaSelect(input) {
  const file = input.files[0];
  if (!file) return;
  const prev = document.getElementById('mediaPreview');
  const url  = URL.createObjectURL(file);
  prev.innerHTML = file.type.startsWith('video/')
    ? `<video src="${url}" controls style="width:100%; border-radius:6px; max-height:150px; margin-top:10px;"></video>`
    : `<img  src="${url}" style="width:100%; border-radius:6px; max-height:150px; object-fit:cover; margin-top:10px;" alt="preview"/>`;
}

// Drop zone events
document.addEventListener('DOMContentLoaded', () => {
  const zone = document.getElementById('dropZone');
  if (zone) {
    zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', e => {
      e.preventDefault();
      zone.classList.remove('drag-over');
      const file = e.dataTransfer.files[0];
      if (file) {
        const dt = new DataTransfer();
        dt.items.add(file);
        const input = document.getElementById('mediaInput');
        input.files = dt.files;
        handleMediaSelect(input);
      }
    });
  }
});
