You are redesigning the KontentPyper dashboard UI. You have access to four CSS files:
design-system.css, dashboard.css, studio-modal.css, and carousel.css — and the main
dashboard.html. Make ALL changes listed below precisely. Do NOT change JavaScript logic,
routing, or HTML structure beyond what is specified. Do NOT change font families.
Do NOT remove any existing class names — only modify their CSS properties.

════════════════════════════════════════════════
SECTION 1 — DESIGN SYSTEM (design-system.css)
════════════════════════════════════════════════

Replace the entire :root block with this exact token set:

:root {
  /*Depth layers*/
  --deep:      #0e0e14;
  --base:      #121219;
  --surface:   #181824;
  --surface2:  #1e1e2e;
  --surface3:  #242438;

  /*Borders*/
  --border:    rgba(200, 249, 81, 0.07);
  --border-hi: rgba(200, 249, 81, 0.20);
  --border-med:rgba(200, 249, 81, 0.12);

  /*Primary accent — lime-chartreuse*/
  --accent:      #c8f951;
  --accent-hover:#d6ff5b;
  --accent-dim:  #a0cc35;
  --accent-glow: rgba(200, 249, 81, 0.09);
  --accent-glow-hi: rgba(200, 249, 81, 0.16);

  /*Secondary — muted lavender (UI only, NEVER CTAs)*/
  --lavender:     #5c5490;
  --lavender-dim: rgba(92, 84, 144, 0.12);
  --lavender-border: rgba(92, 84, 144, 0.25);

  /*Tertiary — electric cyan (data/live status only)*/
  --cyan:      #1affd5;
  --cyan-dim:  rgba(26, 255, 213, 0.08);
  --cyan-border: rgba(26, 255, 213, 0.20);

  /*Text hierarchy — 4 levels*/
  --text:       #eceff5;
  --text-muted: #6e7385;
  --text-dim:   #3e4156;
  --text-faint: #2a2c3d;

  /*Semantic*/
  --success:   #c8f951;
  --warning:   #f0a030;
  --danger:    #ff4e6a;
  --danger-dim:rgba(255, 78, 106, 0.12);

  /*Typography*/
  --font-display: 'Space Grotesk', system-ui, sans-serif;
  --font-mono:    'JetBrains Mono', 'Fira Code', monospace;

  /*Sizing*/
  --sidebar-w:  252px;
  --topbar-h:   62px;
  --radius:     12px;
  --radius-sm:  7px;
  --radius-lg:  18px;
  --radius-xl:  24px;

  /*Transitions*/
  --ease:  cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
}

Change html, body background to: var(--deep)

════════════════════════════════════════════════
SECTION 2 — SIDEBAR (dashboard.css)
════════════════════════════════════════════════

TARGET: .sidebar

- Change background to: var(--base)
- Change border-right to: 1px solid var(--border-med)
- Keep the scanline texture but change its opacity from 0.012 to 0.018

TARGET: .sidebar-header

- Change padding from: 22px 22px 20px
  to:                  28px 22px 24px     ← MORE top/bottom breathing room
- border-bottom: 1px solid var(--border-med)

TARGET: .sidebar-nav

- Change padding from: 16px 12px
  to:                  20px 12px 20px    ← more top AND bottom padding on the nav section

TARGET: .nav-group-label

- Change padding from: 12px 10px 5px
  to:                  16px 10px 6px     ← more space above group labels
- Change color to: var(--text-dim)
- Change font-size from 10px to 9.5px
- Add: letter-spacing: 0.18em

TARGET: .nav-item

- Change padding from: 9px 10px
  to:                  10px 12px         ← more horizontal padding, slightly taller
- Change font-size from: 13.5px to: 13px
- Change gap from 10px to 12px

TARGET: .nav-item:hover

- background: rgba(200, 249, 81, 0.04)   ← subtle lime tint on hover (was white)
- color: var(--text)

TARGET: .nav-item.active

- background: rgba(200, 249, 81, 0.08)
- color: var(--accent)
- Add: box-shadow: inset 0 0 0 1px rgba(200,249,81,0.10)

