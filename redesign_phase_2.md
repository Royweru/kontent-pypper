════════════════════════════════════════════════════════════
SUPPLEMENTAL REDESIGN — AUTH PAGES + SIDEBAR ICON FIX
KontentPyper | Complement to the dashboard redesign prompt
Apply these AFTER the dashboard redesign instructions.
════════════════════════════════════════════════════════════

════════════════════════════════════════════════
FIX 1 — SIDEBAR ICON: Post History vs Hamburger Conflict
(dashboard.html)
════════════════════════════════════════════════

In the sidebar nav, locate the Post History nav-item button:
  <span class="nav-icon" aria-hidden="true">≡</span>

CHANGE the inner unicode symbol from:  ≡
TO:                                    ⊟

So it reads:
  <span class="nav-icon" aria-hidden="true">⊟</span>

This visually distinguishes the post history icon from
the topbar hamburger toggle (which uses three CSS bars).
The ⊟ symbol reads as "list with a container" — semantically
appropriate for post history, and visually distinct.

════════════════════════════════════════════════
FIX 2 — login.css: Wrong Brand Color (Critical Bug)
════════════════════════════════════════════════

In login.css, locate the .bg-grid rule:
  background-image:
    linear-gradient(rgba(0,229,160,0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,229,160,0.035) 1px, transparent 1px);

REPLACE rgba(0,229,160,...) with the correct brand lime:
  background-image:
    linear-gradient(rgba(200,249,81,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(200,249,81,0.025) 1px, transparent 1px);
  background-size: 52px 52px;

Locate the .bg-orb rule:
  background: radial-gradient(circle, rgba(0,229,160,0.07) 0%, transparent 70%);

REPLACE with:
  background: radial-gradient(circle, rgba(200,249,81,0.055) 0%,
    rgba(92,84,144,0.025) 45%, transparent 70%);

This adds a faint lavender edge to the orb — creating depth
and using the color system properly.

Locate .btn-primary:hover in login.css:
  background: #1ffbb8;
  box-shadow: 0 0 24px rgba(0,229,160,0.3);

REPLACE with:
  background: var(--accent-hover);
  box-shadow: 0 0 28px rgba(200,249,81,0.28), 0 4px 12px rgba(0,0,0,0.3);

════════════════════════════════════════════════
FIX 3 — login.css: Card Refinements
════════════════════════════════════════════════

TARGET: .card
CHANGE:
  background: var(--surface);        → background: var(--base);
  border: 1px solid var(--border-hi); → keep but change to var(--border-med)
  padding: 44px 42px;                → padding: 48px 44px
  max-width: 408px;                  → max-width: 420px

CHANGE box-shadow from:
  0 0 0 1px rgba(0,229,160,0.05),
  0 24px 80px rgba(0,0,0,0.5),
  inset 0 1px 0 rgba(255,255,255,0.04);

TO:
  0 0 0 1px rgba(200,249,81,0.04),
  0 32px 80px rgba(0,0,0,0.55),
  0 0 60px rgba(200,249,81,0.03),
  inset 0 1px 0 rgba(255,255,255,0.03);

The ::before top accent line on .card — UPDATE:
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  opacity: 0.35;   ← was 0.5, dial it down, more subtle

ADD a new ::after glow on .card for depth:
  .card::after {
    content: '';
    position: absolute;
    bottom: -1px; left: 40px; right: 40px;
    height: 1px;
    background: linear-gradient(90deg, transparent,
      rgba(200,249,81,0.08), transparent);
    border-radius: 1px;
  }

TARGET: input[type="text"], input[type="email"], input[type="password"]
CHANGE:
  padding: 12px 16px; → padding: 11px 14px
  font-size: 15px;    → font-size: 14px
  border-radius: var(--radius); → border-radius: var(--radius-sm)

ADD:
  letter-spacing: 0.01em;

For input:focus — CHANGE:
  box-shadow: 0 0 0 3px var(--accent-glow);
TO:
  box-shadow: 0 0 0 3px rgba(200,249,81,0.10),
              0 0 0 1px rgba(200,249,81,0.20);
This is a two-ring focus ring — more refined than a single flat glow.

TARGET: label
CHANGE:
  font-size: 11px;  → font-size: 10px
  letter-spacing: 0.08em; → letter-spacing: 0.14em
  margin-bottom: 7px; → margin-bottom: 6px

TARGET: .wordmark
CHANGE:
  margin-bottom: 32px; → margin-bottom: 28px
ADD:
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border);

TARGET: .wordmark-name
  font-size: 19px; → font-size: 17px

TARGET: .glow-label (the "Operator access" / "New operator registration" line)
ADD:
  margin-bottom: 20px;   ← tighten it

TARGET: .form-group
CHANGE:
  margin-bottom: 18px; → margin-bottom: 16px

