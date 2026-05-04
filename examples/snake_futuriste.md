# TECHNICAL ARCHITECTURE DOCUMENT

## SNYKE — Cyberpunk Snake Game

**Version**: 1.0.0
**Date**: January 2025
**Status**: Finalized

---

## 1. Executive Summary

**SNYKE** is a Snake game reimagined in a cyberpunk/holographic universe, developed in vanilla HTML5/CSS3/JavaScript (ES6+). The player controls a glowing snake composed of segments that leave a neon trail, moving within a futuristic holographic grid.

The application is intended for modern desktop and mobile browsers, featuring a responsive interface and sci-fi visual effects. The architecture is designed to function without external dependencies or build steps, while delivering smooth 60 FPS performance.

**Quality Objectives**:

- Fluid and responsive gameplay
- Consistent cyberpunk aesthetic (neon, glow, scanlines)
- Procedurally generated sounds (Web Audio API)
- Local persistence of scores and settings
- Modular and maintainable code

---

## 2. Architecture Overview

The architecture follows a **modular event-driven** model where the `GameLoop` orchestrates the flow between subsystems. Each module exposes a minimalist public API and communicates via an `EventBus` for decoupling.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SNYKE ENGINE v1.0                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                    │
│  │    INPUT     │──▶│   GAME       │──▶│  RENDERER    │                    │
│  │   HANDLER    │   │    LOOP      │   │   (Canvas)   │                    │
│  │  Keyboard    │   │   60 FPS     │   │              │                    │
│  │    Touch     │   │              │   │              │                    │
│  └──────────────┘   └──────┬───────┘   └──────────────┘                    │
│                            │                                               │
│                            ▼                                               │
│                     ┌──────────────┐                                       │
│                     │    STATE     │◀───────────────────────────────────┐   │
│                     │   MANAGER    │                                    │   │
│                     └──────┬───────┘                                    │   │
│                            │                                           │   │
│         ┌─────────────────┼─────────────────┐                          │   │
│         ▼                 ▼                 ▼                          │   │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐                      │   │
│  │   SCORE    │   │   LEVEL    │   │   AUDIO    │                      │   │
│  │  SERVICE   │   │  SERVICE   │   │  SERVICE   │                      │   │
│  └────────────┘   └────────────┘   └────────────┘                      │   │
│                                                              ▲           │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐      │           │
│  │  PARTICLE   │   │   STORAGE    │   │    MENU      │      │           │
│  │   SYSTEM    │   │  (localStorage)  │   MANAGER    │──────┘           │
│  └──────────────┘   └──────────────┘   └──────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Global Flow

1. **Initialization**: `main.js` orchestrates dependency injection and startup.
2. **Game Loop**: `GameLoop` runs continuously at 60 FPS via `requestAnimationFrame`.
3. **Tick game logic**: Executed at a fixed interval (configurable, default 150ms).
4. **Render**: Executed every frame for display.
5. **Responsive UI**: Screens (menu, HUD, game over) overlay the canvas via CSS layers.

---

## 3. Components & Responsibilities

### 3.1 — Engine Layer (`engine/`)

| Module | Responsibility | Public API | Dependencies |
|--------|---------------|--------------|-------------|
| `GameLoop` | RAF loop 60 FPS, delta time, tick scheduling, pause/resume | `start()`, `stop()`, `pause()`, `resume()`, `isPaused()` | EventBus |
| `StateManager` | State machine (MENU/PLAYING/PAUSED/GAMEOVER), guarded transitions | `setState(state)`, `getState()`, `onTransition(cb)`, `onEnter(state, cb)` | EventBus |
| `InputHandler` | Directional queue (max 2 buffered), anti-180° filtering, touch swipe detection | `getDirection()`, `queueDirection(dir)`, `subscribe(cb)`, `enable()`, `disable()` | Config |
| `Config` | All centralized constants (GRID, SPEED, COLORS) | Exposed members (`GRID_COLS`, `GRID_ROWS`, `TICK_MS`, `COLORS`) | — |