TARGET: .nav-item.active::before (left border indicator)

- Change left from -12px to -12px (keep)
- Change width from 2px to 3px
- Add: box-shadow: 0 0 10px rgba(200,249,81,0.6), 0 0 20px rgba(200,249,81,0.2)

TARGET: .sidebar-footer

- Change padding from: 16px  to:  20px 16px   ← more top/bottom padding
- border-top: 1px solid var(--border-med)

TARGET: .user-avatar

- Change background to: var(--surface3)
- Change border to: 1px solid var(--border-hi)
- Change border-radius to: var(--radius-sm)
- Add: box-shadow: 0 0 12px rgba(200,249,81,0.08)

════════════════════════════════════════════════
SECTION 3 — TOPBAR (dashboard.css)
════════════════════════════════════════════════

TARGET: .topbar

- Change height from: var(--topbar-h) → use: min-height: var(--topbar-h)
- Change padding from: 0 28px  to:  0 32px
- Change background from: rgba(17,17,24,0.85) to: rgba(14,14,20,0.90)
- Add: border-bottom: 1px solid var(--border-med)

TARGET: .status-pill

- Change background from: rgba(200,249,81,0.07) to: var(--cyan-dim)
- Change border from: rgba(200,249,81,0.18) to: var(--cyan-border)
- Change color from: var(--accent) to: var(--cyan)
- Change font-size from 11px to 10.5px
- Add: letter-spacing: 0.1em

TARGET: .status-dot

- Change background from: var(--accent) to: var(--cyan)
- Change animation to include a subtle spread:
  @keyframes blink {
    0%, 100% { opacity: 1; box-shadow: 0 0 6px var(--cyan); }
    50%       { opacity: 0.4; box-shadow: none; }
  }

════════════════════════════════════════════════
SECTION 4 — BUTTONS (dashboard.css)
════════════════════════════════════════════════

TARGET: .btn-primary

- Change border-radius from: var(--radius-sm) to: var(--radius-sm)
- Change font-weight from 700 to 600
- Change letter-spacing from 0.01em to 0.02em
- Change transition to: background 0.18s, box-shadow 0.18s, transform 0.12s

TARGET: .btn-primary:hover

- Change background from: #d5ff6a to: var(--accent-hover)
- Change box-shadow to: 0 0 24px rgba(200,249,81,0.30), 0 4px 12px rgba(0,0,0,0.3)

THE AUTOMATE BUTTON (in dashboard.html, the inline-styled second btn-primary):
REMOVE these inline styles from the "Automate Content from Scratch" button:
  background: var(--lavender); color: var(--deep);
REPLACE with:
  background: transparent;
  border: 1px solid var(--border-hi);
  color: var(--text-muted);
  font-weight: 500;
This demotes it visually to a secondary action. "Create Post" must be the single
dominant CTA. Only one button should glow lime at a time.

For the "Automate" button hover, add a new class .btn-secondary in dashboard.css:
.btn-secondary {
  background: transparent;
  border: 1px solid var(--border-hi);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  padding: 10px 18px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: border-color 0.2s, color 0.2s, background 0.2s;
}
.btn-secondary:hover {
  border-color: var(--lavender-border);
  color: var(--text);
  background: var(--lavender-dim);
}
Then apply class="btn-secondary" to the "Automate Content from Scratch" button
instead of btn-primary.

════════════════════════════════════════════════
SECTION 5 — STAT CARDS (dashboard.css)
════════════════════════════════════════════════

TARGET: .stat-card

- Change background to: var(--surface)
- Change border to: 1px solid var(--border-med)
- Change border-radius to: var(--radius)
- Change padding from: 18px 20px  to:  22px 22px
- Add: position: relative; overflow: hidden;
- Remove the ::after pseudo element (the small top-right accent line)
- Replace ::after with a new LEFT border accent:
  .stat-card::before {
    content: '';
    position: absolute;
    left: 0; top: 20%; bottom: 20%;
    width: 2px;
    background: linear-gradient(180deg, transparent, var(--accent), transparent);
    border-radius: 2px;
    opacity: 0;
    transition: opacity 0.3s;
  }
  .stat-card:hover::before { opacity: 1; }

