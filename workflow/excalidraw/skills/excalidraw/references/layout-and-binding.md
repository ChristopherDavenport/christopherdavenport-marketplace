# Layout and Binding

The geometry and the bidirectional wiring, shared by create ([creating.md](creating.md)) and modify ([modifying.md](modifying.md)). The one invariant that governs everything here: **a binding touches two elements; both must be edited or it is wrong.**

## Bound arrows — the `connect` recipe

Write this to `/tmp/connect.js`. It computes where an arrow should meet each shape's edge, builds the arrow with relative `points`, and — critically — writes the binding on **all three** places: the arrow's `startBinding`/`endBinding`, and each shape's `boundElements`.

```js
// /tmp/connect.js — bound-arrow geometry + flowchart layout. Requires /tmp/exc.js.
const { base, shape, addLabel, file } = require('/tmp/exc.js');

// connect two existing shapes with a bound arrow; mutates both shapes + pushes the arrow.
function connect(elements, fromId, toId, o = {}) {
  const gap = o.gap ?? 8;
  const A = elements.find(e => e.id === fromId);
  const B = elements.find(e => e.id === toId);

  // point on `box` boundary in the direction of (tx,ty), starting from box center
  const edge = (box, tx, ty) => {
    const cx = box.x + box.width / 2, cy = box.y + box.height / 2;
    const dx = tx - cx, dy = ty - cy;
    if (dx === 0 && dy === 0) return { x: cx, y: cy };
    const s = 1 / Math.max(Math.abs(dx) / (box.width / 2),
                           Math.abs(dy) / (box.height / 2));
    return { x: cx + dx * s, y: cy + dy * s };
  };

  const cb = { x: B.x + B.width / 2, y: B.y + B.height / 2 };
  const ca = { x: A.x + A.width / 2, y: A.y + A.height / 2 };
  let start = edge(A, cb.x, cb.y);   // A's edge toward B
  let end   = edge(B, ca.x, ca.y);   // B's edge toward A

  const len = Math.hypot(end.x - start.x, end.y - start.y) || 1;
  const ux = (end.x - start.x) / len, uy = (end.y - start.y) / len;
  start = { x: start.x + ux * gap, y: start.y + uy * gap }; // gap off A
  end   = { x: end.x   - ux * gap, y: end.y   - uy * gap }; // gap off B

  const dx = end.x - start.x, dy = end.y - start.y;
  const arrow = base({
    type: 'arrow', x: start.x, y: start.y,
    width: Math.abs(dx), height: Math.abs(dy),
    points: [[0, 0], [dx, dy]], lastCommittedPoint: null,
    roundness: { type: 2 },
    startArrowhead: o.startArrowhead ?? null,
    endArrowhead:   o.endArrowhead   ?? 'arrow',
    startBinding: { elementId: A.id, focus: 0, gap },
    endBinding:   { elementId: B.id, focus: 0, gap },
  });

  A.boundElements = (A.boundElements || []).concat({ id: arrow.id, type: 'arrow' });
  B.boundElements = (B.boundElements || []).concat({ id: arrow.id, type: 'arrow' });
  elements.push(arrow);
  return arrow;
}

// tie factory + connect into an auto-laid-out flowchart
function flow(labels, o = {}) {
  const els = [];
  const w = o.boxW ?? 200, h = o.boxH ?? 64, gap = o.gap ?? 70;
  const x0 = o.x ?? 100, y0 = o.y ?? 100;
  const horizontal = o.horizontal ?? false;
  const nodes = labels.map((label, i) => {
    const x = horizontal ? x0 + i * (w + gap) : x0;
    const y = horizontal ? y0 : y0 + i * (h + gap);
    const s = shape('rectangle', x, y, w, h);
    els.push(s); addLabel(els, s.id, label);
    return s;
  });
  for (let i = 0; i < nodes.length - 1; i++) connect(els, nodes[i].id, nodes[i + 1].id);
  return file(els);
}

module.exports = { connect, flow };
```

### Why the geometry is what it is

- **`edge(box, tx, ty)`** finds where a ray from the box's center toward `(tx, ty)` crosses the box boundary. The `s` scale picks whichever axis (x or y) the ray exits first, so the point always lands on an edge, never a corner overshoot.
- **`gap`** nudges both endpoints back off the edges so the arrowhead doesn't kiss the shape — matching how the editor draws bound arrows (default `8`px).
- **`points: [[0, 0], [dx, dy]]`** are relative to the arrow's `x`/`y` (which is `start`). The first point is always `[0, 0]`; the second is the vector to `end`. `width`/`height` are the absolute components of that vector — the arrow's bounding box.
- **`focus: 0`** centers the attachment; the editor recomputes it on the first drag, so `0` is a safe generated default.

The editor re-derives exact endpoints from the bindings when a bound shape moves, so slightly approximate geometry still snaps correct on load — but keeping it right means the file looks correct even before the first interaction.

## Labels — centered and bound

`addLabel(elements, shapeId, str)` (in `/tmp/exc.js`, [creating.md](creating.md)) centers a text element inside a shape and binds it both ways: it sets `containerId` on the text *and* appends `{id, type:"text"}` to the shape's `boundElements`. Use `verticalAlign:"middle"` + `textAlign:"center"` (which `addLabel` sets) so the label reads as inside the box. Never attach a label with a `"label"` property — that field doesn't exist in the format and renders blank ([schema.md](schema.md)).

## Grouping

A group is just a shared string in every member's `groupIds`:

```js
const { id } = require('/tmp/exc.js');
const gid = id();
for (const e of [boxA, labelA, boxB]) e.groupIds = [...e.groupIds, gid];
```

- Every member must carry the **same** group id string; a member missing it isn't in the group.
- `groupIds` is ordered outer→inner for nested groups; a single group is a one-element array.
- Ungroup by removing that id from each member's `groupIds`.

## Z-order

Array order in `elements` is the stacking order (later = on top). To raise an element, move it later in the array; to send it back, move it earlier. Only reach for explicit `index` fields ([schema.md](schema.md)) when you need a z-order that must survive independently of array position — otherwise omit `index` and let `restore()` backfill it.

## Alignment and distribution

Operate on the shapes' `x`/`y`/`width`/`height` directly, then re-run `connect` (or let the editor re-derive) for any arrows whose endpoints moved:

```js
// align a set of shapes' left edges to the leftmost:
const minX = Math.min(...shapes.map(s => s.x));
for (const s of shapes) s.x = minX;

// center horizontally on a common axis:
const cx = 400;
for (const s of shapes) s.x = cx - s.width / 2;

// distribute vertically with a fixed gap:
let y = shapes[0].y;
for (const s of shapes) { s.y = y; y += s.height + 40; }
```

When you move a shape that has a bound label, move the label too (`label.x += dx; label.y += dy`) — or re-run `addLabel` after clearing the old one. When you move a shape that has bound arrows, re-derive them with `connect` so they don't point at stale coordinates ([modifying.md](modifying.md)).
