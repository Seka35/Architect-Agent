
# DOCUMENT D'ARCHITECTURE TECHNIQUE

## SNYKE — Jeu Snake Cyberpunk

**Version** : 1.0.0
**Date** : Janvier 2025
**Statut** : Finalisé

---

## 1. Résumé Exécutif

**SNYKE** est un jeu Snake reimaginé dans un univers cyberpunk/holographique, développé en HTML5/CSS3/JavaScript vanilla (ES6+). Le joueur contrôle un serpent lumineux composed de segments qui laissent une traînée néon, evoluant dans une grille holographique futuriste.

L'application se destine aux navigateurs modernes sur desktop et mobile, avec une interface réactive et des effets visuels de type sci-fi. L'architecture est conçue pour fonctionner sans dépendances externes ni étape de build, tout en offrant des performances fluides à 60 FPS.

**Objectifs qualité** :

- Jouabilité fluide et responsive
- Esthétique cyberpunk cohérente (néon, glow, scanlines)
- Sons générés procéduralement (Web Audio API)
- Persistance locale des scores et paramètres
- Code modulaire et maintenable

---

## 2. Vue d'Architecture

L'architecture suit un modèle **事件驱动 modulaire** où le `GameLoop` orchestre le flux entre les subsystems. Chaque module expose une API publique minimaliste et communique via un `EventBus` pour le découplage.

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

### Flux global

1. **Initialisation** : `main.js` orchestre l'injection des dépendances et le démarrage
2. **Boucle de jeu** : `GameLoop` tourne en permanence à 60 FPS via `requestAnimationFrame`
3. **Tick game logic** : exécuté à intervalle fixe (configurable, défaut 150ms)
4. **Render** : exécuté à chaque frame pour l'affichage
5. **UI réactive** : les screens (menu, HUD, game over) se superposent au canvas via des couches CSS

---

## 3. Composants & Responsabilités

### 3.1 — Couche Moteur (`engine/`)

| Module | Responsabilité | API publique | Dépendances |
|--------|---------------|--------------|-------------|
| `GameLoop` | RAF loop 60 FPS, delta time, tick scheduling, pause/resume | `start()`, `stop()`, `pause()`, `resume()`, `isPaused()` | EventBus |
| `StateManager` | Machine à états (MENU/PLAYING/PAUSED/GAMEOVER), transitions guardées | `setState(state)`, `getState()`, `onTransition(cb)`, `onEnter(state, cb)` | EventBus |
| `InputHandler` | Queue directionnelle (max 2 buffered), filtrage anti-180°, touch swipe detection | `getDirection()`, `queueDirection(dir)`, `subscribe(cb)`, `enable()`, `disable()` | Config |
| `Config` | Toutes constantes centralisées (GRID, SPEED, COLORS) | Membres exposés (`GRID_COLS`, `GRID_ROWS`, `TICK_MS`, `COLORS`) | — |

### 3.2 — Entités de jeu (`entities/`)

| Module | Responsabilité | API publique | État interne |
|--------|---------------|--------------|--------------|
| `Snake` | Position segments, direction, croissance, mouvement | `move(dir)`, `grow()`, `getHead()`, `getSegments()`, `reset()` | `segments[]`, `direction`, `growPending` |
| `Food` | Position, type, effet, respawn aléatoire | `spawn(grid)`, `getPosition()`, `getType()`, `isAt(x, y)` | `position`, `type`, `effect` |
| `Grid` | Grille logique, collision lookup | `isOccupied(x, y)`, `occupy(x, y)`, `release(x, y)`, `isInBounds(x, y)` | Map `x,y → owner` |

### 3.3 — Rendu (`rendering/`)

| Module | Responsabilité | API publique | Coût |
|--------|---------------|--------------|------|
| `Renderer` | Orchestrateur draw frame, clear, composite final | `render(gameState)`, `init(canvas)`, `resize(w, h)` | — |
| `GridRenderer` | Lignes holographiques, background | `draw(ctx, time)` | O(GRID) |
| `SnakeRenderer` | Segments, glow, trail lumineux | `draw(ctx, snake, time)` | O(SNAKE_LENGTH) |
| `FoodRenderer` | Sprite nourriture, pulse, glow | `draw(ctx, food, time)` | O(1) |
| `ParticleSystem` | Object pool 500 particules, burst, gravity | `emit(type, pos)`, `update(dt)`, `render(ctx)`, `clear()` | O(POOL_SIZE) |
| `TrailRenderer` | Traînée dégradée derrière le serpent | Intégré dans SnakeRenderer | — |
| `GlowRenderer` | Filtres glow via radialGradient | Helpers statiques | — |