TARGET: .stat-label

- Change font-size from 10px to 9.5px
- Change letter-spacing from 0.12em to 0.16em
- Change color to: var(--text-dim)
- Change margin-bottom from 10px to 12px

TARGET: .stat-value

- Change font-size from 30px to 28px
- Change letter-spacing from -0.02em to -0.03em
- Change color to: var(--text)
- Add: line-height: 1

TARGET: .stat-delta

- Change font-size from 11px to 10.5px
- Change color to: var(--text-muted)
- Change margin-top to: 8px

The "Agent Status" stat-card — in dashboard.html, add a data attribute:
data-status="on" to that stat-card div. Then add this CSS:
.stat-card[data-status="on"] {
  border-color: var(--cyan-border);
  background: linear-gradient(135deg, var(--surface) 60%, rgba(26,255,213,0.03) 100%);
}
.stat-card[data-status="on"] .stat-value {
  color: var(--cyan);
}
.stat-card[data-status="on"] .stat-delta.up {
  color: var(--cyan);
}

For the "Total Posts" card — handle empty state. In dashboard.js, when stat-posts
renders "0", instead set the innerHTML of stat-posts to:
  <span style="font-size:16px; color:var(--text-dim); font-weight:400;
  letter-spacing:0;">No posts yet</span>
And set stat-plan innerHTML to:
  <a onclick="openStudioModal()" style="color:var(--accent); cursor:pointer;
  font-size:10px; text-decoration:underline; text-underline-offset:3px;
  letter-spacing:0.06em;">→ CREATE YOUR FIRST</a>

════════════════════════════════════════════════
SECTION 6 — ENGAGEMENT CHART (dashboard.css + dashboard.js)
════════════════════════════════════════════════

