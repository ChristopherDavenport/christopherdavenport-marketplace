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
