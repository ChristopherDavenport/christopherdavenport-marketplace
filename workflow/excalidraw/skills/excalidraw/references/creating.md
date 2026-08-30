# Creating

Track B — generate a valid diagram from nothing. The whole track rests on one rule: **never hand-type element JSON.** Build every element through the factory below, which fills the correct defaults and randomizes the identity fields, then run [the validator](validating.md) before you finish.

There are two generators that satisfy that rule. This file documents the **factory**: a few dozen lines of plain `node`, no dependencies, works offline — the default. The alternative is Excalidraw's own **Skeleton API**, `convertToExcalidrawElements`, which takes a compact `{type, x, y, label, start, end}` description and expands it using upstream's code; it needs a network install and a DOM shim, and it is documented in [skeleton-api.md](skeleton-api.md). Prefer it when you want Excalidraw itself to size text containers, fit frames to their children, or place arrow endpoints from real text metrics. Either way, finish at the validator.

## The element factory

Write this to `/tmp/exc.js`. Other scripts `require('/tmp/exc.js')`.

```js
// /tmp/exc.js — element factory + file wrapper. require() this from other scripts.
const crypto = require('crypto');

const rnd = () => Math.floor(Math.random() * 2 ** 31);              // 32-bit int for seed/versionNonce
const id  = () => crypto.randomBytes(16).toString('hex').slice(0, 21); // unique-enough id

function base(o = {}) {
  return {
    id: id(), type: 'rectangle',
    x: 0, y: 0, width: 100, height: 100, angle: 0,
    strokeColor: '#1e1e1e', backgroundColor: 'transparent',
    fillStyle: 'solid', strokeWidth: 2, strokeStyle: 'solid',
    roughness: 1, opacity: 100,
    groupIds: [], frameId: null, roundness: null,
    seed: rnd(), version: 1, versionNonce: rnd(),
    isDeleted: false, boundElements: null,
    updated: Date.now(), link: null, locked: false,
    ...o,
  };
}

// rectangle | ellipse | diamond
function shape(type, x, y, width, height, o = {}) {
  const roundness = type === 'rectangle' ? { type: 3 } : null;
  return base({ type, x, y, width, height, roundness, ...o });
}

function text(str, x, y, o = {}) {
  const fontSize = o.fontSize ?? 20, lineHeight = 1.25;
  const lines = String(str).split('\n');
  const width  = o.width  ?? Math.max(1, ...lines.map(l => l.length)) * fontSize * 0.6;
  const height = o.height ?? lines.length * fontSize * lineHeight;
  return base({
    type: 'text', x, y, width, height,
    text: str, originalText: str,
    fontSize, fontFamily: o.fontFamily ?? 5,   // 5 = Excalifont, Excalidraw's current default
    textAlign: o.textAlign ?? 'left', verticalAlign: o.verticalAlign ?? 'top',
    containerId: o.containerId ?? null, lineHeight, autoResize: true,
    ...o,
  });
}

// centered label bound INTO a shape (edits both ends)
function addLabel(elements, shapeId, str, o = {}) {
  const s = elements.find(e => e.id === shapeId);
  const t = text(str, 0, 0, { textAlign: 'center', verticalAlign: 'middle',
                              containerId: shapeId, ...o });
  t.x = s.x + (s.width  - t.width)  / 2;
  t.y = s.y + (s.height - t.height) / 2;
  s.boundElements = (s.boundElements || []).concat({ id: t.id, type: 'text' });
  elements.push(t);
  return t;
}

function file(elements) {
  return {
    type: 'excalidraw', version: 2, source: 'https://excalidraw.com',
    elements,
    appState: { gridSize: null, viewBackgroundColor: '#ffffff' },
    files: {},
  };
}

module.exports = { rnd, id, base, shape, text, addLabel, file };
```

What each helper guarantees:

- `base(overrides)` — a complete element with every required base field ([schema.md](schema.md)) and a fresh `id`/`seed`/`versionNonce`. Spread your overrides last.
- `shape(type, x, y, w, h, overrides)` — a `rectangle` (rounded by default), `ellipse`, or `diamond`.
- `text(str, x, y, overrides)` — a text element; estimates `width`/`height` from the string (Excalidraw recomputes exact metrics on load, so an estimate is fine).
- `addLabel(elements, shapeId, str)` — a **bound, centered label**: it sets the text's `containerId` *and* pushes `{id, type:"text"}` into the shape's `boundElements`. Both sides, always.
- `file(elements)` — wraps the array into a complete scene object.

## Build-order discipline

Build in dependency order so ids exist before anything references them:

1. **Shapes first** — create every rectangle/ellipse/diamond/frame and collect their ids.
2. **Labels next** — `addLabel(els, shape.id, "…")` for each labeled shape.
3. **Arrows last** — `connect(els, fromId, toId)` (see [layout-and-binding.md](layout-and-binding.md)) once both endpoints exist.

Then `file(els)`, write, and validate.

## Worked build

```js
// /tmp/build.js
const { shape, addLabel, file } = require('/tmp/exc.js');
const { connect } = require('/tmp/connect.js');   // see layout-and-binding.md
const fs = require('fs');

const els = [];
const api   = shape('rectangle', 100, 100, 200, 64); els.push(api);   addLabel(els, api.id,   'API');
const cache = shape('rectangle', 100, 240, 200, 64); els.push(cache); addLabel(els, cache.id, 'Cache');
const db    = shape('rectangle', 100, 380, 200, 64); els.push(db);    addLabel(els, db.id,    'DB');
connect(els, api.id, cache.id);
connect(els, cache.id, db.id);

fs.writeFileSync(process.argv[2], JSON.stringify(file(els), null, 2));
```

```sh
node /tmp/build.js diagram.excalidraw
node /tmp/validate.js diagram.excalidraw     # must print {ok:true, ...}
```

## Flowchart auto-layout

For the common "turn this list of steps into a flowchart" request, the `flow` helper (in `/tmp/connect.js`, [layout-and-binding.md](layout-and-binding.md)) lays boxes out in a column (or row) and wires them in sequence:

```sh
node -e "const {flow}=require('/tmp/connect.js'); \
  require('fs').writeFileSync('flow.excalidraw', JSON.stringify(flow(['Start','Validate','Save','Done']), null, 2));"
node /tmp/validate.js flow.excalidraw
```

Pass `{horizontal:true}` for a left-to-right layout, or `{boxW, boxH, gap, x, y}` to tune spacing.

## Colors and styling

Style via the `overrides` argument, staying inside the enums ([schema.md](schema.md)):

```js
shape('rectangle', 100, 100, 200, 64, {
  backgroundColor: '#a5d8ff',   // fill only shows when != "transparent"
  fillStyle: 'solid',           // solid | hachure | cross-hatch | zigzag
  strokeColor: '#1971c2',
  strokeWidth: 2,               // 1 | 2 | 4  (nothing else)
  roughness: 1,                 // 0 | 1 | 2
});
```

Always finish with the validator — a create run that hasn't been validated is unfinished.