### 3.2 — Game Entities (`entities/`)

| Module | Responsibility | Public API | Internal State |
|--------|---------------|--------------|--------------|
| `Snake` | Segment positions, direction, growth, movement | `move(dir)`, `grow()`, `getHead()`, `getSegments()`, `reset()` | `segments[]`, `direction`, `growPending` |
| `Food` | Position, type, effect, random respawn | `spawn(grid)`, `getPosition()`, `getType()`, `isAt(x, y)` | `position`, `type`, `effect` |
| `Grid` | Logical grid, collision lookup | `isOccupied(x, y)`, `occupy(x, y)`, `release(x, y)`, `isInBounds(x, y)` | Map `x,y → owner` |

### 3.3 — Rendering (`rendering/`)

| Module | Responsibility | Public API | Cost |
|--------|---------------|--------------|------|
| `Renderer` | Frame draw orchestrator, clear, final composite | `render(gameState)`, `init(canvas)`, `resize(w, h)` | — |
| `GridRenderer` | Holographic lines, background | `draw(ctx, time)` | O(GRID) |
| `SnakeRenderer` | Segments, glow, glowing trail | `draw(ctx, snake, time)` | O(SNAKE_LENGTH) |
| `FoodRenderer` | Food sprite, pulse, glow | `draw(ctx, food, time)` | O(1) |
| `ParticleSystem` | 500-particle object pool, burst, gravity | `emit(type, pos)`, `update(dt)`, `render(ctx)`, `clear()` | O(POOL_SIZE) |
| `TrailRenderer` | Gradient trail behind the snake | Integrated in SnakeRenderer | — |
| `GlowRenderer` | Glow filters via radialGradient | Static helpers | — |

### 3.4 — Audio (`audio/`)

| Module | Responsibility | Public API | Technology |
|--------|---------------|--------------|-------------|
| `AudioManager` | Audio Context, master volume, mute | `init()`, `play(sfxName)`, `setVolume(v)`, `mute()`, `unmute()` | Web Audio API |
| `SynthEngine` | Configurable oscillators, ADSR envelopes | `tone(freq, duration, type)`, `noise(duration)`, `sweep(start, end, dur)` | OscillatorNode |
| `sfx/*` | Waveform generating functions | `eat()`, `move()`, `die()`, `levelup()`, `gameover()` | OscillatorNode + GainNode |

### 3.5 — User Interface (`ui/`)

| Module | Responsibility | Public API | Rendering |
|--------|---------------|--------------|-------|
| `MenuScreen` | Animated title, 3 options (Play/Settings/HighScores), navigation | `show()`, `hide()`, `onSelect(cb)` | DOM/CSS |
| `HUD` | Overlay for score, level, speed, timer | `updateScore(s)`, `updateLevel(l)`, `show()`, `hide()` | DOM overlay |
| `GameOverScreen` | Final score, high score comparison, restart | `show(score, isHigh)`, `hide()`, `onRestart(cb)` | DOM |
| `SettingsModal` | Volume slider, speed select, controls remap | `show()`, `hide()`, `onSave(settings)`, `getSettings()` | DOM/CSS |

### 3.6 — Services (`services/`)

| Module | Responsibility | Public API | Persistence |
|--------|---------------|--------------|-------------|
| `ScoreService` | Score addition, multiplier, combo bonus, reset | `add(points)`, `multiply(m)`, `reset()`, `getScore()` | Via StorageService |
| `LevelService` | Level progression → speed, milestones, bonus life | `addScore(s)`, `getLevel()`, `getSpeed()` | Via StorageService |
| `StorageService` | localStorage wrapper, schema validation, defaults | `save(key, data)`, `load(key)`, `clear()` | localStorage |
| `EventBus` | Decoupled pub/sub, event namespaces | `on(event, cb)`, `emit(event, data)`, `off(event, cb)` | — |

