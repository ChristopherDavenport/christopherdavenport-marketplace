# Inspecting

Track A — parse, summarize, and query an existing `.excalidraw` file. Read-only: nothing here mutates the file.

## Loading

- **Small files** — just Read the file; it's JSON, and the structure is [documented in schema.md](schema.md).
- **Large files** (many elements, or embedded images bloating `files`) — don't dump the whole thing into context. Query it with `jq`/`node` and report the answer.

## The summarize recipe

Write to `/tmp/summarize.js`. Prints `{counts, texts, edges, bbox}` — a one-shot overview.

```js
// node /tmp/summarize.js file.excalidraw -> {counts, texts, edges, bbox}
const doc = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const els = doc.elements.filter(e => !e.isDeleted);
const byId = new Map(els.map(e => [e.id, e]));
const label = id => { const c = byId.get(id); if (!c) return id;
  const t = els.find(e => e.type === 'text' && e.containerId === id);
  return (t && t.text) || `${c.type}:${id.slice(0, 6)}`; };

const counts = {};
for (const e of els) counts[e.type] = (counts[e.type] || 0) + 1;
const texts = els.filter(e => e.type === 'text' && !e.containerId).map(e => e.text);
const edges = els.filter(e => e.type === 'arrow' && e.startBinding && e.endBinding)
  .map(a => `${label(a.startBinding.elementId)} -> ${label(a.endBinding.elementId)}`);
const bbox = els.reduce((b, e) => ({
  minX: Math.min(b.minX, e.x), minY: Math.min(b.minY, e.y),
  maxX: Math.max(b.maxX, e.x + e.width), maxY: Math.max(b.maxY, e.y + e.height),
}), { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity });

console.log(JSON.stringify({ counts, texts, edges, bbox }, null, 2));
```

What the fields mean:

- `counts` — number of live (non-deleted) elements per type.
- `texts` — **free-standing** text only (labels bound into shapes are excluded, since they show up in `edges`/node names instead). This keeps the list to captions and notes.
- `edges` — the connectivity outline: `Source -> Target`, naming each endpoint by its **bound label text** where it has one, else `type:idprefix`. This is the readable structure of the drawing.
- `bbox` — the overall bounding box, useful for placing new elements or reporting canvas size.

## The enrichment recipe

`summarize.js` reads only what the file states outright: it counts an arrow as an edge *only* when both ends are bound, and it treats every free text as a caption. On a hand-drawn whiteboard that undercounts badly — arrows are often never snapped to their shapes, labels are often just text dropped on top of (or just above) a box, and grouping is often "I drew this box inside that box." This recipe recovers that implied structure with pure geometry: no model, fully deterministic. Reach for it when `summarize.js` returns an empty or suspiciously thin `edges` list, or when you need the nesting the raw graph never encoded.

Write to `/tmp/enrich.js`. It keeps the summarizer's output keys and adds `flow`, `containment`, and `warnings` — but note that **`edges` is now an array of objects, not `"A -> B"` strings** (fields below).

