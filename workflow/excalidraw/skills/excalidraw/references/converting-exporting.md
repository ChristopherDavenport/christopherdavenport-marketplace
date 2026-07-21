# Converting and Exporting

Track D — the lightest track. Two things: turn simple **Mermaid** into Excalidraw (doable in-skill), and produce **SVG/PNG** (not doable in-skill — documented as an out-of-process step). Do not conflate them: this skill emits `.excalidraw` JSON; rasterizing is someone else's job.

## Mermaid → Excalidraw

### Preferred: parse simple graphs and rebuild with the factory

For `graph TD/LR/TB` and `flowchart` with rectangle/round/diamond nodes and `-->` edges, parse the source and rebuild with `shape` + `addLabel` + `connect`. No DOM, no dependencies, deterministic layout. Write to `/tmp/mermaid.js`:

```js
// node /tmp/mermaid.js graph.mmd out.excalidraw
const { shape, addLabel, file } = require('/tmp/exc.js');
const { connect } = require('/tmp/connect.js');
const fs = require('fs');

function parseGraph(src) {
  const lines = src.split('\n').map(l => l.trim()).filter(Boolean);
  let horizontal = false;
  const nodes = new Map();          // key -> {key, label, kind}
  const edges = [];                 // {from, to, label}

  const decl = (tok) => {           // parse "A[Label]" / "A(Label)" / "A{Label}" / bare "A"
    let m;
    if ((m = tok.match(/^(\w+)\{(.+?)\}$/)))      return upsert(m[1], m[2], 'diamond');
    if ((m = tok.match(/^(\w+)\((.+?)\)$/)))      return upsert(m[1], m[2], 'ellipse');
    if ((m = tok.match(/^(\w+)\[(.+?)\]$/)))      return upsert(m[1], m[2], 'rectangle');
    if ((m = tok.match(/^(\w+)$/)))               return upsert(m[1], m[1], 'rectangle');
    return null;
  };
  const upsert = (key, label, kind) => {
    if (!nodes.has(key)) nodes.set(key, { key, label, kind });
    else if (label !== key) Object.assign(nodes.get(key), { label, kind }); // later decl with a label wins
    return nodes.get(key);
  };

  for (const line of lines) {
    let m;
    if ((m = line.match(/^(?:graph|flowchart)\s+(TB|TD|BT|LR|RL)/i))) {
      horizontal = /LR|RL/i.test(m[1]); continue;
    }
    // edge:  A[..] -->|label| B{..}   (label optional)
    m = line.match(/^(.+?)\s*--+>\s*(?:\|(.+?)\|\s*)?(.+?)$/);
    if (m) {
      const a = decl(m[1].trim()), b = decl(m[3].trim());
      if (a && b) edges.push({ from: a.key, to: b.key, label: m[2] || null });
      continue;
    }
    decl(line);   // standalone node declaration
  }
  return { horizontal, nodes: [...nodes.values()], edges };
}

function build({ horizontal, nodes, edges }) {
  const els = [];
  const w = 200, h = 64, gap = 80;
  const order = new Map(nodes.map((n, i) => [n.key, i]));
  const byKey = new Map();
  nodes.forEach((n, i) => {
    const x = horizontal ? 100 + i * (w + gap) : 100;
    const y = horizontal ? 100 : 100 + i * (h + gap);
    const s = shape(n.kind, x, y, w, h);
    els.push(s); addLabel(els, s.id, n.label);
    byKey.set(n.key, s);
  });
  for (const e of edges) {
    const arrow = connect(els, byKey.get(e.from).id, byKey.get(e.to).id);
    if (e.label) addLabel(els, arrow.id, e.label);   // edge label binds to the arrow
  }
  return file(els);
}

const src = fs.readFileSync(process.argv[2], 'utf8');
fs.writeFileSync(process.argv[3], JSON.stringify(build(parseGraph(src)), null, 2));
```

```sh
printf 'graph TD\n  A[Start] --> B{Check}\n  B -->|ok| C[Done]\n  B -->|no| A\n' > /tmp/g.mmd
node /tmp/mermaid.js /tmp/g.mmd out.excalidraw
node /tmp/validate.js out.excalidraw
```

Scope of this parser: `graph`/`flowchart` direction, node shapes `[rect]` / `(round)` / `{diamond}`, and `-->` / `-->|label|` edges. It lays nodes out in declaration order (column, or row for `LR`). It does **not** do real graph layout (crossing minimization, ranks) — for a handful of nodes it's fine; past that, or for other node shapes, use the official package below.

### Higher fidelity: the official package

For richer Mermaid (subgraphs, many node shapes, sequence/class/state/gantt), use Excalidraw's own converter. It needs a browser-like environment, so run it under `jsdom` — flag the heaviness to the user (network install, slower):

```sh
npx --yes --package=@excalidraw/mermaid-to-excalidraw --package=@excalidraw/excalidraw \
    --package=jsdom node -e '
const { JSDOM } = require("jsdom");
const dom = new JSDOM("<!doctype html><html><body></body></html>");
global.window = dom.window; global.document = dom.window.document;
const { parseMermaidToExcalidraw } = require("@excalidraw/mermaid-to-excalidraw");
const { convertToExcalidrawElements } = require("@excalidraw/excalidraw");
const fs = require("fs");
(async () => {
  const { elements } = await parseMermaidToExcalidraw(fs.readFileSync(process.argv[1],"utf8"));
  const full = convertToExcalidrawElements(elements);
  fs.writeFileSync(process.argv[2], JSON.stringify({
    type:"excalidraw", version:2, source:"https://excalidraw.com",
    elements: full, appState:{gridSize:null, viewBackgroundColor:"#ffffff"}, files:{}
  }, null, 2));
})();
' /tmp/g.mmd out.excalidraw
```

`convertToExcalidrawElements` backfills all the required fields (ids, seeds, bindings) from a compact skeleton — so its output is already schema-valid; still run the validator to be sure.

## Exporting to SVG / PNG — out of process

**You cannot rasterize an Excalidraw file in-skill.** Rendering needs the Excalidraw canvas/renderer, which needs a DOM/browser. Never write a PNG/SVG yourself and never claim you did. Offer one of these instead:

- **SVG, headless.** `npx --yes excalidraw-to-svg` (community, jsdom-based), or Excalidraw's own `exportToSvg` from `@excalidraw/excalidraw` run under `jsdom`/headless Chrome. Returns an SVG string/DOM.
- **PNG, headless.** `excalidraw_export` (a puppeteer CLI: `npx --yes excalidraw_export file.excalidraw`) drives a real headless Chromium and writes `.png`/`.svg`. Excalidraw's `exportToBlob` does the same inside a browser context.
- **Manual (most reliable).** Tell the user: open the file at excalidraw.com → File → Open, then File → Export image → PNG/SVG.

If the user's actual deliverable is an image, produce and validate the `.excalidraw`, then hand them one of the above and stop — that's the correct completion of an export request, not a rendered file from this skill.

## Acceptance via the real library (strongest check)

When the environment allows a network install, the highest-confidence proof that a generated file will open is to feed it through Excalidraw's own `restore()` + `exportToSvg()` under `jsdom`: if the official code accepts and renders it without throwing, the schema is good — a stronger signal than the hand-rolled [validator](validating.md). This is optional and heavy; the validator is the everyday gate.