### 3.4 — Audio (`audio/`)

| Module | Responsabilité | API publique | Technologie |
|--------|---------------|--------------|-------------|
| `AudioManager` | Contexte Audio, master volume, mute | `init()`, `play(sfxName)`, `setVolume(v)`, `mute()`, `unmute()` | Web Audio API |
| `SynthEngine` | Oscillateurs configurables, envelopes ADSR | `tone(freq, duration, type)`, `noise(duration)`, `sweep(start, end, dur)` | OscillatorNode |
| `sfx/*` | Fonctions génératrices de waveforms | `eat()`, `move()`, `die()`, `levelup()`, `gameover()` | OscillatorNode + GainNode |

### 3.5 — Interface utilisateur (`ui/`)

| Module | Responsabilité | API publique | Rendu |
|--------|---------------|--------------|-------|
| `MenuScreen` | Titre animé, 3 options (Play/Settings/HighScores), navigation | `show()`, `hide()`, `onSelect(cb)` | DOM/CSS |
| `HUD` | Overlay score, niveau, vitesse, timer | `updateScore(s)`, `updateLevel(l)`, `show()`, `hide()` | DOM overlay |
| `GameOverScreen` | Score final, high score comparison, restart | `show(score, isHigh)`, `hide()`, `onRestart(cb)` | DOM |
| `SettingsModal` | Volume slider, speed select, controls remap | `show()`, `hide()`, `onSave(settings)`, `getSettings()` | DOM/CSS |

### 3.6 — Services (`services/`)

| Module | Responsabilité | API publique | Persistance |
|--------|---------------|--------------|-------------|
| `ScoreService` | Ajout score, multiplier, combo bonus, reset | `add(points)`, `multiply(m)`, `reset()`, `getScore()` | Via StorageService |
| `LevelService` | Progression level→speed, paliers, bonus life | `addScore(s)`, `getLevel()`, `getSpeed()` | Via StorageService |
| `StorageService` | Wrapper localStorage, schema validation, defaults | `save(key, data)`, `load(key)`, `clear()` | localStorage |
| `EventBus` | Pub/sub découplé, namespaces d'événements | `on(event, cb)`, `emit(event, data)`, `off(event, cb)` | — |

### 3.7 — Utilitaires (`utils/`)

| Module | Responsabilité | Fonctions |
|--------|---------------|-----------|
| `math.js` | Opérations mathématiques | `clamp(val, min, max)`, `lerp(a, b, t)`, `randInt(min, max)`, `randFloat(min, max)` |
| `time.js` | Gestion temporelle | `deltaMs(last, now)`, `throttle(fn, ms)`, `debounce(fn, ms)` |
| `dom.js` | Helpers DOM | `$qs(selector)`, `$qsa(selector)`, `createEl(tag, attrs)`, `removeEl(el)` |

---

## 4. Stack Technologique

| Catégorie | Choix | Version | Justification |
|-----------|-------|---------|---------------|
| **Langage** | JavaScript ES6+ | ES2022 | Modules natifs, optional chaining, nullish coalescing |
| **Style** | CSS3 | — | Variables CSS, grid, flexbox, backdrop-filter, animations |
| **Graphisme** | Canvas 2D API | — | Performances 2D excellentes, pas de WebGL overhead |
| **Audio** | Web Audio API | — | Synthèse procédurale, pas de fichiers audio à charger |
| **Persistance** | localStorage | — | Quota ~5 MB, pas de backend, JSON natif |
| **Module system** | ES Modules | — | Pas de bundler obligatoire, import/export natif |
| **Fonts** | Google Fonts Orbitron | — | Typographie futuriste, lazy load |
| **Build** | Aucun (vanilla) | — | Zéro dépendances, fichier unique exécutable |