```js
// node /tmp/enrich.js file.excalidraw -> {counts, flow, texts, edges, containment, bbox, warnings}
// Geometry pass: recover the structure the raw graph doesn't encode —
// unbound arrows, text-inside/above-shape labels, and box-inside-box nesting.
const doc  = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const els  = doc.elements.filter(e => !e.isDeleted);
const byId = new Map(els.map(e => [e.id, e]));

const NODE_TYPES  = new Set(['rectangle', 'ellipse', 'diamond', 'image']);
const SNAP_PX     = 40;   // max gap from a loose arrow endpoint to the shape it "means"
const CONTAIN_PAD = 2;    // slack when testing whether one bbox encloses another
const TITLE_GAP   = 12;   // max px a title may sit above a shape's top edge
const nodes = els.filter(e => NODE_TYPES.has(e.type));
const warnings = [];

// geometry — axis-aligned; ignores `angle` and treats every shape as its bbox
const rect   = e => ({ x0: e.x, y0: e.y, x1: e.x + e.width, y1: e.y + e.height });
const center = e => [e.x + e.width / 2, e.y + e.height / 2];
const area   = r => (r.x1 - r.x0) * (r.y1 - r.y0);
const distPointRect = ([px, py], r) => {
  const dx = Math.max(r.x0 - px, 0, px - r.x1);
  const dy = Math.max(r.y0 - py, 0, py - r.y1);
  return Math.hypot(dx, dy);                        // 0 when the point is inside
};
const encloses = (a, b) =>
  a.x0 - CONTAIN_PAD <= b.x0 && a.y0 - CONTAIN_PAD <= b.y0 &&
  a.x1 + CONTAIN_PAD >= b.x1 && a.y1 + CONTAIN_PAD >= b.y1 && area(a) > area(b);

// pass 1 — labels: bound (containerId) → free text inside a shape → free text titling a shape
const boundLabel = id => {
  const t = els.find(e => e.type === 'text' && e.containerId === id);
  return t && t.text;
};
const implicitLabel = new Map();
const named = id => !!boundLabel(id) || implicitLabel.has(id);   // shape already has a label
const texts = [];                                    // genuinely free-standing notes
const leftover = [];
for (const t of els.filter(e => e.type === 'text' && !e.containerId)) {
  const host = nodes                                 // (a) center sits inside a shape
    .filter(n => distPointRect(center(t), rect(n)) === 0)
    .sort((a, b) => area(rect(a)) - area(rect(b)))[0];   // smallest enclosing shape
  if (host && !named(host.id)) implicitLabel.set(host.id, t.text);
  else leftover.push(t);
}
for (const t of leftover) {                          // (b) text sitting just above a shape's top edge
  const tr = rect(t), tcx = center(t)[0];
  const host = nodes
    .filter(n => { const r = rect(n); const gap = r.y0 - tr.y1;
      return tcx >= r.x0 && tcx <= r.x1 && gap >= -2 && gap <= TITLE_GAP; })
    .sort((a, b) => (rect(a).y0 - tr.y1) - (rect(b).y0 - tr.y1))[0];   // nearest below the text
  if (host && !named(host.id)) implicitLabel.set(host.id, t.text);
  else texts.push(t.text);
}
const labelOf = id => {
  const n = byId.get(id);
  return boundLabel(id) || implicitLabel.get(id) || (n && n.name) ||
         (n ? `${n.type}:${id.slice(0, 6)}` : id);
};

// pass 2 — edges: trust a binding, else snap the endpoint to the nearest (then smallest) shape
const endpointScene = (a, which) => {
  const p = which === 'start' ? a.points[0] : a.points[a.points.length - 1];
  return [a.x + p[0], a.y + p[1]];
};
const resolveEnd = (a, which) => {
  const b = which === 'start' ? a.startBinding : a.endBinding;
  if (b && byId.has(b.elementId)) return { id: b.elementId, via: 'bound', dist: 0 };
  if (b) warnings.push(`${a.id}.${which}Binding -> missing ${b.elementId}`);
  const pt = endpointScene(a, which);
  let best = null;
  for (const n of nodes) {
    const d = distPointRect(pt, rect(n)), ar = area(rect(n));
    if (!best || d < best.dist - 1e-9 || (Math.abs(d - best.dist) < 1e-9 && ar < best.area))
      best = { id: n.id, via: 'inferred', dist: d, area: ar };
  }
  if (best && best.dist <= SNAP_PX) return best;
  warnings.push(`${a.id}.${which} has no shape within ${SNAP_PX}px`);
  return null;
};
const edges = [];
for (const a of els.filter(e => e.type === 'arrow')) {
  if (!Array.isArray(a.points) || a.points.length < 2) { warnings.push(`${a.id} has no points`); continue; }
  const s = resolveEnd(a, 'start'), t = resolveEnd(a, 'end');
  if (!s || !t) continue;
  if (s.id === t.id) { warnings.push(`${a.id} resolves to a self-loop on ${labelOf(s.id)} — dropped`); continue; }
  const via = boundLabel(a.id);                       // an arrow can carry its own label (e.g. "yes")
  edges.push({
    from: s.id, to: t.id, fromLabel: labelOf(s.id), toLabel: labelOf(t.id),
    ...(via ? { label: via } : {}),
    provenance: s.via === 'bound' && t.via === 'bound' ? 'bound' : 'inferred',
    slack: Math.round(Math.max(s.dist, t.dist)),      // 0 = exact; higher = looser inference
  });
}

// pass 3 — containment: frameId wins, else the smallest shape that encloses it
const parentOf = new Map();
for (const b of nodes) {
  if (b.frameId && byId.has(b.frameId)) { parentOf.set(b.id, b.frameId); continue; }
  let p = null;
  for (const a of nodes)
    if (a.id !== b.id && encloses(rect(a), rect(b)) && (!p || area(rect(a)) < area(rect(p)))) p = a;
  if (p) parentOf.set(b.id, p.id);
}
const containment = {};
for (const [child, parent] of parentOf)
  (containment[labelOf(parent)] ??= []).push(labelOf(child));

// pass 4 — dominant flow direction from the edge vectors
let dx = 0, dy = 0;
for (const e of edges) {
  const [sx, sy] = center(byId.get(e.from)), [tx, ty] = center(byId.get(e.to));
  dx += Math.abs(tx - sx); dy += Math.abs(ty - sy);
}
const flow = !edges.length ? 'none' : dy > dx * 1.3 ? 'TD' : dx > dy * 1.3 ? 'LR' : 'mixed';

// output — summarize.js keys plus the inferred structure (note: edges are now objects)
const counts = {};
for (const e of els) counts[e.type] = (counts[e.type] || 0) + 1;
const bbox = els.reduce((b, e) => ({
  minX: Math.min(b.minX, e.x), minY: Math.min(b.minY, e.y),
  maxX: Math.max(b.maxX, e.x + e.width), maxY: Math.max(b.maxY, e.y + e.height),
}), { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity });

console.log(JSON.stringify({ counts, flow, texts, edges, containment, bbox, warnings }, null, 2));
```