### 3.7 — Utilities (`utils/`)

| Module | Responsibility | Functions |
|--------|---------------|-----------|
| `math.js` | Mathematical operations | `clamp(val, min, max)`, `lerp(a, b, t)`, `randInt(min, max)`, `randFloat(min, max)` |
| `time.js` | Time management | `deltaMs(last, now)`, `throttle(fn, ms)`, `debounce(fn, ms)` |
| `dom.js` | DOM helpers | `$qs(selector)`, `$qsa(selector)`, `createEl(tag, attrs)`, `removeEl(el)` |

---

## 4. Technology Stack

| Category | Choice | Version | Justification |
|-----------|-------|---------|---------------|
| **Language** | JavaScript ES6+ | ES2022 | Native modules, optional chaining, nullish coalescing |
| **Style** | CSS3 | — | CSS variables, grid, flexbox, backdrop-filter, animations |
| **Graphics** | Canvas 2D API | — | Excellent 2D performance, no WebGL overhead |
| **Audio** | Web Audio API | — | Procedural synthesis, no audio files to load |
| **Persistence** | localStorage | — | ~5 MB quota, no backend, native JSON |
| **Module system** | ES Modules | — | No mandatory bundler, native import/export |
| **Fonts** | Google Fonts Orbitron | — | Futuristic typography, lazy load |
| **Build** | None (vanilla) | — | Zero dependencies, single executable file |

### Target Browser Compatibility

- Chrome 80+
- Firefox 75+
- Safari 14+
- Edge 80+
- Mobile Chrome / Safari

> ⚠️ **Note**: Browsers must support ES Modules (`<script type="module">`) and Web Audio API. Graceful fallback (mute + message) if unavailable.

---

## 5. Data Flows

### 5.1 — Main Flow (Game Loop)

```
┌──────────────────────────────────────────────────────────────────┐
│                    GAME LOOP — 60 FPS                            │
│                   (requestAnimationFrame)                        │
└──────────────────────────────────────────────────────────────────┘
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
         ┌──────────┐   ┌──────────┐   ┌──────────┐
         │  INPUT   │   │  TICK    │   │  RENDER  │
         │  READ    │   │  LOGIC   │   │  FRAME   │
         └──────────┘   └──────────┘   └──────────┘
               │               │               │
               ▼               ▼               ▼
         DirectionQueue   GameState       Canvas API
         validated (anti- updated         draw calls
         180°) for next  (Snake, Food,    (Grid, Snake,
         tick            Score, Level)    Food, Particles)
                                 │
                                 ▼
                     EventBus.emit() for
                     cross-component events
```

### 5.2 — Event Flow

```
EVENT BUS CHANNELS
════════════════════════════════════════════════════════════════════

  CHANNEL              EMITTER           LISTENERS
  ───────────────────────────────────────────────────────────────
  food.eaten           Snake/Food        ParticleSystem, ScoreService,
                                        AudioManager, HUD

  level.up             LevelService     AudioManager, HUD, Renderer
                                        (speed increase visual)

  game.over            Snake             GameOverScreen, ScoreService,
                                        AudioManager, StorageService

  game.start           StateManager     ParticleSystem (reset),
                                        AudioManager, HUD

  pause.toggle         InputHandler      GameLoop, HUD

  snake.move           Snake             SnakeRenderer

  highscore.new        StorageService    GameOverScreen (highlight)
```

### 5.3 — Collision Flow

```
Input Direction
      │
      ▼
 InputHandler.validate(direction) → directionQueue
      │
      ▼
 Snake.move(direction)
      │
      ├─▶ Grid.isInBounds(head) ──────▶ GAME OVER (Wall)
      │
      ├─▶ Snake.checkSelfCollision() ─▶ GAME OVER (Self)
      │
      └─▶ Grid.isOccupied(head) ──────▶ FOOD EATEN
             │                            │
             │                            ├─▶ Food.spawn()
             │                            ├─▶ ScoreService.add()
             │                            ├─▶ ParticleSystem.emit('burst')
             │                            ├─▶ AudioManager.play('eat')
             │                            └─▶ LevelService.check()
             │
             └─▶ Snake.grow() (if food)
```