### Compatibilité navigateur cible

- Chrome 80+
- Firefox 75+
- Safari 14+
- Edge 80+
- Mobile Chrome / Safari

> ⚠️ **Note** : Les navigateurs doivent supporter ES Modules (`<script type="module">`) et Web Audio API. Fallback gracieux (mute + message) si non disponible.

---

## 5. Flux de Données

### 5.1 — Flux principal (boucle de jeu)

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
        validée (anti-   mis à jour      draw calls
        180°) pour le    (Snake, Food,   (Grid, Snake,
        prochain tick     Score, Level)   Food, Particles)
                                │
                                ▼
                    EventBus.emit() pour les
                    events cross-composants
```

### 5.2 — Flux des événements

```
EVENT BUS CHANNELS
════════════════════════════════════════════════════════════════════

  CHANNEL              EMITTEUR          LISTENERS
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

### 5.3 — Flux de collision

```
Input Direction
      │
      ▼
 InputHandler.validate(direction) → directionQueue
      │
      ▼
 Snake.move(direction)
      │
      ├─▶ Grid.isInBounds(head) ──────▶ GAME OVER (mur)
      │
      ├─▶ Snake.checkSelfCollision() ─▶ GAME OVER (self)
      │
      └─▶ Grid.isOccupied(head) ──────▶ FOOD EATEN
             │                            │
             │                            ├─▶ Food.spawn()
             │                            ├─▶ ScoreService.add()
             │                            ├─▶ ParticleSystem.emit('burst')
             │                            ├─▶ AudioManager.play('eat')
             │                            └─▶ LevelService.check()
             │
             └─▶ Snake.grow() (si food)
```

### 5.4 — Flux de rendu

```
requestAnimationFrame(timestamp)
      │
      ▼
 Renderer.render(gameState, timestamp)
      │
      ├─▶ ctx.clearRect(0, 0, w, h)
      │
      ├─▶ GridRenderer.drawGrid(ctx, time)
      │       (lignes holographiques alpha 0.15)
      │
      ├─▶ SnakeRenderer.drawSnake(ctx, snake, time)
      │       ├─ TrailRenderer (globalAlpha dégradé)
      │       └─ GlowRenderer (radialGradient sur head)
      │
      ├─▶ FoodRenderer.drawFood(ctx, food, time)
      │       (pulse: sin(time) * scale)
      │
      ├─▶ ParticleSystem.render(ctx)
      │       (particules actives uniquement)
      │
      └─▶ HUD.updateDOM()
              (DOM update, pas de canvas)
```

---

## 6. Sécurité

### 6.1 — Modèle de menaces

| Menace | Probabilité | Impact | Mitigation appliquée |
|--------|-------------|--------|----------------------|
| XSS via localStorage | Faible | Moyen | Clés whitelistées, parse try/catch avec defaults |
| Modification scores côté client | Moyenne | Négligeable | Scores solo only, pas de serveur |
| canvas manipulation | Très faible | Négligeable | Canvas isolé, pas d'iframe cross-origin |
| CSS injection | Négligeable | Faible | Styles en fichier CSS, pas d'injection dynamic |
| Audio autoplay bloqué | Haute | Faible | `AudioContext.resume()` au premier user gesture |

### 6.2 — Politiques de sécurité appliquées

```html
<!-- Content Security Policy (optionnel, peut être activé) -->
<!-- <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;"> -->

<!-- Audio : pas d'autoplay -->
<script>
  // AudioContext créé au premier user interaction uniquement
  document.addEventListener('click', () => {
    if (audioCtx && audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
  }, { once: true });
</script>
```

### 6.3 — Validation des données

```javascript
// Schema validation pour localStorage
const SCORE_SCHEMA = {
  version: 1,
  scores: Array,  // max 10 entrées, triées descendantes
  settings: { volume: Number, speed: String, controls: String },
  stats: { gamesPlayed: Number, totalScore: Number, playTimeSeconds: Number }
};

// Validation au chargement
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

### 6.4 — Event handling sécurisé

```javascript
// Delegation sur élément connu uniquement
const container = document.getElementById('game-container');
container.addEventListener('keydown', handleKeyDown);

