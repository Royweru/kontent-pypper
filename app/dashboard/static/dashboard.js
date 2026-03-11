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
let PLATFORM_RULES  = null;

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
  news:        'News Feed',
  analytics:   'Analytics',
  posts:       'Post History',
  settings:    'Settings',
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
  if (pageId === 'news')        loadNewsFeed();
  if (pageId === 'connections') renderPlatforms();
  if (pageId === 'analytics')   loadAnalytics();
  if (pageId === 'settings')    loadTelegramSettings();
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
    
    // Fetch Platform Rules
    const rulesRes = await apiFetch('/studio/rules');
    if (rulesRes.ok) {
      PLATFORM_RULES = await rulesRes.json();
    }
    
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

  if (used === 0) {
    document.getElementById('stat-posts').innerHTML = `<span style="color:var(--text-muted); font-size:24px;">0</span>`;
    document.getElementById('stat-plan').innerHTML  = `<a href="#" onclick="openStudioModal()" style="color:var(--accent);text-decoration:none;font-weight:500;">Create first post →</a>`;
    document.getElementById('stat-remaining').textContent = remaining;
  } else {
    document.getElementById('stat-posts').textContent     = used;
    document.getElementById('stat-remaining').textContent = remaining;
    document.getElementById('stat-plan').textContent      = `ON ${currentUser.plan.toUpperCase()} PLAN`;
  }

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

// Deterministic bar chart with X-axis labels
function renderBarChart() {
  const wrap = document.getElementById('chartBars');
  if (!wrap) return;
  // Simulated engagement values (replaced with real data in Phase 8)
  const vals = [38, 62, 44, 79, 55, 91, 48, 73, 87, 61, 95, 68];
  
  let barsHtml = vals.map((h, i) => 
    `<div class="chart-bar" style="height:${h}%; animation-delay:${i * 0.04}s;" title="${h * 12} Engagements"></div>`
  ).join('');
  
  let labelsHtml = vals.map((_, i) => 
    `<div style="flex:1; font-size:9.5px; color:var(--text-muted); font-family:var(--font-mono); text-align:center;">W${i+1}</div>`
  ).join('');
  
  wrap.innerHTML = `
    <div style="display:flex; width:100%; align-items:flex-end; justify-content:space-between; height:110px; padding-bottom:8px;">
      ${barsHtml}
    </div>
    <div style="display:flex; width:100%; justify-content:space-between; border-top:1px solid var(--border-hi); padding-top:8px;">
      ${labelsHtml}
    </div>
  `;
}

// ── Posts Carousel & History ────────────────────────────────────────

function buildCarouselCard(post) {
  const plIcons = post.platforms.map(pid => {
    const pl = PLATFORMS.find(p => pid.toLowerCase().includes(p.id));
    return pl ? `<div class="carousel-platform-icon" style="color:${pl.color};">${pl.emoji}</div>` : '';
  }).join('');
  
  const when = post.created_at ? new Date(post.created_at).toLocaleDateString() : '';
  const overallStatus = post.status.toLowerCase();
  
  // Try to find a media preview
  let mediaPreview = '';
  if (post.image_urls) {
    const urls = post.image_urls.split(',');
    mediaPreview = `<img src="${urls[0]}" class="carousel-card-media-preview" alt="preview">`;
  } else if (post.video_urls) {
    const urls = post.video_urls.split(',');
    mediaPreview = `<video src="${urls[0]}" class="carousel-card-media-preview"></video>`;
  }

  return `
    <div class="carousel-card" onclick="openPostDetails(${post.id})">
      <div class="carousel-card-header">
        <div class="carousel-card-platforms">${plIcons || '<div class="carousel-platform-icon">🌐</div>'}</div>
        <div class="carousel-card-date">${when}</div>
      </div>
      ${mediaPreview}
      <div class="carousel-card-body">
        ${esc(post.original_content ?? '')}
      </div>
      <div class="carousel-card-footer">
        <span class="carousel-status-badge ${overallStatus}">${overallStatus}</span>
        <span style="font-size:16px; color:var(--text-muted);">→</span>
      </div>
    </div>
  `;
}

async function loadRecentPosts() {
  const cCont = document.getElementById('postsCarousel');
  if (!cCont) return;
  try {
    const r = await apiFetch('/posts?limit=10');
    if (!r.ok) throw new Error('API issue');
    const posts = await r.json();
    const badgeText = document.getElementById('postCountBadgeText');
    if (badgeText) badgeText.textContent = posts.length + ' POSTS';

    if (!posts.length) {
      cCont.innerHTML = `<div class="empty-state" style="width:100%; border:1px solid var(--border-med); border-radius:12px; padding:40px; background:var(--surface2);">
        <div style="font-size:32px; margin-bottom:16px; opacity:0.5;">✦</div>
        <div style="color:var(--text); font-weight:500; margin-bottom:8px; font-size:16px; letter-spacing:-0.01em;">No Pipeline Activity Yet</div>
        <div style="font-size:13px; color:var(--text-muted); margin-bottom:24px;">Your recent scheduled or published posts will appear here.</div>
        <button class="btn-secondary" onclick="openStudioModal()">Create First Post</button>
      </div>`;
      return;
    }
    cCont.innerHTML = posts.map(buildCarouselCard).join('');
  } catch (e) {
    cCont.innerHTML = `<div class="empty-state" style="width:100%;">Could not load posts: ${e.message}</div>`;
  }
}

async function loadPostHistory() {
  const el = document.getElementById('postHistoryFeed');
  if (!el) return;
  try {
    const r = await apiFetch('/posts?limit=50');
    if (!r.ok) { el.innerHTML = `<div class="empty-state">No posts yet</div>`; return; }
    const posts = await r.json();
    el.innerHTML = posts.length
      ? `<div class="posts-carousel-container" style="flex-wrap:wrap; display:flex; gap:16px;">${posts.map(buildCarouselCard).join('')}</div>` // Reuse the cards but wrap them
      : `<div class="empty-state">No posts yet</div>`;
  } catch {
    el.innerHTML = `<div class="empty-state">Could not load history</div>`;
  }
}

// ── Post Details Modal ────────────────────────────────────────────
function closePostDetails() {
  const m = document.getElementById('postDetailsOverlay');
  if (m) m.classList.remove('open');
}