### 5.4 — Rendering Flow

```
requestAnimationFrame(timestamp)
      │
      ▼
 Renderer.render(gameState, timestamp)
      │
      ├─▶ ctx.clearRect(0, 0, w, h)
      │
      ├─▶ GridRenderer.drawGrid(ctx, time)
      │       (holographic lines alpha 0.15)
      │
      ├─▶ SnakeRenderer.drawSnake(ctx, snake, time)
      │       ├─ TrailRenderer (gradient globalAlpha)
      │       └─ GlowRenderer (radialGradient on head)
      │
      ├─▶ FoodRenderer.drawFood(ctx, food, time)
      │       (pulse: sin(time) * scale)
      │
      ├─▶ ParticleSystem.render(ctx)
      │       (active particles only)
      │
      └─▶ HUD.updateDOM()
              (DOM update, no canvas)
```

---

## 6. Security

### 6.1 — Threat Model

| Threat | Probability | Impact | Applied Mitigation |
|--------|-------------|--------|----------------------|
| XSS via localStorage | Low | Medium | Whitelisted keys, parse try/catch with defaults |
| Client-side score modification | Medium | Negligible | Single-player only, no server |
| Canvas manipulation | Very low | Negligible | Isolated canvas, no cross-origin iframe |
| CSS injection | Negligible | Low | Styles in CSS file, no dynamic injection |
| Audio autoplay blocked | High | Low | `AudioContext.resume()` on first user gesture |

### 6.2 — Security Policies Applied

```html
<!-- Content Security Policy (Optional, can be enabled) -->
<!-- <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;"> -->

<!-- Audio: No autoplay -->
<script>
  // AudioContext created only on first user interaction
  document.addEventListener('click', () => {
    if (audioCtx && audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
  }, { once: true });
</script>
```

### 6.3 — Data Validation

```javascript
// Schema validation for localStorage
const SCORE_SCHEMA = {
  version: 1,
  scores: Array,  // max 10 entries, sorted descending
  settings: { volume: Number, speed: String, controls: String },
  stats: { gamesPlayed: Number, totalScore: Number, playTimeSeconds: Number }
};

// Validation on load
function loadScores() {
  try {
    const raw = localStorage.getItem('snyke_highscores');
    if (!raw) return DEFAULT_SCORES;
    const parsed = JSON.parse(raw);
    return validateSchema(parsed, SCORE_SCHEMA) ? parsed : DEFAULT_SCORES;
  } catch (e) {
    return DEFAULT_SCORES;
  }
}
```

### 6.4 — Secure Event Handling

```javascript
// Delegation only on known element
const container = document.getElementById('game-container');
container.addEventListener('keydown', handleKeyDown);

// No dynamic event listeners on window/document
// Except for global shortcuts (Escape = pause)
```

---

## 7. Scalability & Performance

### 7.1 — Performance Metrics

| Metric | Target | Critical Threshold | Strategy |
|----------|-------|----------------|-----------|
| FPS | 60 | < 50 | Reduce particles, skip frame |
| Input Latency | < 16ms | > 50ms | RAF scheduling, no heavy work in input handler |
| Tick time | < 5ms | > 20ms | O(1) algorithms for collision |
| Memory | < 30 MB | > 50 MB | Object pool, cleanup on game over |
| Bundle size | < 100 KB | — | ES modules, lazy loading screens |
| localStorage I/O | < 10ms | > 100ms | Batch writes, debounce saves |

### 7.2 — Implemented Optimizations