// Pas d'event listener dynamique sur window/document
// Sauf pour les shortcuts globaux (Escape = pause)
```

---

## 7. Scalabilité & Performance

### 7.1 — Métriques de performance

| Métrique | Cible | Seuil critique | Stratégie |
|----------|-------|----------------|-----------|
| FPS | 60 | < 50 | Reduce particles, skip frame |
| Latence input | < 16ms | > 50ms | RAF scheduling, no heavy work in input handler |
| Tick time | < 5ms | > 20ms | Algorithmes O(1) pour collision |
| Memory | < 30 MB | > 50 MB | Object pool, cleanup on game over |
| Bundle size | < 100 KB | — | ES modules, lazy loading screens |
| localStorage I/O | < 10ms | > 100ms | Batch writes, debounce saves |

### 7.2 — Optimisations implémentées

**Object Pooling (particules)**
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
  // Réutilisation, pas de new/GC
}
```

**Collision O(1) via Grid Map**
```javascript
// Grid.isOccupied(x, y) — Map lookup au lieu de array scan
this.grid = new Map();
// Clé: "x,y" → valeur: "snake" | "food"
isOccupied(x, y) {
  return this.grid.has(`${x},${y}`);
}
```

**Dirty checking (Snake segments)**
```javascript
// Ne redessine que si l'état a changé
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

### 7.3 — Responsive design

| Viewport | Canvas | Grid | Particles | Touch |
|----------|--------|------|-----------|-------|
| ≥ 1024px | 800×500 | 40×25 | 500 | Non |
| 768–1023px | 640×400 | 32×20 | 300 | Non |
| < 768px | 100vw–20px | 24×15 | 200 | Oui (swipe) |

### 7.4 — Extensibilité future

```
AJOUTS POSSIBLES SANS REFONTE
═══════════════════════════════

Power-ups:
  ├── Module: PowerUp.js
  ├── Rendu: PowerUpRenderer.js
  ├── Service: PowerUpService.js
  └── EventBus: powerup.spawn, powerup.collect

Multiplayer local:
  ├── Module: Snake2.js (2e serpent)
  ├── InputHandler: dual queue
  └── Renderer: multi-snake

Multiplayer online:
  ├── Module: NetworkManager.js (WebSocket)
  ├── API: sync state every tick
  └── Conflict resolution: server authority

Themes:
  ├── css/variables-themes.css
  ├── Constantes: Config.THEME
  └── Loader: ThemeManager.load(themeName)