TARGET: .btn-primary (in login.css, not design-system)
CHANGE padding from 13px to:  padding: 12px 16px
ADD:
  letter-spacing: 0.02em;
  border-radius: var(--radius-sm);

TARGET: .card-footer
CHANGE:
  margin-top: 22px; → margin-top: 20px
  font-size: 11px;  → font-size: 10.5px

════════════════════════════════════════════════
FIX 4 — login.css: Password Toggle Eyecon
════════════════════════════════════════════════

Add this CSS block to login.css:

  .input-wrap {
    position: relative;
  }

  .input-wrap input {
    padding-right: 42px;
  }

  .pw-toggle {
    position: absolute;
    right: 12px;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-dim);
    font-size: 14px;
    padding: 4px;
    display: flex;
    align-items: center;
    transition: color 0.15s;
    line-height: 0;
  }

  .pw-toggle:hover {
    color: var(--text-muted);
  }

  .pw-toggle svg {
    width: 16px;
    height: 16px;
    stroke: currentColor;
    stroke-width: 1.8;
    fill: none;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

════════════════════════════════════════════════
FIX 5 — login.html: DOM Changes
════════════════════════════════════════════════

CHANGE the wordmark block. Replace:
  <div class="wordmark-icon" aria-hidden="true"></div>
WITH:
  <img src="/logo.png" alt="KontentPyper"
    style="width:36px;height:36px;border-radius:7px;flex-shrink:0;" />

This makes both auth pages use the actual logo, not a CSS triangle.

CHANGE the glow-label text from:
  "Operator access"
TO:
  "Welcome back"

CHANGE the Password form-group from this:
  <div class="form-group">
    <label for="password">Password</label>
    <input id="password" type="password" ... />
  </div>

TO:
  <div class="form-group">
    <label for="password">Password</label>
    <div class="input-wrap">
      <input id="password" type="password"
        placeholder="••••••••••"
        autocomplete="current-password" required />
      <button type="button" class="pw-toggle"
        id="pwToggle" aria-label="Show password">
        <svg id="eyeIcon" viewBox="0 0 24 24">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
          <circle cx="12" cy="12" r="3"/>
        </svg>
      </button>
    </div>
  </div>

Then add this script block at the bottom of login.html
BEFORE the closing </body>, right above the existing script tag:
  <script>
    const pwToggle = document.getElementById('pwToggle');
    const pwInput  = document.getElementById('password');
    const eyeIcon  = document.getElementById('eyeIcon');
    const eyeOpen  = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
    const eyeClosed = '<path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>';
    if (pwToggle) {
      pwToggle.addEventListener('click', () => {
        const isHidden = pwInput.type === 'password';
        pwInput.type = isHidden ? 'text' : 'password';
        eyeIcon.innerHTML = isHidden ? eyeClosed : eyeOpen;
      });
    }
  </script>

════════════════════════════════════════════════
FIX 6 — signup.html: Major Structural Changes
════════════════════════════════════════════════

REMOVE the entire <nav class="pub-nav"> block from signup.html.
The auth experience should be navbar-free — a clean, focused
environment. No nav on login = no nav on signup.

CHANGE the .signup-page wrapper padding from:
  (currently defined in public.css as: padding: 80px 24px)
UPDATE in login.css instead (add a new rule since pub-nav is gone):
  .signup-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40px 24px;
  }

This centers the card vertically in the full viewport height,
same as the login page experience.

CHANGE the glow-label text from:
  "New operator registration"
TO:
  "Start automating today"

CHANGE wordmark block — the signup page already uses <img> correctly.
Standardize it to match login format exactly:
  <div class="wordmark">
    <img src="/logo.png" alt="KontentPyper"
      style="width:36px;height:36px;border-radius:7px;flex-shrink:0;" />
    <div>
      <div class="wordmark-name">KontentPyper</div>
      <div class="wordmark-tag">CREATE ACCOUNT</div>
    </div>
  </div>

For the Password field in signup — wrap it with the same
pw-toggle pattern (eye toggle). Replicate the exact same
.input-wrap + .pw-toggle structure as login.html above,
on BOTH the "Password" and "Confirm Password" fields.
Give the second toggle id="pwToggle2" and input id stays
"confirmPassword". Replicate the same toggle JS for pwToggle2.

════════════════════════════════════════════════
FIX 7 — signup.html: Password Strength Meter
════════════════════════════════════════════════

After the Password form-group (the first password field,
NOT confirm password), insert this HTML:
  <div class="pw-strength-wrap" id="pwStrengthWrap"
    style="display:none; margin-top:-10px; margin-bottom:14px;">
    <div class="pw-strength-bar">
      <div class="pw-strength-fill" id="pwStrengthFill"></div>
    </div>
    <div class="pw-strength-label" id="pwStrengthLabel">Weak</div>
  </div>