**Object Pooling (particles)**
```javascript
class ParticlePool {
  constructor(size = 500) {
    this.pool = Array.from({ length: size }, () => this.createParticle());
    this.active = new Set();
  }

  acquire() {
    const particle = this.pool.find(p => !p.active);
    if (particle) {
      particle.active = true;
      this.active.add(particle);
    }
    return particle;
  }

  release(particle) {
    particle.active = false;
    this.active.delete(particle);
  }
  // Reuse, no new/GC
}
```

**O(1) Collision via Grid Map**
```javascript
// Grid.isOccupied(x, y) — Map lookup instead of array scan
this.grid = new Map();
// Key: "x,y" → value: "snake" | "food"
isOccupied(x, y) {
  return this.grid.has(`${x},${y}`);
}
```

**Dirty Checking (Snake segments)**
```javascript
// Only redraw if state changed
let lastRenderState = null;
function render(state) {
  if (JSON.stringify(state) === lastRenderState) return;
  // draw...
  lastRenderState = JSON.stringify(state);
}
```

**Adaptive particle count**
```javascript
const MAX_PARTICLES = window.innerWidth < 768 ? 200 : 500;
```

### 7.3 — Responsive Design

| Viewport | Canvas | Grid | Particles | Touch |
|----------|--------|------|-----------|-------|
| ≥ 1024px | 800×500 | 40×25 | 500 | No |
| 768–1023px | 640×400 | 32×20 | 300 | No |
| < 768px | 100vw–20px | 24×15 | 200 | Yes (swipe) |

### 7.4 — Future Extensibility

```
POSSIBLE ADDITIONS WITHOUT REFACTOR
═══════════════════════════════════

Power-ups:
  ├── Module: PowerUp.js
  ├── Rendering: PowerUpRenderer.js
  ├── Service: PowerUpService.js
  └── EventBus: powerup.spawn, powerup.collect

Local Multiplayer:
  ├── Module: Snake2.js (2nd snake)
  ├── InputHandler: dual queue
  └── Renderer: multi-snake

Online Multiplayer:
  ├── Module: NetworkManager.js (WebSocket)
  ├── API: sync state every tick
  └── Conflict resolution: server authority

Themes:
  ├── css/variables-themes.css
  ├── Constants: Config.THEME
  └── Loader: ThemeManager.load(themeName)
```

---

## 8. Project Structure