```

---

## 8. Structure du Projet

```
snyke/
│
├── index.html                    # Point d'entrée unique
│   ├── <meta> tags (viewport, description)
│   ├── Google Fonts (Orbitron)
│   ├── <link> styles.css
│   └── <script type="module" src="js/main.js">
│
├── css/
│   │
│   ├── main.css                 # Reset, variables CSS, layout global
│   │   ├── /* Variables : --color-primary, --glow-intensity, etc. */
│   │   ├── /* Reset : box-sizing, margin 0 */
│   │   └── /* Layout : #game-container, layers */
│   │
│   ├── components/
│   │   ├── menu.css              # .menu-screen, .menu-title, .menu-options
│   │   ├── hud.css               # .hud, .hud-score, .hud-level
│   │   ├── modal.css             # .modal, .modal-content, .settings-group
│   │   └── gameover.css          # .gameover-screen, .final-score, .highscore-badge
│   │
│   └── effects/
│       ├── scanlines.css         # .scanlines-overlay (::after pseudo)
│       ├── glow.css              # .neon-glow, .text-glow (fallback CSS)
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
│   │   └── Config.js             # Constantes: GRID_SIZE, SPEED, COLORS, AUDIO
│   │
│   ├── entities/
│   │   ├── Snake.js              # Segments[], move(), grow(), collision()
│   │   ├── Food.js               # Position, type, effect, spawn()
│   │   └── Grid.js               # Grid Map, isOccupied(), isInBounds()
│   │
│   ├── rendering/
│   │   ├── Renderer.js           # Orchestrateur: clear → draw → composite
│   │   ├── GridRenderer.js       # Lignes holographiques
│   │   ├── SnakeRenderer.js      # Segments + trail + glow
│   │   ├── FoodRenderer.js       # Pulse + glow
│   │   ├── ParticleSystem.js     # Object pool 500, emit(), update(), render()
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
│   ├── fonts/                   # (optionnel) Orbitron .woff2 local
│   └── icons/
│       └── favicon.svg          # Icône snake futuriste
│
├── SPEC.md                      # Spécification fonctionnelle détaillée
├── CHANGELOG.md                # Historique des versions
└── README.md                   # Guide d'installation / développement
```

### Arbre des imports

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

## 9. Roadmap d'Implémentation

### Sprint 1 — Core Engine (Jours 1-2)

**Objectif** : Prototype fonctionnel minimal jouable

| Tâche | Description | Critère de succès |
|-------|-------------|-------------------|
| 1.1 | Setup projet + index.html + CSS global | Fichier unique exécutable |
| 1.2 | GameLoop + Config | `requestAnimationFrame` tourne, pause fonctionnelle |
| 1.3 | StateManager | FSM transitions correctes (MENU→PLAYING→GAMEOVER) |
| 1.4 | Grid + Snake basique | Serpent bouge, ne sort pas des murs (ou wrap) |
| 1.5 | Food spawn + collision eat | Score augmente, serpent grandit |
| 1.6 | InputHandler (keyboard) | Flèches directionnelles fonctionnelles |
| 1.7 | HUD basique | Score affiché en overlay |

**Deliverable** : `index.html` jouable avec score qui augmente

### Sprint 2 — Rendering (Jours 3-4)

**Objectif** : Visuel cyberpunk complet sur Canvas

| Tâche | Description | Critère de succès |
|-------|-------------|-------------------|
| 2.1 | GridRenderer | Lignes holographiques visibles (alpha 0.15) |
| 2.2 | SnakeRenderer | Segments + glow tête + trail |
| 2.3 | FoodRenderer | Pulse animation + glow |
| 2.4 | ParticleSystem | Burst au makan food (pool 500) |
| 2.5 | Responsive canvas | Resize handler fonctionnel |
| 2.6 | Scanlines effect | Overlay CSS scanlines |

**Deliverable** : Canvas rendu avec tous les effets visuels

### Sprint 3 — Audio & Effects (Jours 5-6)

**Objectif** : Feedback audio complet + polish effets

| Tâche | Description | Critère de succès |
|-------|-------------|-------------------|
| 3.1 | AudioManager init | AudioContext créé au premier click |
| 3.2 | SFX eat/move/die/levelup | Sons procéduraux jouables |
| 3.3 | Screen shake | Shake sur collision (mur ou self) |
| 3.4 | Screen flash | Flash blanc sur makan food |
| 3.5 | LevelService | Vitesse augmente à chaque palier |
| 3.6 | Speed scaling | TICK_MS diminue de 10% par level |

**Deliverable** : Feedback audio-visuel complet

### Sprint 4 — UI & Polish (Jours 7-8)

**Objectif** : UI complète + mobile + scores

| Tâche | Description | Critère de succès |
|-------|-------------|-------------------|
| 4.1 | MenuScreen | Titre animé + 3 options + navigation |
| 4.2 | GameOverScreen | Score final + high score + restart |
| 4.3 | SettingsModal | Volume slider + speed select |
| 4.4 | Touch controls | Swipe detection pour mobile |
| 4.5 | High scores localStorage | Sauvegarde/chargement fonctionnel |
| 4.6 | Stats tracking | gamesPlayed, playTime, totalScore |
| 4.7 | Performance audit | 60 FPS stable, memory < 30MB |

**Deliverable** : Version production-ready

### Estimation effort total

| Phase | Complexité | Temps estimé |
|-------|------------|--------------|
| Sprint 1 | ★★☆ | ~6 heures |
| Sprint 2 | ★★★ | ~8 heures |
| Sprint 3 | ★★☆ | ~5 heures |
| Sprint 4 | ★★☆ | ~6 heures |
| **Total** | | **~25 heures** |

---

## 10. Points d'Attention & Risques

### 10.1 — Risques identifiés

| ID | Risque | Probabilité | Impact | Mitigation |
|----|--------|-------------|--------|------------|
| R1 | **Canvas performance mobile** | Moyenne | Moyen | Particle pool réduit sur mobile (200), dirty checking |
| R2 | **Audio autoplay browsers** | Haute | Faible | `AudioContext.resume()` au premier click, fallback mute automatique |
| R3 | **localStorage quota exceeded** | Basse | Moyen | Validation avant écriture, cleanup des vieux scores |
| R4 | **Memory leak long sessions** | Moyenne | Moyen | Object pool reset au game over, pas de listeners orphelins |
| R5 | **Input lag high scores** | Basse | Faible | Direction queue bufferisé, anti-180° déjà implémenté |
| R6 | **Touch controls confusion** | Moyenne | Moyen | Instructions visuelles sur mobile, feedback tactile |
| R7 | **Cross-origin fonts blocked** | Basse | Faible | Fallback système si Google Fonts unreachable |

### 10.2 — Points de vigilance développement

**Performance**

- Ne jamais créer d'objets dans le game loop hot path (pré-allocation)
- Pooling обязательно pour les particules (500 max)
- Collision lookup via Map, pas d'array scan `includes()`

**Audio**

- Tester sur navigateurs variés (Safari a parfois des quirks Web Audio)
- Prévoir fallback silencieux si `AudioContext` non supporté
- Gérer le cas où l'utilisateur mute via les raccourcis système

**Responsive**

- Tester sur viewport 320px minimum
- Canvas resize doit préserver le game state
- Touch controls ne doivent pas interférer avec scroll naturel

**Persist**

- Schema versioning pour migrations futures
- Validation systématique des données lues depuis localStorage
- Prévoir export/import CSV pour transfer de scores

### 10.3 — Définitions

| Terme | Définition |
|-------|-----------|
| **Tick** | Un cycle de logique jeu (mouvement serpent, collision) exécuté à intervalle fixe |
| **Frame** | Une itération de rendu (RAF) à 60 FPS |
| **Dirty checking** | Détection de changement d'état avant rendu |
| **Object pool** | Pré-allocation d'objets réutilisables pour éviter l'allocation GC |

### 10.4 — Checklist qualité avant release

```
PRE-RELEASE CHECKLIST
══════════════════════

