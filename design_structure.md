# KontentPyper Design System & Structure Analysis

Based on a comprehensive review of the `design-system.css`, `dashboard.css`, and `studio-modal.css` files, here is the full definition of the UI/UX architecture, typography, color palettes, and component states. Ensure you adhere strictly to these defined tokens across all components.

## 1. Color Palette & Theming

The application utilizes a primary "Dark Charcoal" aesthetic, heavily contrasted with "Lime-Chartreuse" and "Lavender" accents.

### Background Layers (Depth)
- **Deep (App Background):** `#0e0e14`
- **Base (Containers/Inputs):** `#121219`
- **Surface (Cards/Modals):** `#181824`
- **Surface 2 (Hover/Active areas):** `#1e1e2e`
- **Surface 3 (Elevated Floating/Toasts):** `#242438`

### Brand Accents
- **Primary (Lime-Chartreuse):** `#c8f951`
  - *Hover/Bright:* `#d6ff5b`
  - *Dim/Border:* `#a0cc35`
  - *Glow FX:* `rgba(200, 249, 81, 0.09) - 0.16`
- **Secondary (Muted Lavender):** `#5c5490`
  - *Dim:* `rgba(92, 84, 144, 0.12)`
  - *Border:* `rgba(92, 84, 144, 0.25)`
  - *Rule:* Used strictly for UI accents, NEVER for Call-to-Action buttons.
- **Tertiary (Electric Cyan):** `#1affd5`
  - *Use Case:* Data and live status indicators only.

### Text Hierarchy
- **Text Primary:** `#eceff5` (General reading)
- **Text Muted:** `#A0A0A0` (Secondary descriptions)
- **Text Dim:** `#3e4156` (Metadata, fine print)
- **Text Faint:** `#2a2c3d` (Borders, structural marks)

### Semantic UI Colors
- **Success:** `#c8f951` (Lime-Chartreuse reused)
- **Warning / Amber:** `#f0a030`
- **Danger:** `#ff4e6a` (Danger Dim: `rgba(255, 78, 106, 0.12)`)

---

## 2. Typography

Two font families create a distinct contrast between structural clarity and technical feeling.

- **Display (Structural, Headers, Layout):** `'Space Grotesk', system-ui, sans-serif`
- **Monospace (Data, Code, Terminal, Metadata):** `'JetBrains Mono', 'Fira Code', monospace`

### Heading Scales
- **H1:** `2rem` (32px), `700` weight, `-0.02em` letter-spacing
- **H2:** `1.35rem` (~21.6px), `600` weight, `-0.01em` letter-spacing
- **H3:** `1rem` (16px), `600` weight
- **Glow Label (Brand Anchor Element):** `11px`, Monospace, `0.12em` letter-spacing, uppercase, `var(--accent)`, with a 24px wide underline accent track.

---

## 3. Structural Dimensions & Spacing

### Layout Basics
- **Sidebar Width:** `252px`
- **Topbar Height:** `62px`
- **Page Container Padding:** `32px 36px 40px`

### Border Radii
- **radius-sm:** `7px` (Inputs, Buttons)
- **radius (default):** `12px` (Cards, Panels)
- **radius-lg:** `18px` (Modals)
- **radius-xl:** `24px` (Large overlays)

### Borders
Theme borders lean heavily on very low opacity primary colors to add a neon tint to lines.
- **Border Default:** `rgba(200, 249, 81, 0.07)`
- **Border Medium:** `rgba(200, 249, 81, 0.12)`
- **Border High:** `rgba(200, 249, 81, 0.20)`

---

## 4. Global Effects & Interactions

### Noise Texture Overlay
A subtle static grain SVG is applied to `body::before` (opacity: 0.03/opacity modifier to 0.4 on background) across the application, adding organic texture to the dark interfaces.

### Transitions & Animation
- **Standard Ease:** `cubic-bezier(0.16, 1, 0.3, 1)`
- **Ease Out:** `cubic-bezier(0, 0, 0.2, 1)`
- **Page Transition:** `.page` class fades vertically upward `translateY(6px)` to `0` over `0.25s`.
- **Status Dot Pulse:** Blinks globally via `opacity: 1 -> 0.4` with box-shadow pulses.

---

## 5. UI Elements & Component Styles

### Buttons
- **Primary Button (`.btn-primary`):** 
  - Background: `var(--accent)`
  - Text: `var(--deep)` / Space Grotesk / 13px / 600 weight.
  - Hover: `var(--accent-hover)` + Drop shadow glow (`0 0 24px rgba(200,249,81,0.30)`).
- **Secondary Button (`.btn-secondary`):**
  - Transparent with `1px solid var(--border-hi)`.
  - Hover: Border switches to `var(--text-muted)`, text color sharpens to `var(--text)`.
- **Ghost Button (`.btn-ghost`):**
  - Matches secondary but spans `width: 100%`.

### Inputs & Textareas
- **Base State:** Background `var(--base)`, Border `var(--border-med)`, Radius `7px` (`--radius-sm`).
- **Focus State:** Border shifts to `var(--accent-dim)`, Box shadow adds an outer glow ring `0 0 0 3px var(--accent-glow)`.

### Surface Cards (`.surface-card`, `.stat-card`)
- **Default:** Background `var(--surface)`, Border `var(--border-med)`, Radius `12px`.
- **Hover Impact:** Transform translate-y up `-2px`, border tightens to `var(--accent-glow-hi)`, faint chartreuse box shadow `0 4px 20px rgba(...)`.
- **Stat Cards Specifics:** Incorporate an invisible left-hand linear gradient bar that fades in on hover.

### Navigation Items (`.nav-item`)
- Color `var(--text-muted)`, generic transparent hover.
- **Active State (`.nav-item.active`):** 
  - Background turns `rgba(200, 249, 81, 0.08)`.
  - Inset stroke `box-shadow: inset 0 0 0 1px rgba(200,249,81,0.10)`.
  - Adds absolute left vertical active bar with drop shadow glow properties.

### Badges & Chips (`.feed-badge`, `.pipeline-chip`)
- Monospaced, `9.5px - 10px`, heavily spaced `0.06em - 0.08em` uppercase type.
- Distinct colorizations based on intent (Success/Liming, Warning, Danger).

---

## 6. Overlays & Modals

### Studio Modal (`.studio-modal`)
- **Overlay:** Extensive background blur `backdrop-filter: blur(20px)` over an 85% opacity `#0a0a0f` background.
- **Container Sizing:** `1100px` max width, `90vh` height.
- **Depth Map:** Uses deep shadow stack `0 24px 60px rgba(0,0,0,0.5)`, internal contour lighting `inset 0 0 0 1px rgba(...)`.

### Pipeline Modal / Synthetic Architect Map (`.pipeline-modal`)
- Uses heavily saturated overlay blurring (`backdrop-filter: blur(28px) saturate(1.3)`).
- Uses stepped visual timelines with `var(--accent)` pulsing spinner rings and CSS gradient connective tissue (`linear-gradient(to bottom, var(--accent), var(--border))`).

## 7. Responsive / Mocked Component Classes (Social Grids)
The application includes extensive structural mimicry for output validation covering:
- **X (Twitter) Mocks (`.mock-x`):** Darker backgrounds (`#000`), grid-based imagery (`.tw-media-grid`).
- **LinkedIn Mocks (`.mock-li`):** `#1b1f23` background spaces.
- **TikTok/YouTube:** Structured 9:16 and 16:9 bounding boxes enforcing object overlays.