```
snyke/
│
├── index.html                    # Single entry point
│   ├── <meta> tags (viewport, description)
│   ├── Google Fonts (Orbitron)
│   ├── <link> styles.css
│   └── <script type="module" src="js/main.js">
│
├── css/
│   │
│   ├── main.css                 # Reset, CSS variables, global layout
│   │   ├── /* Variables: --color-primary, --glow-intensity, etc. */
│   │   ├── /* Reset: box-sizing, margin 0 */
│   │   └── /* Layout: #game-container, layers */
│   │
│   ├── components/
│   │   ├── menu.css              # .menu-screen, .menu-title, .menu-options
│   │   ├── hud.css               # .hud, .hud-score, .hud-level
│   │   ├── modal.css             # .modal, .modal-content, .settings-group
│   │   └── gameover.css          # .gameover-screen, .final-score, .highscore-badge
│   │
│   └── effects/
│       ├── scanlines.css         # .scanlines-overlay (::after pseudo)
│       ├── glow.css              # .neon-glow, .text-glow (CSS fallback)
│       └── transitions.css       # .fade-in, .slide-up (animations)
│
├── js/
│   │
│   ├── main.js                   # Bootstrap: init modules, start game loop
│   │
│   ├── engine/
│   │   ├── GameLoop.js           # RAF loop, tick scheduling, pause/resume
│   │   ├── StateManager.js       # FSM: MENU → PLAYING → PAUSED/GAMEOVER
│   │   ├── InputHandler.js       # Keyboard + Touch, direction queue
│   │   └── Config.js             # Constants: GRID_SIZE, SPEED, COLORS, AUDIO
│   │
│   ├── entities/
│   │   ├── Snake.js              # Segments[], move(), grow(), collision()
│   │   ├── Food.js               # Position, type, effect, spawn()
│   │   └── Grid.js               # Grid Map, isOccupied(), isInBounds()
│   │
│   ├── rendering/
│   │   ├── Renderer.js           # Orchestrator: clear → draw → composite
│   │   ├── GridRenderer.js       # Holographic lines
│   │   ├── SnakeRenderer.js      # Segments + trail + glow
│   │   ├── FoodRenderer.js       # Pulse + glow
│   │   ├── ParticleSystem.js     # 500-particle object pool, emit(), update(), render()
│   │   └── effects/
│   │       ├── GlowRenderer.js   # radialGradient helpers
│   │       └── TrailRenderer.js  # alpha gradient trail
│   │
│   ├── audio/
│   │   ├── AudioManager.js       # Web Audio init, play(), volume, mute
│   │   ├── SynthEngine.js        # tone(), noise(), sweep() generators
│   │   └── sfx/
│   │       ├── eat.js            # "nom" sound: 440Hz + harmonics + decay
│   │       ├── move.js          # low buzz
│   │       ├── die.js           # descending sweep + noise burst
│   │       ├── levelup.js       # ascending arpeggio
│   │       └── gameover.js      # low drone + fade
│   │
│   ├── ui/
│   │   ├── MenuScreen.js        # show(), hide(), onSelect(option)
│   │   ├── HUD.js               # updateScore(), updateLevel(), DOM refs
│   │   ├── GameOverScreen.js    # show(score), showHighScore(), onRestart()
│   │   └── SettingsModal.js     # show(), hide(), onSave(settings), sliders
│   │
│   ├── services/
│   │   ├── ScoreService.js      # add(), multiply(), reset(), getScore()
│   │   ├── LevelService.js      # check(), getLevel(), getSpeed(), SPEED_TABLE
│   │   ├── StorageService.js    # save(), load(), clear(), VALID_KEYS
│   │   └── EventBus.js          # on(), emit(), off(), _listeners Map
│   │
│   └── utils/
│       ├── math.js              # clamp(), lerp(), randInt(), randFloat(), ease()
│       ├── time.js              # deltaMs(), throttle(), debounce()
│       └── dom.js               # $qs(), $qsa(), createEl(), removeEl()
│
├── assets/
│   ├── fonts/                   # (Optional) Local Orbitron .woff2
│   └── icons/
│       └── favicon.svg          # Futuristic snake icon
│
├── SPEC.md                      # Detailed functional specification
├── CHANGELOG.md                # Version history
└── README.md                   # Installation / Development guide
```

### Import Tree

```
main.js
├── Config.js
├── EventBus.js
├── StorageService.js
├── AudioManager.js
│   └── SynthEngine.js
│       └── sfx/*.js
├── StateManager.js
│   └── EventBus.js
├── GameLoop.js
│   ├── Config.js
│   ├── EventBus.js
│   └── StateManager.js
├── InputHandler.js
│   ├── Config.js
│   └── EventBus.js
├── Snake.js
│   ├── Grid.js
│   └── EventBus.js
├── Food.js
│   └── Grid.js
├── Grid.js
├── ScoreService.js
│   ├── EventBus.js
│   └── StorageService.js
├── LevelService.js
│   ├── EventBus.js
│   └── Config.js
├── Renderer.js
│   ├── GridRenderer.js
│   ├── SnakeRenderer.js
│   │   ├── effects/GlowRenderer.js
│   │   └── effects/TrailRenderer.js
│   ├── FoodRenderer.js
│   └── ParticleSystem.js
├── MenuScreen.js
├── HUD.js
├── GameOverScreen.js
│   └── StorageService.js
└── SettingsModal.js
    └── StorageService.js
```

---

## 9. Implementation Roadmap

### Sprint 1 — Core Engine (Days 1-2)

**Objective**: Minimal functional playable prototype