async function openPostDetails(id) {
  const m = document.getElementById('postDetailsOverlay');
  const b = document.getElementById('postDetailsBody');
  if (!m || !b) return;
  
  b.innerHTML = '<div class="skeleton" style="height:200px;"></div>';
  m.classList.add('open');
  
  try {
    const r = await apiFetch(`/posts/${id}`);
    if (!r.ok) throw new Error('Could not fetch post details');
    const post = await r.json();
    
    // Status badges
    const resHtml = post.results.map(res => `
      <div class="platform-result-item">
        <div style="font-weight:600; display:flex; align-items:center; gap:8px;">
          <span style="font-size:18px;">${PLATFORMS.find(p=>p.id===res.platform)?.emoji||'🌐'}</span>
          <span style="text-transform:capitalize;">${res.platform}</span>
        </div>
        <div style="display:flex; align-items:center; gap:12px;">
          ${res.platform_post_url ? `<a href="${res.platform_post_url}" target="_blank" style="color:var(--accent); font-size:13px; font-weight:600;">View Post ↗</a>` : ''}
          <span class="carousel-status-badge ${res.status.toLowerCase()}">${res.status}</span>
        </div>
        ${res.error_message ? `<div style="color:var(--danger); font-size:12px; margin-top:4px;">${esc(res.error_message)}</div>` : ''}
      </div>
    `).join('');
    
    // Analytics
    const anHtml = post.analytics.map(an => `
      <div class="meta-box">
        <h4>${an.platform} Analytics</h4>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:14px;">
          <div><span style="color:var(--text-dim);">Views</span><br><span class="mono">${an.views}</span></div>
          <div><span style="color:var(--text-dim);">Likes</span><br><span class="mono">${an.likes}</span></div>
          <div><span style="color:var(--text-dim);">Comments</span><br><span class="mono">${an.comments}</span></div>
          <div><span style="color:var(--text-dim);">Shares</span><br><span class="mono">${an.shares}</span></div>
        </div>
      </div>
    `).join('');
    
    // Media
    let mediaHtml = '';
    const imgUrls = post.image_urls ? post.image_urls.split(',') : [];
    const vidUrls = post.video_urls ? post.video_urls.split(',') : [];
    if (imgUrls.length || vidUrls.length) {
      mediaHtml = '<div class="media-gallery">';
      imgUrls.forEach(url => { if(url) mediaHtml += `<img src="${url}">` });
      vidUrls.forEach(url => { if(url) mediaHtml += `<video src="${url}" controls></video>` });
      mediaHtml += '</div>';
    }

    b.innerHTML = `
      <div>
        <h3 style="font-size:13px; text-transform:uppercase; color:var(--text-dim); margin-bottom:8px; letter-spacing:0.5px;">Original Request</h3>
        <div style="background:var(--surface2); padding:16px; border-radius:var(--radius-sm); border:1px solid var(--border); white-space:pre-wrap; font-size:15px; line-height:1.5;">${esc(post.original_content)}</div>
      </div>
      
      ${mediaHtml}
      
      <div>
        <h3 style="font-size:13px; text-transform:uppercase; color:var(--text-dim); margin-bottom:8px; letter-spacing:0.5px;">Platform Status</h3>
        ${resHtml || '<div class="muted">No platform results yet.</div>'}
      </div>
      
      ${anHtml ? `
      <div>
        <h3 style="font-size:13px; text-transform:uppercase; color:var(--text-dim); margin-bottom:8px; letter-spacing:0.5px;">Performance</h3>
        <div class="post-meta-grid">${anHtml}</div>
      </div>
      ` : ''}
    `;
    
  } catch (e) {
    b.innerHTML = `<div class="empty-state" style="color:var(--danger);">${e.message}</div>`;
  }
}