TARGET: .surface-card (the chart's parent card)

- Add below the section-title for the chart:
  <span style="font-family:var(--font-mono); font-size:9px; color:var(--text-dim);
  letter-spacing:0.1em; text-transform:uppercase;">TOTAL ENGAGEMENTS</span>

TARGET: .chart-wrap in dashboard.css

- Change height from 120px to 140px
- Add: padding: 0 4px

TARGET: .chart-bar

- Change background to:
  linear-gradient(180deg, var(--accent) 0%, rgba(200,249,81,0.06) 100%)
- Add: position: relative; cursor: pointer;
- Add tooltip on hover — add this to .chart-bar::after:
  .chart-bar {
    --bar-value: '';
  }
  (The JS already handles injecting bars — just add a title attribute to each bar
   element with the week number and value, e.g. title="Week 8 · 24 engagements"
   so the browser native tooltip shows context.)

Add X-axis labels to chart in dashboard.js:
After injecting bars into #chartBars, append a label row:
  <div style="display:flex; gap:6px; margin-top:6px; padding: 0 4px;">
    {weekLabels.map(w =>
      `<div style="flex:1;text-align:center;font-family:var(--font-mono);
       font-size:8px;color:var(--text-dim);letter-spacing:0.04em;">${w}</div>`
    ).join('')}
  </div>
Where weekLabels is an array like ["W1","W2","W3",...,"W12"].

════════════════════════════════════════════════
SECTION 7 — CAROUSEL CARDS (carousel.css) ← BIGGEST VISUAL CHANGE
════════════════════════════════════════════════

TARGET: .posts-carousel-container

- Add: margin-top: 12px

TARGET: .posts-carousel

- Change gap from 20px to 12px
- Add: padding: 4px 2px 20px   ← breathing room so hover shadows aren't clipped

TARGET: .carousel-card  ← MAKE CARDS SMALLER AND MORE REFINED

- Change flex from: flex: 0 0 320px  to:  flex: 0 0 240px
- Change border-radius from: var(--radius-lg) to: var(--radius)
- Change padding from: 20px  to:  14px 16px
- Change background to: var(--surface)
- Change border to: 1px solid var(--border-med)
- ADD:
  box-shadow: 0 2px 8px rgba(0,0,0,0.25);

TARGET: .carousel-card:hover

- Change transform from: translateY(-4px) to: translateY(-3px)
- Change border-color to: var(--accent)
- Change box-shadow to:
  0 8px 24px rgba(0,0,0,0.4),
  0 0 0 1px rgba(200,249,81,0.08) inset,
  0 0 16px rgba(200,249,81,0.06)

TARGET: .carousel-card-header

- Change margin-bottom from 12px to 8px

TARGET: .carousel-platform-icon

- Change width/height from 24px to 20px
- Change border-radius from 6px to 5px
- Change font-size from 12px to 10px
- Change background to: var(--surface2)
- Add: border: 1px solid var(--border)

TARGET: .carousel-card-date

- Change font-size from 11px to 9.5px
- Change padding from: 4px 8px  to:  3px 7px
- Change background to: rgba(255,255,255,0.04)
- Add: font-family: var(--font-mono); letter-spacing: 0.04em;

TARGET: .carousel-card-body

- Change font-size from 14px to 12.5px
- Change line-height from 1.5 to 1.55
- Change -webkit-line-clamp from 4 to 3  ← shorter, tighter card body
- Change margin-bottom from 16px to 10px
- Change color to: var(--text-muted)

TARGET: .carousel-card-media-preview

- Change height from 120px to 80px    ← smaller media thumbnail
- Change margin-bottom from 16px to 10px
- Change border-radius from 8px to 6px

TARGET: .carousel-card-footer

- Change padding-top from 16px to 10px
- Change margin-top to: auto

TARGET: .carousel-status-badge

- Change font-size from 11px to 9.5px
- Change padding from: 4px 10px  to:  3px 8px
- Change border-radius from 99px to 4px  ← square badges, more precise
- Add: font-family: var(--font-mono); letter-spacing: 0.08em;

For empty carousel state (when no posts exist), inject this into #postsCarousel
instead of skeleton divs when post count is 0:
  <div style="width:100%; padding: 32px 16px; text-align:center;
  color:var(--text-dim); font-size:13px; display:flex; flex-direction:column;
  align-items:center; gap:12px;">
    <div style="font-size:32px; opacity:0.4;">◈</div>
    <div>No posts published yet.</div>
    <button onclick="openStudioModal()" style="font-family:var(--font-mono);
    font-size:10px; letter-spacing:0.1em; text-transform:uppercase;
    color:var(--accent); background:var(--accent-glow); border:1px solid
    var(--border-hi); padding:6px 16px; border-radius:4px; cursor:pointer;">
      + CREATE FIRST POST
    </button>
  </div>

════════════════════════════════════════════════
SECTION 8 — MAGIC WAND FAB (dashboard.css)
════════════════════════════════════════════════

TARGET: .magic-wand-fab

- Add: aria-label="AI Co-pilot"  (already exists, keep it)
- Add below the button in dashboard.html a tooltip sibling:
  <div class="fab-tooltip">AI Co-pilot</div>
- Add to dashboard.css:
  .magic-wand-fab {
    position: fixed;
    bottom: 30px; right: 30px;
  }
  .fab-tooltip {
    position: fixed;
    bottom: 96px; right: 30px;
    background: var(--surface2);
    border: 1px solid var(--border-hi);
    color: var(--text);
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 5px 10px;
    border-radius: 4px;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s, transform 0.2s;
    transform: translateY(4px);
    white-space: nowrap;
  }
  .magic-wand-fab:hover + .fab-tooltip,
  .magic-wand-fab:focus + .fab-tooltip {
    opacity: 1;
    transform: translateY(0);
  }

════════════════════════════════════════════════
SECTION 9 — QUICK ACTIONS ROW (dashboard.html + dashboard.css)
════════════════════════════════════════════════

In dashboard.html — replace the quick-actions-row div with:
  <div class="quick-actions-row">
    <button class="btn-primary" onclick="openStudioModal()"
      style="display:inline-flex; align-items:center; gap:8px;
      width:auto; font-size:13px; padding:10px 20px; margin-top:0;">
      <span style="font-size:16px; line-height:0; font-weight:300;">+</span>
      Create Post
    </button>
    <button class="btn-secondary" onclick="openAutomateModal()"
      style="display:inline-flex; align-items:center; gap:8px;">
      <span>⚡</span> Automate Content
    </button>
  </div>

In dashboard.css, update .quick-actions-row:
  .quick-actions-row {
    display: flex;
    gap: 10px;
    margin-bottom: 28px;
    align-items: center;
  }

════════════════════════════════════════════════
SECTION 10 — SURFACE CARDS AND TWO-COL LAYOUT
════════════════════════════════════════════════

TARGET: .surface-card

- Change background to: var(--surface)
- Change border to: 1px solid var(--border-med)
- Change border-radius to: var(--radius)
- Change padding from: 20px  to:  22px 22px 20px

TARGET: .two-col

- Change gap from 16px to 14px

TARGET: .section-title (inside surface cards)

- Change font-size from 12px to 10px
- Change letter-spacing from 0.1em to 0.15em
- Add: color: var(--text-dim)

════════════════════════════════════════════════
SECTION 11 — DASHBOARD OVERVIEW LAYOUT CHANGE
════════════════════════════════════════════════

In dashboard.html, restructure the #page-overview section layout:

STEP A: Add a dashboard welcome strip above stats row:
  <div class="dash-greeting">
    <div class="dash-greeting-left">
      <div class="dash-greeting-title" id="greetingText">Good morning</div>
      <div class="dash-greeting-sub">Here's what's happening with your content.</div>
    </div>
    <div class="dash-greeting-right">
      <div class="dash-date" id="dashDate"></div>
    </div>
  </div>

Add to dashboard.css:
  .dash-greeting {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--border);
  }
  .dash-greeting-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--text);
    letter-spacing: -0.02em;
    margin-bottom: 3px;
  }
  .dash-greeting-sub {
    font-size: 12px;
    color: var(--text-muted);
    font-family: var(--font-mono);
    letter-spacing: 0.04em;
  }
  .dash-date {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-dim);
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