Add to login.css:
  .pw-strength-wrap { display: flex; align-items: center; gap: 10px; }

  .pw-strength-bar {
    flex: 1;
    height: 3px;
    background: var(--border-med);
    border-radius: 99px;
    overflow: hidden;
  }

  .pw-strength-fill {
    height: 100%;
    width: 0%;
    border-radius: 99px;
    transition: width 0.35s var(--ease), background 0.35s;
  }

  .pw-strength-label {
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-dim);
    min-width: 40px;
    text-align: right;
    transition: color 0.3s;
  }

Then add this script block BEFORE the closing </body> tag
in signup.html (above the existing script tag):
  <script>
    // Password strength meter
    const pwField = document.getElementById('password');
    const wrap    = document.getElementById('pwStrengthWrap');
    const fill    = document.getElementById('pwStrengthFill');
    const label   = document.getElementById('pwStrengthLabel');
    const levels  = [
      { min: 0,  label: 'Weak',   color: '#ff4e6a', width: '25%'  },
      { min: 6,  label: 'Fair',   color: '#f0a030', width: '50%'  },
      { min: 10, label: 'Good',   color: '#c8f951', width: '75%'  },
      { min: 14, label: 'Strong', color: '#1affd5', width: '100%' },
    ];
    if (pwField) {
      pwField.addEventListener('input', () => {
        const v = pwField.value;
        if (!v) { wrap.style.display = 'none'; return; }
        wrap.style.display = 'flex';
        const score = [
          v.length >= 8, v.length >= 12,
          /[A-Z]/.test(v), /[0-9]/.test(v),
          /[^A-Za-z0-9]/.test(v)
        ].filter(Boolean).length;
        const lv = score <= 1 ? levels[0] : score <= 2 ? levels[1]
                 : score <= 3 ? levels[2] : levels[3];
        fill.style.width     = lv.width;
        fill.style.background= lv.color;
        label.textContent    = lv.label;
        label.style.color    = lv.color;
      });
    }

    // Eye toggle — signup password fields
    ['pwToggle','pwToggle2'].forEach(id => {
      const btn = document.getElementById(id);
      if (!btn) return;
      const input = btn.closest('.input-wrap').querySelector('input');
      const svg   = btn.querySelector('svg');
      const open  = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
      const closed= '<path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>';
      btn.addEventListener('click', () => {
        const hidden = input.type === 'password';
        input.type = hidden ? 'text' : 'password';
        svg.innerHTML = hidden ? closed : open;
      });
    });
  </script>

════════════════════════════════════════════════
FIX 8 — public.css: Auth page background consistency
════════════════════════════════════════════════

The signup page imports public.css which has no .bg-grid
or .bg-orb rules. Add these to public.css so signup.html
has the same atmospheric background as login.html:

  /*Auth page background effects (shared with login)*/
  .bg-grid {
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(200,249,81,0.022) 1px, transparent 1px),
      linear-gradient(90deg, rgba(200,249,81,0.022) 1px, transparent 1px);
    background-size: 52px 52px;
    pointer-events: none;
    z-index: 0;
  }

  .bg-orb {
    position: fixed;
    width: 680px;
    height: 680px;
    border-radius: 50%;
    background: radial-gradient(circle,
      rgba(200,249,81,0.05) 0%,
      rgba(92,84,144,0.02) 45%,
      transparent 70%);
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    pointer-events: none;
    z-index: 0;
    animation: orb-breathe 10s ease-in-out infinite alternate;
  }

  @keyframes orb-breathe {
    from { opacity: 0.7; transform: translate(-50%, -50%) scale(0.97); }
    to   { opacity: 1;   transform: translate(-50%, -50%) scale(1.04); }
  }

Note: login.css already defines .bg-grid and .bg-orb.
After applying Fix 2 (the color correction above),
you can leave login.css definitions as-is — they will
override public.css for the login page since login.html
does NOT import public.css.

════════════════════════════════════════════════
FINAL PASS CHECKLIST FOR AUTH PAGES
════════════════════════════════════════════════

After all changes verify:

1. Login page: no navbar, card centered vertically in viewport ✓
2. Signup page: no navbar (removed), card centered same as login ✓
3. Both pages: logo renders as <img> not CSS triangle ✓
4. Both pages: bg-grid and bg-orb use rgba(200,249,81,...) NOT rgba(0,229,160,...) ✓
5. Both pages: btn-primary hover glow is lime, NOT teal ✓
6. Password fields on both pages: have eye toggle button inside .input-wrap ✓
7. Signup: password strength meter appears on first keystroke ✓
8. Sidebar: Post History icon is ⊟ not ≡ ✓
9. No lavender color used on any CTA button on any page ✓
10. Both auth pages feel like ONE product — same card, same bg, same energy ✓

════════════════════════════════════════════════
END OF SUPPLEMENTAL INSTRUCTIONS
════════════════════════════════════════════════