// ── News Feed ─────────────────────────────────────────────────────
async function loadNewsFeed() {
  const el = document.getElementById('newsFeedList');
  if (!el) return;
  
  el.innerHTML = '<div class="skeleton" style="height:80px; margin:4px 0;"></div><div class="skeleton" style="height:80px; margin:4px 0;"></div>';
  
  try {
    const r = await apiFetch('/news/feed?limit=25');
    if (!r.ok) throw new Error('Failed to fetch news');
    const items = await r.json();
    
    if (!items.length) {
      el.innerHTML = `<div class="empty-state">No news found. Ensure your ingestion services are running.</div>`;
      return;
    }
    
    el.innerHTML = items.map(item => {
      const srcClr  = item.source_type === 'reddit' ? '#FF4500' : '#EAB308';
      const snippet = item.snippet ? `<div style="font-size:13px; color:var(--text-2); margin-top:8px; line-height:1.5;">${esc(item.snippet)}</div>` : '';
      const safeTitle = esc(item.title).replace(/'/g, "\\'").replace(/"/g, '&quot;');
      const safeUrl   = esc(item.url).replace(/'/g, "%27");
      
      return `
        <div class="feed-item" style="flex-direction:column; align-items:flex-start; padding:16px;">
          <div style="display:flex; justify-content:space-between; width:100%; align-items:flex-start;">
            <div style="flex:1;">
              <a href="${item.url}" target="_blank" rel="noopener" style="color:var(--text); text-decoration:none; font-weight:500; font-size:15px; line-height:1.4; display:block;" class="trunc">
                ${esc(item.title)}
              </a>
              <div style="display:flex; gap:10px; font-size:12px; color:var(--text-muted); margin-top:6px; align-items:center;">
                <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:${srcClr};"></span>
                <span>${esc(item.source_name)}</span>
                <span>·</span>
                <span>Rating: ${Math.round(item.relevance_score * 10) / 10}</span>
              </div>
            </div>
            <button class="btn-ghost" style="padding:6px 12px; font-size:11px; margin-left:12px; border:1px solid var(--border);" onclick="sendNewsToStudio('${safeTitle}', '${safeUrl}')">
               ✎ Write Post
            </button>
          </div>
          ${snippet}
        </div>
      `;
    }).join('');
    
  } catch(e) {
    el.innerHTML = `<div class="empty-state">Could not load news feed: ${esc(e.message)}</div>`;
  }
}

// ── Studio Modal & State ──────────────────────────────────────────
function openStudioModal(initialText = '') {
  const modal = document.getElementById('studioModalOverlay');
  if (modal) {
    modal.classList.add('open');
    const input = document.getElementById('studioInput');
    if (input) {
      if (initialText) input.value = initialText;
      input.focus();
    }
  }
}

function closeStudioModal() {
  const modal = document.getElementById('studioModalOverlay');
  if (modal) {
    modal.classList.remove('open');
  }
  // Automatically close the AI drawer if open
  const drawer = document.getElementById('aiDrawer');
  if (drawer && drawer.classList.contains('open')) {
    drawer.classList.remove('open');
  }
}

function toggleAiDrawer() {
  const drawer = document.getElementById('aiDrawer');
  if (drawer) {
    drawer.classList.toggle('open');
  }
}

// Close AI drawer when clicking outside
document.addEventListener('mousedown', (e) => {
  const drawer = document.getElementById('aiDrawer');
  if (drawer && drawer.classList.contains('open')) {
    // Ensure we aren't clicking inside the drawer or on its toggles
    if (!drawer.contains(e.target) && !e.target.closest('.magic-wand-fab') && !e.target.closest('.ai-drawer-toggle')) {
      drawer.classList.remove('open');
    }
  }
});

function sendNewsToStudio(title, url) {
  const content = `Trending topic: ${title}\n\nSource link: ${url}\n\nPlease adapt this into a compelling post.`;
  navigate('studio'); // go to the launchpad background page
  openStudioModal(content); // open the modal overlay directly
  toast('News imported to Studio', 'success');
}

// ── Platform connections ──────────────────────────────────────────
let connectedPlatforms = null;

async function renderPlatforms() {
  const grid = document.getElementById('platformsGrid');
  if (!grid) return;

  try {
    const r = await apiFetch('/social/connections');
    if (r.ok) {
      connectedPlatforms = (await r.json()).map(c => c.platform?.toLowerCase() ?? '');
    }
  } catch {}

  document.getElementById('stat-platforms').textContent = connectedPlatforms?.length || 0;

  grid.innerHTML = PLATFORMS.map(p => {
    const isOn = (connectedPlatforms || []).some(c => c.includes(p.id));
    if (isOn) {
      return `
        <div class="platform-tile connected" style="cursor:default;">
          <div class="pt-icon">${p.emoji}</div>
          <div class="pt-name">${p.name}</div>
          <div class="pt-state on">● CONNECTED</div>
          <button class="btn-ghost" style="margin-top:10px; font-size:11px; padding:4px 8px; color:var(--danger);" onclick="disconnectPlatform('${p.id}')">Disconnect</button>
        </div>`;
    } else {
      return `
        <div class="platform-tile" onclick="connectPlatform('${p.id}')">
          <div class="pt-icon">${p.emoji}</div>
          <div class="pt-name">${p.name}</div>
          <div class="pt-state">○ NOT CONNECTED</div>
        </div>`;
    }
  }).join('');
  
  renderPlatformToggles(); // Re-render studio toggles to disable unconnected ones
}

async function disconnectPlatform(pid) {
  if (!confirm(`Are you sure you want to disconnect ${pid}?`)) return;
  try {
    const r = await apiFetch(`/social/disconnect/${pid}`, { method: 'DELETE' });
    if (r.ok) {
      toast(`Disconnected from ${pid}`, 'success');
      renderPlatforms();
      loadOverview();
    } else {
      toast('Failed to disconnect', 'error');
    }
  } catch (e) {
    toast('Error: ' + e.message, 'error');
  }
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
  
  // Automatically fetch connections if not loaded yet
  if (connectedPlatforms === null) {
    apiFetch('/social/connections')
      .then(r => r.json())
      .then(data => {
         connectedPlatforms = data.map(c => c.platform?.toLowerCase() ?? '');
         // Call again once data is here
         renderPlatformToggles();
      }).catch(e => console.error(e));
    return;
  }

  container.innerHTML = PLATFORMS.map(p => {
    const isConnected = connectedPlatforms.includes(p.id);
    const disabledClass = isConnected ? '' : 'disabled';
    const clickAttr = isConnected ? '' : 'disabled';
    
    return `<span class="ptoggle ${disabledClass}" data-platform="${p.id}" title="${isConnected ? '' : 'Connect ' + p.name + ' in Connections tab'}">${p.emoji} ${p.name}</span>`
  }).join('');
  
  container.querySelectorAll('.ptoggle').forEach(el => {
    el.addEventListener('click', () => {
      if (el.classList.contains('disabled')) {
        toast(`Please connect ${el.textContent.trim()} in the Connections tab first`, 'warning');
        return;
      }
      el.classList.toggle('on');
      // trigger validation when toggling platforms
      validateStudioPost();
      const activePlatformTab = document.querySelector('.preview-platform-tab.active');
      const activePlatform = activePlatformTab ? activePlatformTab.dataset.platform : 'twitter';
      renderPreview(activePlatform);
    });
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
    toast('Content enhanced! You can now publish or edit further.', 'success');
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '\u2726 ENHANCE WITH AI';
  }
}

// ── Studio: Real-Time Previews (Postiz Style) ───────────────────────
function bindRealTimePreview() {
  const input = document.getElementById('studioInput');
  if (input) {
    // When the user types, clear the AI enhanced state and 
    // force the preview to render their raw keystrokes in real-time.
    input.addEventListener('input', () => {
      // If they type manually, we invalidate the AI enhanced version to 
      // show them exactly what they are typing.
      enhancedContent = {};
      const activePlatformTab = document.querySelector('.preview-platform-tab.active');
      const activePlatform = activePlatformTab ? activePlatformTab.dataset.platform : 'twitter';
      renderPreview(activePlatform);
    });
  }
}

function validateStudioPost() {
  if (!PLATFORM_RULES) return true;
  const selected = getSelectedPlatforms();
  const raw = document.getElementById('studioInput')?.value.trim() || '';
  const mediaInput = document.getElementById('mediaInput');
  const hasMedia = mediaInput && mediaInput.files && mediaInput.files.length > 0;
  
  let hasVideo = false;
  let hasImage = false;
  if (hasMedia) {
      for (let i = 0; i < mediaInput.files.length; i++) {
          if (mediaInput.files[i].type.startsWith('video/')) hasVideo = true;
          if (mediaInput.files[i].type.startsWith('image/')) hasImage = true;
      }
  }
  
  let errors = [];
  
  selected.forEach(pid => {
    // Convert 'twitter' back to 'X' for rule lookup
    let ruleKey = pid.toUpperCase();
    if (ruleKey === 'TWITTER') ruleKey = 'X';
    
    const rules = PLATFORM_RULES[ruleKey];
    if (!rules) return;
    
    const content = enhancedContent[pid] !== undefined ? enhancedContent[pid] : raw;
    
    // Basic character length validation
    if (content.length > rules.max_chars) {
      errors.push(`${pid}: char limit exceeded (${content.length}/${rules.max_chars})`);
    }
    // Media requirements validation
    if (rules.requires_media && !hasMedia) {
      errors.push(`${pid}: requires at least one image or video`);
    }
    // Allowed media types
    if (hasVideo && !rules.allowed_media.includes('video')) {
      errors.push(`${pid}: does not allow video uploads`);
    }
    if (hasImage && !rules.allowed_media.includes('image')) {
      errors.push(`${pid}: does not allow image uploads`);
    }
  });
  
  // Show error summary in UI
  const errorContainer = document.getElementById('studioValidationErrors');
  const publishBtn = document.getElementById('publishBtn');
  
  if (errorContainer) {
    if (errors.length > 0) {
      errorContainer.innerHTML = errors.map(e => `<div>⚠️ ${esc(e)}</div>`).join('');
      errorContainer.style.display = 'block';
    } else {
      errorContainer.innerHTML = '';
      errorContainer.style.display = 'none';
    }
  }
  
  if (publishBtn) {
    // Also disable if no platform selected or empty content
    const noContent = !raw && Object.keys(enhancedContent).length === 0;
    publishBtn.disabled = errors.length > 0 || selected.length === 0 || noContent;
  }
  
  return errors.length === 0;
}

// Call this once on load
document.addEventListener('DOMContentLoaded', bindRealTimePreview);

function renderPreview(activePlatform) {
  const tabs = document.getElementById('previewTabs');
  const canvas = document.getElementById('previewContent');
  if (!tabs || !canvas) return;

  const selected = getSelectedPlatforms();
  
  // If no platforms are selected, show empty state
  if (!selected.length) {
    tabs.innerHTML = '';
    canvas.innerHTML = '<div style="color:var(--text-dim); font-size:13px; margin-top:40px; text-align:center;">Select a platform to see your real-time preview...</div>';
    return;
  }

  // Ensure an active platform exists in the selected list
  if (!selected.includes(activePlatform)) {
    activePlatform = selected[0];
  }

  // Render Tabs
  tabs.innerHTML = selected.map(pid => {
    const p = PLATFORMS.find(x => x.id === pid);
    return `<button class="preview-platform-tab ${pid === activePlatform ? 'active' : ''}" 
             data-platform="${pid}"
             onclick="switchTab('${pid}')">${p?.emoji ?? ''} ${p?.name ?? pid}</button>`;
  }).join('');

  // Determine what text to render: either the specific AI enhanced draft, or the raw input.
  const rawText = document.getElementById('studioInput')?.value || '';
  const textToRender = enhancedContent[activePlatform] !== undefined ? enhancedContent[activePlatform] : rawText;

  // Render the specific High-Fidelity Mock Card
  if (activePlatform === 'twitter') {
    canvas.innerHTML = buildTwitterMock(textToRender);
  } else if (activePlatform === 'linkedin') {
    canvas.innerHTML = buildLinkedInMock(textToRender);
  } else if (activePlatform === 'youtube') {
    canvas.innerHTML = buildYouTubeMock(textToRender);
  } else if (activePlatform === 'tiktok') {
    canvas.innerHTML = buildTikTokMock(textToRender);
  } else {
    // Generic fallback for others
    canvas.innerHTML = `<div class="mock-card"><div style="white-space:pre-wrap;">${esc(textToRender) || 'Start typing...'}</div></div>`;
  }
  
  // After we render, validate state
  validateStudioPost();
}

function switchTab(pid) {
  renderPreview(pid);
}

function buildTwitterMock(text) {
  const displayName = currentUser?.username || 'Creator';
  const handle = currentUser ? currentUser.email.split('@')[0] : 'creator';
  const safeText = esc(text) || 'What is happening?!';
  
  const mediaInput = document.getElementById('mediaInput');
  let mediaHtml = '';
  if (mediaInput && mediaInput.files && mediaInput.files.length > 0) {
    const fileCount = mediaInput.files.length;
    const gridCount = fileCount >= 4 ? '4+' : fileCount;
    mediaHtml = `<div class="tw-media-grid" data-count="${gridCount}">`;
    const limit = Math.min(fileCount, 4);
    for (let i = 0; i < limit; i++) {
        const file = mediaInput.files[i];
        const url = URL.createObjectURL(file);
        if (file.type.startsWith('video/')) {
            mediaHtml += `<video src="${url}" controls></video>`;
        } else {
            mediaHtml += `<img src="${url}" />`;
        }
    }
    mediaHtml += '</div>';
  }

  return `
    <div class="mock-card mock-x">
      <div class="mock-x-header">
        <div class="mock-x-avatar" style="display:flex;align-items:center;justify-content:center;background:var(--accent);color:var(--deep);font-weight:bold;">${displayName.charAt(0)}</div>
        <div style="display:flex; flex-direction:column;">
          <div style="display:flex; align-items:center; gap:4px;">
            <div class="mock-x-name">${esc(displayName)}</div>
            <svg viewBox="0 0 24 24" aria-label="Verified account" role="img" style="width:16px;height:16px;fill:#1d9bf0;"><g><path d="M22.5 12.5c0-1.58-.875-2.95-2.148-3.6.154-.435.238-.905.238-1.4 0-2.21-1.71-3.998-3.918-3.998-.47 0-.92.084-1.336.25C14.818 2.415 13.51 1.5 12 1.5s-2.816.917-3.337 2.25c-.416-.165-.866-.25-1.336-.25-2.21 0-3.918 1.792-3.918 4 0 .495.084.965.238 1.4-1.273.65-2.148 2.02-2.148 3.6 0 1.46.74 2.746 1.867 3.45-.032.22-.05.45-.05.68 0 2.21 1.71 3.998 3.918 3.998.47 0 .92-.084 1.336-.25C9.182 21.585 10.49 22.5 12 22.5s2.816-.917 3.337-2.25c.416.165.866.25 1.336.25 2.21 0 3.918-1.792 3.918-4 0-.23-.018-.46-.05-.68 1.126-.704 1.867-1.99 1.867-3.45zm-10.44 3.73l-4.226-4.225 1.414-1.414 2.81 2.81 7.026-8.192 1.536 1.228-8.56 9.794z"></path></g></svg>
          </div>
          <div class="mock-x-handle">@${esc(handle)}</div>
        </div>
      </div>
      <div class="mock-x-body">${safeText}</div>
      ${mediaHtml}
      <div style="display:flex; justify-content:space-between; color:#71767b; font-size:13px; margin-top:16px; border-top:1px solid #2f3336; padding-top:12px;">
        <span>💬 0</span>
        <span>🔁 0</span>
        <span>❤️ 0</span>
        <span>📊 0</span>
      </div>
    </div>
  `;
}

function buildLinkedInMock(text) {
  const displayName = currentUser?.username || 'Creator Professional';
  const bio = currentUser?.bio || 'Building the future of AI automation.';
  const safeText = esc(text) || 'Start a post...';
  
  let displayText = safeText;
  let isTruncated = false;
  if (displayText.length > 210) {
    displayText = displayText.substring(0, 210) + '...';
    isTruncated = true;
  }

  const mediaInput = document.getElementById('mediaInput');
  let mediaHtml = '';
  if (mediaInput && mediaInput.files && mediaInput.files.length > 0) {
    const fileCount = mediaInput.files.length;
    const gridCount = fileCount >= 4 ? '4+' : fileCount;
    mediaHtml = `<div class="li-media-grid" data-count="${gridCount}">`;
    const limit = Math.min(fileCount, 4);
    for (let i = 0; i < limit; i++) {
      const file = mediaInput.files[i];
      const url = URL.createObjectURL(file);
      if (file.type.startsWith('video/')) {
        mediaHtml += `<video src="${url}" controls></video>`;
      } else {
        mediaHtml += `<img src="${url}" />`;
      }
    }
    mediaHtml += '</div>';
  }

  return `
    <div class="mock-card mock-li">
      <div class="mock-li-header">
        <div class="mock-li-avatar" style="display:flex;align-items:center;justify-content:center;background:#fff;color:var(--deep);font-weight:bold;">${displayName.charAt(0)}</div>
        <div style="display:flex; flex-direction:column; line-height:1.2;">
          <div class="mock-li-name">${esc(displayName)}</div>
          <div class="mock-li-bio">${esc(bio).substring(0, 50)}</div>
          <div class="mock-li-bio" style="font-size:11px; margin-top:2px;">Just now • 🌐</div>
        </div>
      </div>
      <div class="mock-li-body">
        ${displayText}
        ${isTruncated ? `<span class="mock-li-truncate">see more</span>` : ''}
      </div>
      ${mediaHtml}
      <div style="border-top:1px solid #38434f; margin-top:12px; padding-top:8px; display:flex; justify-content:space-around; color:#a0a0a0; font-size:12px; font-weight:600;">
        <span>👍 Like</span>
        <span>💬 Comment</span>
        <span>🔁 Repost</span>
      </div>
    </div>
  `;
}

function buildYouTubeMock(text) {
  const displayName = currentUser?.username || 'Creator Channel';
  const safeText = esc(text) || 'Video Title goes here...';
  
  let displayTitle = safeText.split('\\n')[0];
  if(displayTitle.length > 60) displayTitle = displayTitle.substring(0, 60) + '...';

  const mediaInput = document.getElementById('mediaInput');
  let mediaHtml = '';
  if (mediaInput && mediaInput.files && mediaInput.files.length > 0) {
      const file = mediaInput.files[0];
      const url = URL.createObjectURL(file);
      if (file.type.startsWith('video/')) {
        mediaHtml = `<video src="${url}" controls preload="metadata"></video>`;
      } else {
        mediaHtml = `<img src="${url}" />`;
      }
  } else {
      mediaHtml = `<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:#666;">No Media Selected</div>`;
  }

  return `
    <div class="mock-yt">
      <div class="mock-yt-player">
        ${mediaHtml}
      </div>
      <div class="mock-yt-info">
        <div class="mock-yt-title">${displayTitle}</div>
        <div class="mock-yt-channel">
            <div class="mock-yt-avatar">${displayName.charAt(0)}</div>
            <div class="mock-yt-meta">${esc(displayName)} • 0 views • Just now</div>
        </div>
      </div>
    </div>
  `;
}

function buildTikTokMock(text) {
  const displayName = currentUser?.username || 'creator';
  const safeText = esc(text) || 'Type a caption here...';
  
  let caption = safeText;
  if (caption.length > 100) caption = caption.substring(0, 100) + '...';

  const mediaInput = document.getElementById('mediaInput');
  let mediaHtml = '';
  if (mediaInput && mediaInput.files && mediaInput.files.length > 0) {
      const file = mediaInput.files[0];
      const url = URL.createObjectURL(file);
      if (file.type.startsWith('video/')) {
        mediaHtml = `<video src="${url}" controls autoplay loop muted></video>`;
      } else {
        mediaHtml = `<img src="${url}" />`;
      }
  } else {
      mediaHtml = `<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:#666;background:#111;">No Video Selected</div>`;
  }

  return `
    <div class="mock-tt">
      <div class="mock-tt-player">
        ${mediaHtml}
      </div>
      <div class="mock-tt-overlay">
        <div class="mock-tt-info">
          <div class="mock-tt-name">@${esc(displayName)}</div>
          <div class="mock-tt-desc">${caption}</div>
          <div style="display:flex;gap:8px;font-size:13px;font-weight:600;">
            <span style="display:flex;align-items:center;gap:4px;">🎵 original sound - ${esc(displayName)}</span>
          </div>
        </div>
        <div class="mock-tt-actions">
           <div class="mock-tt-action"><div class="mock-tt-icon">❤️</div><span class="mock-tt-action-text">0</span></div>
           <div class="mock-tt-action"><div class="mock-tt-icon">💬</div><span class="mock-tt-action-text">0</span></div>
           <div class="mock-tt-action"><div class="mock-tt-icon">🔖</div><span class="mock-tt-action-text">0</span></div>
           <div class="mock-tt-action"><div class="mock-tt-icon">↗️</div><span class="mock-tt-action-text">0</span></div>
        </div>
      </div>
    </div>
  `;
}

// ── Studio: publish ───────────────────────────────────────────────
async function publishContent() {
  const selected = getSelectedPlatforms();
  if (!selected.length) { toast('Select at least one platform', 'error'); return; }

  const raw = document.getElementById('studioInput')?.value.trim();

  // Build content map: use enhanced content if available, otherwise use raw text
  let contentMap = {};
  if (Object.keys(enhancedContent).length) {
    contentMap = enhancedContent;
  } else if (raw) {
    selected.forEach(p => { contentMap[p] = raw; });
  } else {
    toast('Write some content first', 'error');
    return;
  }

  const btn = document.getElementById('publishBtn');
  btn.disabled = true;
  btn.textContent = 'PUBLISHING...';

  let imageUrls = [];
  let videoUrls = [];

  const mediaInput = document.getElementById('mediaInput');
  if (mediaInput && mediaInput.files && mediaInput.files.length > 0) {
    btn.textContent = 'UPLOADING MEDIA...';
    try {
      const formData = new FormData();
      for (let i = 0; i < mediaInput.files.length; i++) {
        formData.append('files', mediaInput.files[i]);
      }
      
      const uploadRes = await fetch(`${API}/media/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      
      if (!uploadRes.ok) {
        const err = await uploadRes.json();
        throw new Error(err.detail || 'Upload failed');
      }
      
      const uploadData = await uploadRes.json();
      uploadData.uploaded.forEach(m => {
        if (m.type === 'video') videoUrls.push(m.url);
        else imageUrls.push(m.url);
      });
    } catch(e) {
      toast('Upload error: ' + e.message, 'error');
      btn.disabled = false;
      btn.textContent = 'Publish Now';
      return;
    }
  }

  btn.textContent = 'PUBLISHING...';

  try {
    const r = await apiFetch('/studio/publish', {
      method: 'POST',
      body:   JSON.stringify({ 
        original_content: raw,
        platform_specific_content: contentMap, 
        platforms: selected,
        image_urls: imageUrls,
        video_urls: videoUrls
      }),
    });
    const data = await r.json();
    if (r.ok) {
      toast(`Published to ${data.successful}/${data.total_platforms} platforms`, 'success');
      enhancedContent = {};
      document.getElementById('studioInput').value = '';
      document.getElementById('previewContent').innerHTML = '<div style="color:var(--text-dim); text-align:center; margin-top:40px;">Type in the editor to see your real-time preview...</div>';
      
      // Clear media
      const prev = document.getElementById('mediaPreview');
      if (prev) prev.innerHTML = '';
      if (mediaInput) mediaInput.value = '';

      // Close the modal
      closeStudioModal();
      loadOverview();
    } else {
      toast(data.detail ?? 'Publish failed', 'error');
    }
  } catch (e) {
    toast('Error: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Publish Now';
  }
}

// ── Studio: agent chat ────────────────────────────────────────────
async function agentChat() {
  const input = document.getElementById('chatInput');
  const container = document.getElementById('agentReply');
  const sendBtn = input?.parentElement?.querySelector('.chat-send-btn');
  const msg = input?.value.trim();
  
  if (!msg || !container) return;

  // 1. Append User Message Bubble
  container.innerHTML += `<div class="chat-bubble user">${esc(msg)}</div>`;
  input.value = '';
  
  // Create an empty agent bubble for loading state
  const thinkingId = 'agent-thinking-' + Date.now();
  container.innerHTML += `<div class="chat-bubble agent" id="${thinkingId}"><span style="color:var(--primary); font-style:italic;">Agent is thinking...</span></div>`;
  
  // Scroll to bottom
  container.scrollTop = container.scrollHeight;

  if (sendBtn) { sendBtn.disabled = true; sendBtn.textContent = '...'; }

  // Build context from both the draft and any enhanced content
  let context = document.getElementById('studioInput')?.value || '';
  if (Object.keys(enhancedContent).length) {
    context += '\n\n--- ENHANCED VERSIONS ---\n';
    for (const [p, text] of Object.entries(enhancedContent)) {
      context += `\n[${p.toUpperCase()}]:\n${text}\n`;
    }
  }

  try {
    const r = await apiFetch('/studio/chat', {
      method: 'POST',
      body: JSON.stringify({ message: msg, context }),
    });
    const data = await r.json();
    const text = data.reply ?? 'No response from agent.';
    
    let renderedHtml = text;
    if (typeof marked !== 'undefined') {
      renderedHtml = marked.parse(text);
    } else {
      renderedHtml = `<div style="white-space:pre-wrap;">${esc(text)}</div>`;
    }
    
    // Replace thinking bubble with actual response
    const thinkingBubble = document.getElementById(thinkingId);
    if (thinkingBubble) {
      thinkingBubble.innerHTML = `<div class="agent-msg-content">${renderedHtml}</div>`;
    } else {
       container.innerHTML += `<div class="chat-bubble agent"><div class="agent-msg-content">${renderedHtml}</div></div>`;
    }
    
  } catch (err) {
    const thinkingBubble = document.getElementById(thinkingId);
    if (thinkingBubble) {
      thinkingBubble.innerHTML = `<span style="color:#ff4d4f;">Agent unreachable. Try again.</span>`;
    }
  } finally {
    if (sendBtn) { sendBtn.disabled = false; sendBtn.innerHTML = '→'; }
    container.scrollTop = container.scrollHeight;
  }
}

// ── Media upload ──────────────────────────────────────────────────
function handleMediaSelect(input) {
  const files = input.files;
  if (!files || files.length === 0) return;
  const prev = document.getElementById('mediaPreview');
  
  // Render small thumbnails in the upload zone
  let html = '';
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const url  = URL.createObjectURL(file);
    if (file.type.startsWith('video/')) {
       html += `<video src="${url}" controls style="border-radius:6px; max-height:48px; object-fit:cover;"></video>`;
    } else {
       html += `<img src="${url}" style="border-radius:6px; max-height:48px; object-fit:cover;" alt="preview"/>`;
    }
  }
  prev.innerHTML = html;
    
  // Force the Real-Time Preview panels on the right to re-render so they show the media in the mock cards
  const activePlatformTab = document.querySelector('.preview-platform-tab.active');
  const activePlatform = activePlatformTab ? activePlatformTab.dataset.platform : 'twitter';
  renderPreview(activePlatform);
  validateStudioPost();
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
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const dt = new DataTransfer();
        for (let i = 0; i < e.dataTransfer.files.length; i++) {
            dt.items.add(e.dataTransfer.files[i]);
        }
        const input = document.getElementById('mediaInput');
        input.files = dt.files;
        handleMediaSelect(input);
      }
    });
  }
});

// ── Telegram Integration ───────────────────────────────────────────────────
async function loadTelegramSettings() {
  try {
    const r = await apiFetch('/auth/settings/telegram');
    if (!r.ok) return;
    const data = await r.json();

    const statusEl = document.getElementById('tgStatus');
    const textEl   = document.getElementById('tgStatusText');
    const metaEl   = document.getElementById('tgStatusMeta');
    const detectEl = document.getElementById('tgDetectSection');

    if (data.is_linked) {
      statusEl.style.display = 'flex';
      statusEl.querySelector('.feed-dot').style.background = 'var(--accent)';
      textEl.textContent = 'Telegram linked';
      metaEl.textContent = 'Chat ID: ' + data.chat_id;
      detectEl.style.display = 'none';
    } else if (data.has_bot_token) {
      statusEl.style.display = 'flex';
      statusEl.querySelector('.feed-dot').style.background = 'var(--amber)';
      textEl.textContent = 'Bot token saved -- awaiting /start detection';
      metaEl.textContent = 'Send /start to the bot, then click Detect';
      detectEl.style.display = 'block';
    } else {
      statusEl.style.display = 'none';
      detectEl.style.display = 'none';
    }
  } catch (e) {
    console.error('Telegram settings load error', e);
  }
}

async function saveTelegramToken() {
  const input = document.getElementById('tgBotToken');
  const btn   = document.getElementById('tgSaveBtn');
  const val   = input.value.trim();

  if (!val) { toast('Enter a bot token first', 'error'); return; }

  btn.disabled = true;
  btn.textContent = 'Saving...';

  try {
    const r = await apiFetch('/auth/settings/telegram', {
      method: 'PUT',
      body: JSON.stringify({ bot_token: val }),
    });
    const data = await r.json();

    if (!r.ok) {
      toast(data.detail || 'Invalid token', 'error');
      return;
    }

    toast(data.message, 'success');
    input.value = '';

    // Show detect section
    var botNameEl = document.getElementById('tgBotName');
    if (botNameEl) botNameEl.textContent = '@' + (data.bot_username || 'yourbot');
    document.getElementById('tgDetectSection').style.display = 'block';

    loadTelegramSettings();
  } catch (e) {
    toast('Error: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Save';
  }
}

async function detectTelegramChat() {
  const btn = document.getElementById('tgDetectBtn');
  const msg = document.getElementById('tgDetectMsg');

  btn.disabled = true;
  btn.textContent = 'Detecting...';
  msg.textContent = '';

  try {
    const r = await apiFetch('/auth/settings/telegram/detect', { method: 'POST' });
    const data = await r.json();

    if (data.success) {
      toast(data.message, 'success');
      msg.textContent = '';
      loadTelegramSettings();
    } else {
      msg.textContent = data.message;
      msg.style.color = 'var(--amber)';
    }
  } catch (e) {
    msg.textContent = 'Detection failed: ' + e.message;
    msg.style.color = 'var(--danger)';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Detect Chat ID';
  }
}

// ── Automate Pipeline & Feeds UI ──────────────────────────────────
function openAutomateModal() {
  const modal = document.getElementById('automateModalOverlay');
  if (modal) modal.classList.add('open');
}
function closeAutomateModal() {
  const modal = document.getElementById('automateModalOverlay');
  if (modal) modal.classList.remove('open');
}

// ── Explore Feeds Modal (Phase 5) ─────────────────────────────────

let catalogueCache = null;          // cached catalogue API response
let activeFeedCategory = 'tech';    // active category slug
let activeSourceType   = 'rss';     // 'rss' or 'reddit'
let userFeeds = [];                 // user's saved feed sources

async function loadCatalogue() {
  if (catalogueCache) return catalogueCache;
  try {
    const r = await apiFetch('/news/catalogue');
    if (r.ok) {
      catalogueCache = await r.json();
    } else {
      catalogueCache = { categories: [], rss: [], subreddits: [] };
    }
  } catch(e) {
    catalogueCache = { categories: [], rss: [], subreddits: [] };
  }
  return catalogueCache;
}

function renderCategoryChips(catalogue) {
  const bar = document.getElementById('exploreCategoryChips');
  if (!bar) return;
  bar.innerHTML = catalogue.categories.map(c => {
    const isActive = c.slug === activeFeedCategory;
    return `<button class="explore-chip${isActive ? ' active' : ''}" onclick="switchFeedCategory('${esc(c.slug)}')">${esc(c.label)}</button>`;
  }).join('');
}

async function openExploreFeedsModal() {
  const modal = document.getElementById('exploreFeedsModalOverlay');
  if (modal) modal.classList.add('open');
  const catalogue = await loadCatalogue();
  renderCategoryChips(catalogue);
  renderExploreFeeds();
}

function closeExploreFeedsModal() {
  const modal = document.getElementById('exploreFeedsModalOverlay');
  if (modal) modal.classList.remove('open');
  closePreviewPanel();
}

function switchFeedCategory(slug) {
  activeFeedCategory = slug;
  const bar = document.getElementById('exploreCategoryChips');
  if (bar) {
    Array.from(bar.children).forEach(btn => {
      btn.classList.toggle('active', btn.textContent.trim() === (catalogueCache?.categories.find(c => c.slug === slug)?.label || ''));
    });
  }
  renderExploreFeeds();
}

function switchSourceType(type) {
  activeSourceType = type;
  document.getElementById('subTabRss')?.classList.toggle('active', type === 'rss');
  document.getElementById('subTabReddit')?.classList.toggle('active', type === 'reddit');
  renderExploreFeeds();
}

function renderExploreFeeds() {
  const grid = document.getElementById('exploreFeedsGrid');
  if (!grid || !catalogueCache) return;

  let items = [];
  if (activeSourceType === 'rss') {
    items = (catalogueCache.rss || []).filter(f => f.category === activeFeedCategory);
  } else {
    items = (catalogueCache.subreddits || []).filter(f => f.category === activeFeedCategory);
  }

  if (!items.length) {
    grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1;">No feeds in this category yet.</div>';
    return;
  }

  grid.innerHTML = items.map(f => {
    const feedUrl = f.url || '';
    const isAdded = userFeeds.some(uf => (uf.url && uf.url === feedUrl) || (uf.subreddit_name && f.subreddit && uf.subreddit_name === f.subreddit));
    const logoSrc = f.logo_url || '';
    const badgeClass = f.source_type === 'reddit' ? 'reddit' : 'rss';
    const badgeLabel = f.source_type === 'reddit' ? 'Reddit' : 'RSS';
    const previewFn = f.source_type === 'reddit'
      ? `previewSubreddit('${esc(f.subreddit || '')}')`
      : `previewFeed('${esc(feedUrl)}')`;
    const toggleFn = `toggleFeed(${JSON.stringify({
      name: f.name,
      url: feedUrl,
      source_type: f.source_type,
      logo_url: logoSrc,
      category: f.category,
      subreddit: f.subreddit || ''
    }).replace(/'/g, "\\'")})`;

    return `
      <div class="feed-card${isAdded ? ' added' : ''}">
        <div class="feed-card-head">
          ${logoSrc ? `<img class="feed-card-logo" src="${esc(logoSrc)}" alt="" onerror="this.style.display='none'">` : ''}
          <span class="feed-card-name">${esc(f.name)}</span>
        </div>
        <div class="feed-card-desc">${esc(f.description || '')}</div>
        <div class="feed-card-footer">
          <span class="source-badge ${badgeClass}">${badgeLabel}</span>
          <div style="display:flex; gap:6px;">
            <button class="btn-ghost" style="margin:0; padding:4px 10px; font-size:11px; width:auto;" onclick="${previewFn}">Preview</button>
            <button class="btn-ghost" style="margin:0; padding:4px 10px; font-size:11px; width:auto; ${isAdded ? 'border-color:var(--accent); color:var(--accent);' : ''}" 
                    onclick='${toggleFn}'>${isAdded ? 'Added' : 'Add'}</button>
          </div>
        </div>
      </div>`;
  }).join('');
}

// ── Feed CRUD (correct API paths) ─────────────────────────────────

window.toggleFeed = async function(feedObj) {
  if (typeof feedObj === 'string') feedObj = JSON.parse(feedObj);

  // Check if already added
  const existing = userFeeds.find(uf =>
    (uf.url && uf.url === feedObj.url) ||
    (uf.subreddit_name && feedObj.subreddit && uf.subreddit_name === feedObj.subreddit)
  );

  if (existing) {
    // Remove
    try {
      await apiFetch(`/news/feed/sources/${existing.id}`, { method: 'DELETE' });
      userFeeds = userFeeds.filter(f => f.id !== existing.id);
      toast(`Removed ${feedObj.name}`);
    } catch(e) {
      toast('Failed to remove feed', 'error');
    }
  } else {
    // Add - check tier limits
    const isPro = currentUser && currentUser.plan !== 'free';
    const rssCount = userFeeds.filter(f => f.source_type !== 'reddit').length;
    const redditCount = userFeeds.filter(f => f.source_type === 'reddit').length;

    if (!isPro) {
      if (feedObj.source_type === 'reddit' && redditCount >= 2) {
        toast('Free plan: max 2 subreddits. Upgrade to Pro for unlimited.', 'error');
        return;
      }
      if (feedObj.source_type !== 'reddit' && rssCount >= 5) {
        toast('Free plan: max 5 RSS feeds. Upgrade to Pro for unlimited.', 'error');
        return;
      }
    }

    const body = {
      title: feedObj.name,
      url: feedObj.url || '',
      source_type: feedObj.source_type || 'rss',
      logo_url: feedObj.logo_url || '',
      category: feedObj.category || '',
    };
    if (feedObj.subreddit) body.subreddit_name = feedObj.subreddit;

    try {
      const r = await apiFetch('/news/feed/sources', {
        method: 'POST',
        body: JSON.stringify(body)
      });
      if (r.ok) {
        const newSource = await r.json();
        userFeeds.push(newSource);
        toast(`Added ${feedObj.name}`, 'success');
      } else {
        const err = await r.json().catch(() => ({}));
        toast(err.detail || 'Failed to add feed', 'error');
      }
    } catch(e) {
      toast('Network error adding feed', 'error');
    }
  }
  renderExploreFeeds();
  renderActiveFeeds();
  updateTierBadge();
};

window.removeFeed = async function(sourceId) {
  try {
    await apiFetch(`/news/feed/sources/${sourceId}`, { method: 'DELETE' });
    userFeeds = userFeeds.filter(f => f.id !== sourceId);
    renderActiveFeeds();
    renderExploreFeeds();
    updateTierBadge();
    toast('Feed removed');
  } catch(e) {
    toast('Failed to remove', 'error');
  }
};

window.addCustomFeed = async function() {
  const input = document.getElementById('customRssUrl');
  if (!input) return;
  const url = input.value.trim();
  if (!url) return;

  const isPro = currentUser && currentUser.plan !== 'free';
  const rssCount = userFeeds.filter(f => f.source_type !== 'reddit').length;
  if (!isPro && rssCount >= 5) {
    toast('Free plan: max 5 RSS feeds. Upgrade to Pro.', 'error');
    return;
  }

  let title;
  try { title = new URL(url).hostname.replace('www.', ''); } catch(e) {
    toast('Invalid URL', 'error');
    return;
  }

  if (userFeeds.some(f => f.url === url)) {
    toast('Feed already added', 'warning');
    return;
  }

  try {
    const r = await apiFetch('/news/feed/sources', {
      method: 'POST',
      body: JSON.stringify({ title, url, source_type: 'rss' })
    });
    if (r.ok) {
      const newSource = await r.json();
      userFeeds.push(newSource);
      toast(`Added custom feed ${title}`, 'success');
      renderActiveFeeds();
      updateTierBadge();
    } else {
      const err = await r.json().catch(() => ({}));
      toast(err.detail || 'Failed to add feed', 'error');
    }
  } catch(e) {
    toast('Network error', 'error');
  }

  input.value = '';
  closeExploreFeedsModal();
};

// ── Active Feeds Grid ─────────────────────────────────────────────

function renderActiveFeeds() {
  const grid = document.getElementById('activeFeedsGrid');
  const countEl = document.getElementById('activeFeedCount');
  if (!grid) return;

  if (countEl) countEl.textContent = `(${userFeeds.length})`;

  if (!userFeeds.length) {
    grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1; padding:20px;">No feeds added yet. Click "Add Feed" to start.</div>';
    return;
  }

  grid.innerHTML = userFeeds.map(f => {
    const logo = f.logo_url || '';
    const badgeClass = f.source_type === 'reddit' ? 'reddit' : 'rss';
    const badgeLabel = f.source_type === 'reddit' ? 'Reddit' : 'RSS';
    const name = f.title || f.subreddit_name || 'Feed';
    return `
      <div class="feed-card added">
        <div class="feed-card-head">
          ${logo ? `<img class="feed-card-logo" src="${esc(logo)}" alt="" onerror="this.style.display='none'">` : ''}
          <span class="feed-card-name">${esc(name)}</span>
        </div>
        <div class="feed-card-footer">
          <div style="display:flex; gap:6px; align-items:center;">
            <span class="source-badge ${badgeClass}">${badgeLabel}</span>
            ${f.category ? `<span class="category-pill">${esc(f.category)}</span>` : ''}
          </div>
          <button class="btn-ghost" style="margin:0; padding:4px 10px; font-size:11px; width:auto; color:var(--danger);" 
                  onclick="removeFeed(${f.id})">Remove</button>
        </div>
      </div>`;
  }).join('');
}

function updateTierBadge() {
  const badge = document.getElementById('feedTierBadge');
  if (!badge) return;
  const isPro = currentUser && currentUser.plan !== 'free';
  const rssCount = userFeeds.filter(f => f.source_type !== 'reddit').length;
  const redditCount = userFeeds.filter(f => f.source_type === 'reddit').length;

  if (isPro) {
    badge.textContent = `PRO: ${rssCount} RSS / ${redditCount} Reddit`;
    badge.style.display = 'inline-block';
  } else {
    badge.textContent = `FREE: ${rssCount}/5 RSS - ${redditCount}/2 Reddit`;
    badge.style.display = 'inline-block';
  }
}

// ── Live Preview Panel ────────────────────────────────────────────

async function previewFeed(url) {
  const panel = document.getElementById('explorePreviewPanel');
  const content = document.getElementById('explorePreviewContent');
  if (!panel || !content) return;
  panel.style.display = 'flex';
  content.innerHTML = '<div class="skeleton" style="height:50px; margin:4px 0;"></div>'.repeat(3);

  try {
    const r = await apiFetch('/news/feed/preview?url=' + encodeURIComponent(url));
    if (r.ok) {
      const data = await r.json();
      const articles = data.articles || data || [];
      if (Array.isArray(articles) && articles.length) {
        content.innerHTML = articles.slice(0, 8).map(a => `
          <div class="feed-item">
            <div class="feed-dot" style="background:var(--cyan);"></div>
            <div class="feed-body">
              <div class="feed-text">${esc(a.title || 'Untitled')}</div>
              <div class="feed-meta">${a.published ? new Date(a.published).toLocaleDateString() : ''}</div>
            </div>
          </div>`).join('');
      } else {
        content.innerHTML = '<div class="empty-state">No articles found in this feed.</div>';
      }
    } else {
      content.innerHTML = '<div class="empty-state">Could not load preview.</div>';
    }
  } catch(e) {
    content.innerHTML = '<div class="empty-state">Preview failed.</div>';
  }
}

async function previewSubreddit(name) {
  const panel = document.getElementById('explorePreviewPanel');
  const content = document.getElementById('explorePreviewContent');
  if (!panel || !content) return;
  panel.style.display = 'flex';
  content.innerHTML = '<div class="skeleton" style="height:50px; margin:4px 0;"></div>'.repeat(3);

  try {
    const r = await apiFetch('/news/subreddit/preview?name=' + encodeURIComponent(name));
    if (r.ok) {
      const data = await r.json();
      const posts = data.posts || data || [];
      if (Array.isArray(posts) && posts.length) {
        content.innerHTML = posts.slice(0, 8).map(p => `
          <div class="feed-item">
            <div class="feed-dot" style="background:#ff6b35;"></div>
            <div class="feed-body">
              <div class="feed-text">${esc(p.title || 'Untitled')}</div>
              <div class="feed-meta">${p.score !== undefined ? p.score + ' pts' : ''} ${p.num_comments !== undefined ? '/ ' + p.num_comments + ' comments' : ''}</div>
            </div>
          </div>`).join('');
      } else {
        content.innerHTML = '<div class="empty-state">No posts found.</div>';
      }
    } else {
      content.innerHTML = '<div class="empty-state">Could not load preview.</div>';
    }
  } catch(e) {
    content.innerHTML = '<div class="empty-state">Preview failed.</div>';
  }
}

function closePreviewPanel() {
  const panel = document.getElementById('explorePreviewPanel');
  if (panel) panel.style.display = 'none';
}

// ── Latest Articles (News Feed page) ──────────────────────────────

async function loadNewsFeed() {
  const list = document.getElementById('newsFeedList');
  if (!list) return;

  try {
    const r = await apiFetch('/news/feed?limit=20');
    if (r.ok) {
      const data = await r.json();
      const articles = data.articles || data || [];
      if (Array.isArray(articles) && articles.length) {
        list.innerHTML = articles.map(a => `
          <div class="article-card">
            <div class="feed-dot" style="background:var(--accent); margin-top:4px;"></div>
            <div class="article-card-body">
              <div class="article-card-title">
                ${a.link ? `<a href="${esc(a.link)}" target="_blank" rel="noopener">${esc(a.title || 'Untitled')}</a>` : esc(a.title || 'Untitled')}
              </div>
              <div class="article-card-snippet">${esc(a.snippet || a.summary || '')}</div>
              <div class="article-card-meta">
                ${a.source_name ? esc(a.source_name) : ''} 
                ${a.published_at ? ' / ' + new Date(a.published_at).toLocaleDateString() : ''}
                ${a.relevance_score ? ' / score ' + a.relevance_score.toFixed(1) : ''}
              </div>
            </div>
            <button class="btn-ghost" style="margin:0; padding:4px 8px; font-size:10px; width:auto; white-space:nowrap;" 
                    onclick="createPostFromArticle(${JSON.stringify(a.title || '').replace(/"/g, '&quot;')}, ${JSON.stringify(a.link || '').replace(/"/g, '&quot;')})">
              Create Post
            </button>
          </div>`).join('');
      } else {
        list.innerHTML = '<div class="empty-state" style="padding:30px;">No articles yet. Add feeds and run the pipeline to see content here.</div>';
      }
    } else {
      list.innerHTML = '<div class="empty-state" style="padding:30px;">Could not load articles.</div>';
    }
  } catch(e) {
    list.innerHTML = '<div class="empty-state" style="padding:30px;">Failed to load feed.</div>';
  }
}

function createPostFromArticle(title, link) {
  // Open the Studio (Compose) page and prefill with article context
  goto('studio');
  setTimeout(() => {
    const ta = document.getElementById('composeBody');
    if (ta) ta.value = `Here is an interesting article: "${title}"\n\nRead more: ${link}\n\n`;
    toast('Article loaded into composer', 'success');
  }, 300);
}

// ── Boot: load user feeds ─────────────────────────────────────────

function startWorkflow() {
  const btn = document.getElementById('runPipelineBtn');
  const tracker = document.getElementById('workflowTracker');
  const log = document.getElementById('workflowTrackerLog');
  
  if (!btn || !tracker || !log) return;
  
  if (userFeeds.length === 0) {
    toast('Please add at least one feed first', 'warning');
    return;
  }
  
  btn.disabled = true;
  tracker.style.display = 'block';
  log.innerHTML = `<div class="feed-item" style="font-size:13px; color:var(--text-2);">
    <span style="color:var(--accent); margin-right:8px;">&#9889;</span> Connecting to LangGraph engine...
  </div>`;
  
  const token = localStorage.getItem('kontent_token');
  const es = new EventSource(`/api/v1/workflow/run?token=${token || ''}`);
  
  es.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.status === 'DONE') {
      es.close();
      btn.disabled = false;
      toast('Content automation finished!', 'success');
      
      const el = document.createElement('div');
      el.className = 'feed-item';
      el.style.fontSize = '13px';
      el.style.color = 'var(--text-2)';
      el.innerHTML = `<span style="color:var(--success); margin-right:8px;">&#10003;</span> Workflow complete. Assets ready for review!`;
      log.appendChild(el);
      log.scrollTop = log.scrollHeight;
      
      window.latestWorkflowResult = data;
      
      setTimeout(() => {
         closeAutomateModal();
         openHitlModal(window.latestWorkflowResult);
      }, 1500);
      
      return;
    }
    
    const el = document.createElement('div');
    el.className = 'feed-item';
    el.style.fontSize = '13px';
    el.style.color = 'var(--text-2)';
    el.innerHTML = `<span style="color:var(--accent); margin-right:8px;">&#10003;</span> ${data.status || 'Processing...'}`;
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
  };

  es.onerror = function(err) {
    es.close();
    btn.disabled = false;
    toast('Pipeline execution error', 'error');
    console.error('SSE Error:', err);
  };
}

async function loadUserFeeds() {
  try {
    const r = await apiFetch('/news/feed/sources');
    if (r.ok) {
      userFeeds = await r.json();
      renderActiveFeeds();
      updateTierBadge();
      loadNewsFeed();
    }
  } catch(e) {}
}
loadUserFeeds();

// ── HITL Modal ────────────────────────────────────────────────────
window.openHitlModal = function(data) {
  const modal = document.getElementById('hitlModalOverlay');
  if (modal) {
      modal.classList.add('open');
      
      // Inject drafted content. Defaulting to Twitter text
      const captionText = document.getElementById('hitlCaptionInput');
      if (captionText && data.scripts) {
          captionText.value = data.scripts.twitter || data.scripts.linkedin || '';
      }
      
      // Inject video
      const vidContainer = document.getElementById('hitlVideoContainer');
      if (vidContainer && data.video_asset) {
          vidContainer.innerHTML = `<video src="${data.video_asset}" autoplay loop muted controls style="width:100%; height:100%; object-fit:cover;"></video>`;
      }
  }
};

window.closeHitlModal = function() {
  const modal = document.getElementById('hitlModalOverlay');
  if (modal) modal.classList.remove('open');
};

window.approveAndPublish = function() {
   // Validate platforms
   const platforms = [];
   if(document.getElementById('hitlToggleTwitter').checked) platforms.push('twitter');
   if(document.getElementById('hitlToggleLinkedin').checked) platforms.push('linkedin');
   if(document.getElementById('hitlToggleYoutube').checked) platforms.push('youtube');
   if(document.getElementById('hitlToggleTiktok').checked) platforms.push('tiktok');
   
   if (platforms.length === 0) {
       toast('Please select at least one platform to publish', 'warning');
       return;
   }
   
   toast(`Publishing approved content to ${platforms.join(', ')}...`, 'success');
   setTimeout(() => closeHitlModal(), 1000);
};

window.saveAssetsToLibrary = async function() {
    const data = window.latestWorkflowResult;
    if (!data) return;
    
    toast('Saving to Asset Library...', 'info');
    
    // Call the backend to save the asset
    const r = await apiFetch('/media/assets', {
        method: 'POST',
        body: JSON.stringify({
            asset_type: 'video',
            content_url: data.video_asset,
            text_content: document.getElementById('hitlCaptionInput').value,
            title: data.selected_article?.title || 'Auto-generated Asset'
        })
    });
    
    if (r.ok) {
        toast('Generated assets saved to library!', 'success');
    } else {
        toast('Failed to save to library', 'error');
    }
};