In dashboard.js, populate #greetingText and #dashDate on load:
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  document.getElementById('greetingText').textContent = greeting;
  document.getElementById('dashDate').textContent =
    new Date().toLocaleDateString('en-US', {weekday:'long', month:'long', day:'numeric'});

STEP B: Change the two-col grid weights so the chart is wider:
  .two-col {
    grid-template-columns: 1.4fr 1fr;   ← chart gets more space than activity
  }

STEP C: In the Recent Activity card — change the section-title to show a count badge:
  After "Recent Activity" span, add:
  <span id="postCountBadge" style="font-family:var(--font-mono); font-size:9px;
  letter-spacing:0.08em; background:var(--accent-glow); border:1px solid
  var(--border-hi); color:var(--accent); padding:2px 7px; border-radius:3px;
  margin-left:8px;">0 POSTS</span>
  Update this badge count from JS when posts load.

════════════════════════════════════════════════
SECTION 12 — PAGE PADDING
════════════════════════════════════════════════

TARGET: .page

- Change padding from: 28px 32px  to:  32px 36px 40px
- This adds more breathing room on top and a generous bottom buffer.

════════════════════════════════════════════════
END OF REDESIGN INSTRUCTIONS
════════════════════════════════════════════════

After all changes, do a final pass and ensure:

1. No element uses var(--lavender) as a button background
2. No pink/magenta color appears anywhere — if user avatars use pink,
   change them to use var(--accent) as text color on var(--surface3) background
3. The .stat-card for "Agent Status" has data-status="on" in the HTML
4. Every border in the redesign uses --border-med or --border-hi, never raw rgba white
5. The FAB tooltip div is placed immediately AFTER the .magic-wand-fab button in HTML
