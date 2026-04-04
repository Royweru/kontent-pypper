════════════════════════════════════════════════
FIX: STUDIO EMPTY STATE PAGE
Target: #page-studio in dashboard.html + dashboard.css
════════════════════════════════════════════════

STEP 1 — Fix the invisible button.
Locate the "Start Writing" button in #page-studio:
  <button class="btn-primary" onclick="openStudioModal()"
    style="font-size: 14px; padding: 14px 24px; display: inline-flex;
    align-items: center; gap: 8px; width: auto;
    background: var(--white); color: var(--deep);
    box-shadow: 0 0 30px rgba(255,255,255,0.15);">

REPLACE the entire inline style with:
  style="font-size: 14px; padding: 14px 32px; display: inline-flex;
  align-items: center; gap: 10px; width: auto;
  background: var(--accent); color: var(--deep);
  font-weight: 700; letter-spacing: 0.02em;
  box-shadow: 0 0 32px rgba(200,249,81,0.35),
              0 4px 16px rgba(0,0,0,0.4);
  margin-top: 0;"

The background was var(--white) — white on near-black is
actually invisible because --white is likely undefined or
transparent in your token set. Correcting to var(--accent).

STEP 2 — Rework the full empty state container.
Replace the entire inner div of #page-studio (the
margin-top:40px centered block) with this structure:

  <div class="studio-empty-state">

    <!-- Ambient orb behind icon -->
    <div class="studio-empty-orb" aria-hidden="true"></div>

    <!-- Sparkle icon with pulse -->
    <div class="studio-empty-icon" aria-hidden="true">✦</div>

    <!-- Heading -->
    <h2 class="studio-empty-heading">Create a New Post</h2>

    <!-- Subtext -->
    <p class="studio-empty-sub">
      Drop your raw idea, link, or thoughts. The AI adapts it 
      into format-perfect posts for every platform you've connected.
    </p>

    <!-- CTA -->
    <button class="btn-primary studio-empty-cta" 
      onclick="openStudioModal()">
      <span style="font-size:18px; font-weight:200; 
        line-height:0;">+</span>
      Start Writing
    </button>

    <!-- Hint strip -->
    <div class="studio-hints">
      <div class="studio-hint">
        <span class="studio-hint-dot"></span>
        AI-optimized per platform
      </div>
      <div class="studio-hint">
        <span class="studio-hint-dot"></span>
        One-click multi-publish
      </div>
      <div class="studio-hint">
        <span class="studio-hint-dot"></span>
        Schedule or publish instantly
      </div>
    </div>

  </div>

STEP 3 — Add these CSS rules to dashboard.css:

  /*── Studio Empty State ──────────────────────────*/
  .studio-empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    min-height: calc(100vh - var(--topbar-h) - 120px);
    position: relative;
    padding: 40px 24px;
    max-width: 480px;
    margin: 0 auto;
  }

  /*Ambient background orb*/
  .studio-empty-orb {
    position: absolute;
    width: 520px;
    height: 520px;
    border-radius: 50%;
    background: radial-gradient(circle,
      rgba(200,249,81,0.05) 0%,
      rgba(200,249,81,0.02) 30%,
      transparent 70%);
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    pointer-events: none;
    z-index: 0;
    animation: studio-orb-pulse 6s ease-in-out infinite alternate;
  }

  @keyframes studio-orb-pulse {
    from { opacity: 0.6; transform: translate(-50%,-50%) scale(0.95); }
    to   { opacity: 1;   transform: translate(-50%,-50%) scale(1.05); }
  }

  /*Sparkle icon*/
  .studio-empty-icon {
    font-size: 44px;
    color: var(--accent);
    margin-bottom: 24px;
    position: relative;
    z-index: 1;
    text-shadow: 0 0 30px rgba(200,249,81,0.4),
                 0 0 60px rgba(200,249,81,0.15);
    animation: icon-breathe 4s ease-in-out infinite alternate;
  }

  @keyframes icon-breathe {
    from { text-shadow: 0 0 20px rgba(200,249,81,0.3); }
    to   { text-shadow: 0 0 40px rgba(200,249,81,0.6),
                        0 0 80px rgba(200,249,81,0.2); }
  }

  /*Heading*/
  .studio-empty-heading {
    font-size: 22px;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 12px;
    letter-spacing: -0.02em;
    position: relative;
    z-index: 1;
  }

  /*Subtext*/
  .studio-empty-sub {
    font-size: 13.5px;
    color: var(--text-muted);
    line-height: 1.65;
    margin-bottom: 32px;
    max-width: 360px;
    position: relative;
    z-index: 1;
  }

  /*CTA Button*/
  .studio-empty-cta {
    position: relative;
    z-index: 1;
    font-size: 14px;
    padding: 13px 32px;
    display: inline-flex;
    align-items: center;
    gap: 10px;
    width: auto;
    font-weight: 700;
    letter-spacing: 0.02em;
    margin-top: 0;
    box-shadow: 0 0 32px rgba(200,249,81,0.30),
                0 4px 16px rgba(0,0,0,0.35);
    transition: background 0.2s, box-shadow 0.2s, transform 0.15s;
  }

  .studio-empty-cta:hover {
    background: var(--accent-hover);
    box-shadow: 0 0 48px rgba(200,249,81,0.45),
                0 8px 24px rgba(0,0,0,0.4);
    transform: translateY(-2px);
  }

  /*Hint strip*/
  .studio-hints {
    display: flex;
    align-items: center;
    gap: 20px;
    margin-top: 28px;
    position: relative;
    z-index: 1;
    flex-wrap: wrap;
    justify-content: center;
  }

  .studio-hint {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 0.08em;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  .studio-hint-dot {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--accent);
    opacity: 0.5;
    flex-shrink: 0;
  }

STEP 4 — Fix the section header alignment.
In #page-studio, the section-header div currently has:
  justify-content: space-between (from .section-header base style)
  with "AI Studio" on left and "Write once..." on right.

CHANGE the section-header in #page-studio to:
  <div class="section-header" style="margin-bottom:0;
    flex-direction: column; align-items: flex-start; gap: 4px;">
    <span class="glow-label">AI Studio</span>
    <span class="muted" style="font-size:12px;
      font-family:var(--font-mono); letter-spacing:0.04em;">
      Write once — generate for everywhere
    </span>
  </div>

This anchors both text pieces to the left, same alignment,
same voice — instead of opposite ends of the page.

════════════════════════════════════════════════
END OF STUDIO EMPTY STATE FIX
════════════════════════════════════════════════