FUNCIONNALITÉ
  □ Serpent bouge dans les 4 directions
  □ Collision mur → game over
  □ Collision self → game over
  □ Makan food → score +1, serpent +1 segment
  □ Level up tous les N points → speed increase
  □ Game over → screen + restart

VISUEL
  □ Grid holographique visible
  □ Glow néon sur serpent (tête + body)
  □ Trail dégradé derrière serpent
  □ Pulse sur food
  □ Burst particules au makan food
  □ Scanlines overlay
  □ Screen shake au game over

AUDIO
  □ SFX eat jouable
  □ SFX die jouable
  □ SFX levelup jouable
  □ Volume adjustable
  □ Mute fonctionnel

UI
  □ Menu screen avec titre animé
  □ HUD score/level visible pendant jeu
  □ Game over screen avec restart
  □ High scores sauvegardés
  □ Settings modal fonctionnel

RESPONSIVE
  □ Desktop (1024px+) : canvas 800×500
  □ Tablet (768px) : canvas 640×400
  □ Mobile (< 768px) : canvas fullwidth + touch controls
  □ Keyboard fonctionnel sur desktop
  □ Touch/swipe fonctionnel sur mobile

PERFORMANCE
  □ 60 FPS stable sur desktop
  □ 30+ FPS stable sur mobile
  □ Memory < 30 MB
  □ No console errors
  □ No memory leak après 10 games

COMPATIBILITÉ
  □ Chrome 80+
  □ Firefox 75+
  □ Safari 14+
  □ Edge 80+
  □ Mobile Chrome / Safari
```

---

## 11. Annexes

### A — Variables CSS (extrait)

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

### B — Table de progression (LevelService)

```javascript
const SPEED_TABLE = [
  { level: 1,  minScore: 0,    tickMs: 150, label: 'INIT' },
  { level: 2,  minScore: 50,   tickMs: 135, label: 'SLOW' },
  { level: 3,  minScore: 100,  tickMs: 120, label: 'MEDIUM' },
  { level: 4,  minScore: 200,  tickMs: 105, label: 'FAST' },
  { level: 5,