What it recovers, pass by pass:

- **Unbound edges.** Each arrow endpoint is resolved to a shape: its binding if it has one, otherwise the nearest shape within `SNAP_PX` (ties broken toward the smaller shape, so an endpoint inside both a box and its container attaches to the box). Every edge carries `provenance` (`"bound"` = both ends were genuinely bound; `"inferred"` = at least one end was snapped) and `slack` (the larger endpoint gap in px — `0` is exact, higher is a looser guess). Filter on these to trust-rank the graph.
- **Implicit labels.** Free text whose center sits inside a shape becomes that shape's name (smallest enclosing shape wins); failing that, a text sitting just above a shape's top edge — horizontally over it, within `TITLE_GAP` px — titles it, catching the common "caption above the box" convention. Either way it feeds node names instead of polluting `texts`, which then holds only genuinely free-standing notes and captions.
- **Containment.** `containment` maps each parent's label to the labels drawn inside it — by `frameId` when set, otherwise by the smallest shape that encloses the child's bbox. This is the nesting/grouping the flat element array doesn't express.
- **Flow direction.** `flow` is `"TD"`, `"LR"`, `"mixed"`, or `"none"`, from the dominant axis of the edge vectors — a quick read of how the diagram is meant to be traversed.
- **Warnings.** Dangling bindings, endpoints with no shape nearby, and dropped self-loops go to `warnings` instead of silently distorting the graph.

Tuning and limits:

- **`SNAP_PX` is the sensitivity dial** for inferred edges: too low drops loose arrows, too high invents them. Because every edge reports `slack`, you can leave it generous and filter afterward rather than guess it up front.
- **Geometry is axis-aligned.** Rotation (`angle`) is ignored and every shape is treated as its bounding box, so an ellipse or diamond counts a corner of its bbox as "inside." Cheap and fine for the overwhelming majority of diagrams; wrong for tilted or tightly-packed ones.
- **Titles are matched above only.** The title pass (`TITLE_GAP`) catches a caption sitting above a shape, not one placed beside or below it; a label to the left of a box stays a free-standing note.
- **This is structure, not meaning.** It yields a clean typed graph — nodes, directed edges, nesting — but does not classify the diagram or assign roles (decision / datastore / actor). That interpretation is a separate step; this recipe exists to give it something precise to work from.

## `jq` one-liners

For quick questions without a script:

```sh
# counts by type
jq '.elements | group_by(.type) | map({type: .[0].type, count: length})' file.excalidraw

# all text content (labels + captions), one per line
jq -r '.elements[] | select(.type=="text") | .text' file.excalidraw

# overall bounding box of live elements
jq '[.elements[] | select(.isDeleted|not)]
    | {minX:(map(.x)|min), minY:(map(.y)|min),
       maxX:(map(.x + .width)|max), maxY:(map(.y + .height)|max)}' file.excalidraw

# every arrow and the ids it connects
jq -r '.elements[] | select(.type=="arrow")
       | "\(.id): \(.startBinding.elementId // "∅") -> \(.endBinding.elementId // "∅")"' file.excalidraw
```

## Query patterns

```sh
# find an element by its label text (returns the CONTAINER id, i.e. the shape)
jq -r --arg q "API" '.elements[] | select(.type=="text" and (.text|test($q;"i"))) | .containerId' file.excalidraw

# list all shapes with their label (join text.containerId back to the shape)
jq -r '.elements as $e
  | $e[] | select(.type|test("rectangle|ellipse|diamond"))
  | . as $s | ($e[] | select(.type=="text" and .containerId==$s.id) | .text) as $t
  | "\($s.type) \($s.id[0:6]): \($t)"' file.excalidraw

# members of a given group
jq -r --arg g "GROUPID" '.elements[] | select(.groupIds | index($g)) | .id' file.excalidraw

# elements inside a frame
jq -r --arg f "FRAMEID" '.elements[] | select(.frameId==$f) | .id' file.excalidraw
```

## Finding broken / dangling references

Useful as a health check before editing an unfamiliar file (the [validator](validating.md) reports these too, with exact messages):

```sh
# arrows whose binding targets no longer exist
node -e '
const d=JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"));
const ids=new Set(d.elements.map(e=>e.id));
for (const a of d.elements.filter(e=>e.type==="arrow")) {
  for (const k of ["startBinding","endBinding"]) {
    const b=a[k]; if (b && !ids.has(b.elementId)) console.log(`${a.id}.${k} -> missing ${b.elementId}`);
  }
}' file.excalidraw
```

For anything beyond a quick look — or before you *change* a file — run the full [validator](validating.md); it enforces every invariant in one pass and tells you exactly what's wrong.