| Task | Description | Success Criteria |
|-------|-------------|-------------------|
| 1.1 | Project setup + index.html + global CSS | Single executable file |
| 1.2 | GameLoop + Config | `requestAnimationFrame` runs, pause working |
| 1.3 | StateManager | Correct FSM transitions (MENU→PLAYING→GAMEOVER) |
| 1.4 | Grid + basic Snake | Snake moves, does not exit walls (or wraps) |
| 1.5 | Food spawn + eat collision | Score increases, snake grows |
| 1.6 | InputHandler (keyboard) | Arrow keys functional |
| 1.7 | Basic HUD | Score displayed in overlay |

**Deliverable**: Playable `index.html` with increasing score

### Sprint 2 — Rendering (Days 3-4)

**Objective**: Full cyberpunk visual on Canvas

| Task | Description | Success Criteria |
|-------|-------------|-------------------|
| 2.1 | GridRenderer | Holographic lines visible (alpha 0.15) |
| 2.2 | SnakeRenderer | Segments + head glow + trail |
| 2.3 | FoodRenderer | Pulse animation + glow |
| 2.4 | ParticleSystem | Burst on eating food (pool 500) |
| 2.5 | Responsive canvas | Working resize handler |
| 2.6 | Scanlines effect | CSS scanlines overlay |

**Deliverable**: Canvas rendered with all visual effects

### Sprint 3 — Audio & Effects (Days 5-6)

**Objective**: Full audio feedback + effect polish

| Task | Description | Success Criteria |
|-------|-------------|-------------------|
| 3.1 | AudioManager init | AudioContext created on first click |
| 3.2 | SFX eat/move/die/levelup | Playable procedural sounds |
| 3.3 | Screen shake | Shake on collision (wall or self) |
| 3.4 | Screen flash | White flash on eating food |
| 3.5 | LevelService | Speed increases at each milestone |
| 3.6 | Speed scaling | TICK_MS decreases by 10% per level |

**Deliverable**: Full audio-visual feedback

### Sprint 4 — UI & Polish (Days 7-8)

**Objective**: Full UI + mobile + scores

| Task | Description | Success Criteria |
|-------|-------------|-------------------|
| 4.1 | MenuScreen | Animated title + 3 options + navigation |
| 4.2 | GameOverScreen | Final score + high score + restart |
| 4.3 | SettingsModal | Volume slider + speed select |
| 4.4 | Touch controls | Swipe detection for mobile |
| 4.5 | localStorage high scores | Working save/load |
| 4.6 | Stats tracking | gamesPlayed, playTime, totalScore |
| 4.7 | Performance audit | Stable 60 FPS, memory < 30MB |

**Deliverable**: Production-ready version

### Total Effort Estimate

| Phase | Complexity | Estimated Time |
|-------|------------|--------------|
| Sprint 1 | ★★☆ | ~6 hours |
| Sprint 2 | ★★★ | ~8 hours |
| Sprint 3 | ★★☆ | ~5 hours |
| Sprint 4 | ★★☆ | ~6 hours |
| **Total** | | **~25 hours** |

---

## 10. Attention Points & Risks

### 10.1 — Identified Risks

| ID | Risk | Probability | Impact | Mitigation |
|----|--------|-------------|--------|------------|
| R1 | **Mobile Canvas performance** | Medium | Medium | Reduced particle pool on mobile (200), dirty checking |
| R2 | **Browsers audio autoplay** | High | Low | `AudioContext.resume()` on first click, automatic mute fallback |
| R3 | **localStorage quota exceeded** | Low | Medium | Validation before writing, cleanup of old scores |
| R4 | **Long session memory leak** | Medium | Medium | Object pool reset at game over, no orphaned listeners |
| R5 | **High scores input lag** | Low | Low | Buffered direction queue, anti-180° already implemented |
| R6 | **Touch controls confusion** | Medium | Medium | Visual instructions on mobile, haptic feedback |
| R7 | **Cross-origin fonts blocked** | Low | Low | System fallback if Google Fonts unreachable |

### 10.2 — Development Watch Points

