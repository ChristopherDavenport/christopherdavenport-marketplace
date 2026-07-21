# Modifying

Track C — edit an existing file without corrupting it. The failure mode here is always the same: you change one element and forget the elements that referenced it. Every mutation below ends by repairing dependents and running [the validator](validating.md).

## The round-trip pattern

```js
// /tmp/mod.js — load, mutate, write back.
const { shape, text, addLabel } = require('/tmp/exc.js');
const { connect } = require('/tmp/connect.js');
const fs = require('fs');

const path = process.argv[2];
const doc = JSON.parse(fs.readFileSync(path, 'utf8'));
const els = doc.elements;
const byId = id => els.find(e => e.id === id);

// ... mutate els in place ...

fs.writeFileSync(path, JSON.stringify(doc, null, 2));   // doc, not just els — preserves appState/files
```

Two non-negotiables:

- **Mutate in place; preserve unknown fields.** Change only the fields you mean to. Never rebuild an element from scratch during a modify — you'll drop keys Excalidraw wrote (custom props, `frameId`, `index`, future fields). Re-serialize `doc`, so `appState` and `files` survive too.
- **Bump `versionNonce` on elements you touch.** Optional but correct — `e.versionNonce = require('/tmp/exc.js').rnd()` — so reconciliation sees the change. Not required for the file to open.

## Add an element

Reuse the factory, push, and (if it's a shape that should be labeled or connected) wire it:

```js
const box = shape('rectangle', 100, 520, 200, 64); els.push(box);
addLabel(els, box.id, 'New Node');       // both-sided label binding
connect(els, byId('EXISTING_ID').id, box.id);   // both-sided arrow binding
```

## Remove an element — and its references

Splicing the element out is the easy half. The essential half is stripping every reference to its id:

```js
function remove(els, id) {
  const target = els.find(e => e.id === id);
  if (!target) return;

  // 1. If removing a SHAPE, also remove arrows/labels bound to it, and clean the other ends.
  const dependents = (target.boundElements || []).map(b => b.id);
  for (const depId of dependents) remove(els, depId);   // recurse: labels + arrows go too

  // 2. Drop the element itself.
  const i = els.findIndex(e => e.id === id);
  if (i >= 0) els.splice(i, 1);

  // 3. Scrub any lingering references from every remaining element.
  for (const e of els) {
    if (Array.isArray(e.boundElements))
      e.boundElements = e.boundElements.filter(b => b.id !== id);
    if (e.startBinding && e.startBinding.elementId === id) e.startBinding = null;
    if (e.endBinding   && e.endBinding.elementId   === id) e.endBinding   = null;
    if (e.containerId === id) e.containerId = null;
  }
}
```

The alternative to splicing is setting `isDeleted: true` (the element stays in the array but doesn't render) — but you **still** must scrub references, so splicing is usually cleaner. After a remove, the validator must report no dangling references.

## Move an element — a graph operation

Moving is never just `x`/`y`. When a shape moves, its label and its bound arrows must follow:

```js
function moveShape(els, id, dx, dy) {
  const s = els.find(e => e.id === id);
  s.x += dx; s.y += dy;

  // 1. Move any bound label with it.
  for (const b of (s.boundElements || []).filter(b => b.type === 'text')) {
    const t = els.find(e => e.id === b.id);
    if (t) { t.x += dx; t.y += dy; }
  }
  // 2. Re-derive every bound arrow's geometry so it still meets the shapes.
  const arrowIds = new Set((s.boundElements || []).filter(b => b.type === 'arrow').map(b => b.id));
  for (const a of els.filter(e => arrowIds.has(e.id))) redrawArrow(els, a);
}
```

The simplest correct `redrawArrow` is to reconnect from scratch: read the arrow's `startBinding`/`endBinding` element ids, delete the arrow, and re-`connect` those two shapes (carrying over `endArrowhead` etc.). Excalidraw *will* re-derive bound-arrow endpoints itself on load, so leaving stale points is not fatal — but the file looks broken until the first interaction, so redraw them.

## Restyle

Mutate only style fields, staying inside the enums ([schema.md](schema.md)):

```js
const s = byId('ID');
Object.assign(s, { backgroundColor: '#b2f2bb', fillStyle: 'solid', strokeColor: '#2f9e44', strokeWidth: 2 });
```

## Connect two existing shapes

```js
connect(els, byId('A').id, byId('B').id);   // updates boundElements on both, pushes the arrow
```

## Relabel

Update the bound text's **both** `text` and `originalText`; let `autoResize` handle sizing on load:

```js
const t = els.find(e => e.type === 'text' && e.containerId === 'SHAPE_ID');
t.text = t.originalText = 'New Label';
```

If the shape has no label yet, use `addLabel(els, 'SHAPE_ID', 'New Label')` instead.

## Group / ungroup

```js
const { id } = require('/tmp/exc.js');
const gid = id();
for (const e of [byId('A'), byId('B'), byId('C')]) e.groupIds = [...e.groupIds, gid];  // group
for (const e of els) e.groupIds = e.groupIds.filter(g => g !== gid);                    // ungroup
```

Every member needs the **same** group id string ([layout-and-binding.md](layout-and-binding.md)).

## Always finish by validating

```sh
node /tmp/mod.js diagram.excalidraw
node /tmp/validate.js diagram.excalidraw   # must be {ok:true}
```

A modify run that hasn't re-passed the validator is unfinished — the whole point of Track C is not corrupting the graph, and the validator is what proves you didn't.