**Performance**

- Never create objects in the game loop hot path (pre-allocation)
- Pooling is mandatory for particles (500 max)
- Collision lookup via Map, no array scan `includes()`

**Audio**

- Test on various browsers (Safari sometimes has Web Audio quirks)
- Provide silent fallback if `AudioContext` not supported
- Handle cases where user mutes via system shortcuts

**Responsive**

- Test on 320px minimum viewport
- Canvas resize must preserve game state
- Touch controls must not interfere with natural scroll

**Persistence**

- Schema versioning for future migrations
- Systematic validation of data read from localStorage
- Provide CSV export/import for score transfer

### 10.3 — Definitions

| Term | Definition |
|-------|-----------|
| **Tick** | A cycle of game logic (snake movement, collision) executed at a fixed interval |
| **Frame** | A rendering iteration (RAF) at 60 FPS |
| **Dirty checking** | Detecting state change before rendering |
| **Object pool** | Pre-allocation of reusable objects to avoid GC allocation |

### 10.4 — Quality Release Checklist

```
PRE-RELEASE CHECKLIST
══════════════════════

FUNCTIONALITY
  □ Snake moves in 4 directions
  □ Wall collision → game over
  □ Self collision → game over
  □ Consuming food → score +1, snake +1 segment
  □ Level up every N points → speed increase
  □ Game over → screen + restart

VISUAL
  □ Holographic grid visible
  □ Neon glow on snake (head + body)
  □ Gradient trail behind snake
  □ Pulse on food
  □ Particle burst when consuming food
  □ Scanlines overlay
  □ Screen shake at game over

AUDIO
  □ SFX eat playable
  □ SFX die playable
  □ SFX levelup playable
  □ Volume adjustable
  □ Mute functional

UI
  □ Menu screen with animated title
  □ HUD score/level visible during game
  □ Game over screen with restart
  □ High scores saved
  □ Settings modal functional

RESPONSIVE
  □ Desktop (1024px+) : canvas 800×500
  □ Tablet (768px) : canvas 640×400
  □ Mobile (< 768px) : fullwidth canvas + touch controls
  □ Keyboard functional on desktop
  □ Touch/swipe functional on mobile

PERFORMANCE
  □ Stable 60 FPS on desktop
  □ Stable 30+ FPS on mobile
  □ Memory < 30 MB
  □ No console errors
  □ No memory leak after 10 games

COMPATIBILITY
  □ Chrome 80+
  □ Firefox 75+
  □ Safari 14+
  □ Edge 80+
  □ Mobile Chrome / Safari
```

---

## 11. Appendices

### A — CSS Variables (snippet)

```css
:root {
  /* Colors */
  --color-bg: #0a0a12;
  --color-primary: #00ff88;
  --color-secondary: #00b4d8;
  --color-accent: #ff006e;
  --color-warning: #ffbe0b;
  --color-text: #e0e0e0;

  /* Glow */
  --glow-intensity: 0 0 10px var(--color-primary),
                    0 0 20px var(--color-primary),
                    0 0 40px var(--color-primary);
  --glow-soft: 0 0 5px var(--color-primary),
               0 0 10px var(--color-primary);

  /* Fonts */
  --font-main: 'Orbitron', 'Courier New', monospace;
  --font-size-base: 16px;
  --font-size-lg: 24px;
  --font-size-xl: 48px;
  --font-size-xxl: 72px;
}
```

### B — Progression Table (LevelService)

```javascript
const SPEED_TABLE = [
  { level: 1,  minScore: 0,    tickMs: 150, label: 'INIT' },
  { level: 2,  minScore: 50,   tickMs: 135, label: 'SLOW' },
  { level: 3,  minScore: 100,  tickMs: 120, label: 'MEDIUM' },
  { level: 4,  minScore: 200,  tickMs: 105, label: 'FAST' },
  { level: 5,  minScore: 400,  tickMs: 90,  label: 'INSANE' }
];
```
