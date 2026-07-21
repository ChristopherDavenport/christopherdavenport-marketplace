---
name: excalidraw
description: >
  Read, create, and edit Excalidraw diagrams (`.excalidraw` JSON) as data — parse
  and summarize a drawing, generate schema-valid diagrams and flowcharts from
  scratch, add / move / restyle / connect shapes with correctly bound arrows and
  labels, and convert simple Mermaid graphs into Excalidraw. Use when the user
  wants to inspect an `.excalidraw` file, "make" or "generate an excalidraw
  diagram", "add a box / arrow / label to this diagram", "connect these shapes",
  "turn this mermaid into excalidraw", or extract the text and structure of a
  drawing. Emits every element with a randomized id / seed / versionNonce, keeps
  bindings bidirectional (arrow↔shape, label↔container), keeps points relative to
  each element's origin, and runs a validator before finishing. Not for rendering
  or exporting PNG / SVG in-process (that needs an external browser-based tool —
  the skill documents how but cannot rasterize), and not for the excalidraw.com
  web UI or real-time collaboration.
---

# Excalidraw

An `.excalidraw` file is plain JSON, so a diagram is fully manipulable as data — you can read it, generate it, and edit it without ever opening the app. But it is not a flat document. It is a *graph* with cross-references: arrows bind to the shapes they connect, text labels bind to the shapes that contain them, and every element carries randomized identity fields (`id`, `seed`, `versionNonce`) that the editor relies on for selection, reconciliation, and hand-drawn rendering. Hand-typing element JSON — or copying an element without re-minting its identity, or writing one side of a binding and forgetting the other — produces a file that silently renders wrong, drops shapes, or refuses to open.

This skill treats the file as a *validated data structure*. It generates every element through a small factory that gets the defaults, identity, and geometry right; it keeps every binding bidirectional; it keeps linear `points` relative to their element's origin; and it runs a validator that proves those invariants hold before declaring the work done. The same discipline covers all four things you do with these files: **inspect** an existing drawing, **create** one from scratch, **modify** one in place, and **convert** simple Mermaid into Excalidraw (with export to PNG/SVG documented as an out-of-process step, because rasterizing needs a browser).

## Scope

**Covers.** Parsing, summarizing, and querying `.excalidraw` files (Track A). Generating schema-valid diagrams — rectangle / ellipse / diamond / text / line / bound arrow / frame, flowcharts, and simple auto-layout (Track B). Modifying existing files — add / remove / move / restyle / connect / group / align / edit-text — while keeping every binding valid (Track C). Converting simple Mermaid graphs (`graph TD/LR`, `flowchart`) to Excalidraw, and documenting the external path for SVG/PNG export (Track D).

**Out of scope.** Rendering or rasterizing to PNG/SVG *in-process* — that requires a browser/DOM, so it is documented, never performed. Driving the excalidraw.com web UI or real-time collaboration. The `.excalidrawlib` library format. Heavy Mermaid features beyond basic flow/graph syntax (sequence, gantt, class, state diagrams) — for those, use the external `@excalidraw/mermaid-to-excalidraw` package described in [converting-exporting.md](references/converting-exporting.md).

## When This Skill Is Triggered

- User says some variation of: "inspect / summarize this `.excalidraw`", "what's in this drawing", "pull the text / structure out of this diagram".
- User says: "make / generate / draw an excalidraw diagram", "create a flowchart", "turn this list of steps into a diagram".
- User says: "add a box / node / arrow / label to this diagram", "connect these two shapes", "move / restyle / recolor X", "relabel this node".
- User says: "turn this mermaid into excalidraw", "convert this graph to excalidraw".
- User hands over a `.excalidraw` file (or asks to write one) and wants it changed or understood.

Do *not* trigger for: producing a **PNG or SVG image as the deliverable** (that is the export caveat in Track D — the skill emits `.excalidraw` JSON and points at an external rasterizer, it does not render); generic drawing / diagramming / design questions unrelated to the file format; or Mermaid that is going to stay Mermaid.

## Core Rules

These hold in every run. Internalize them before touching a file.

- **Bindings are bidirectional — edit both ends, always.** An arrow's `startBinding`/`endBinding.elementId` must point at a shape, *and* that shape's `boundElements` must contain `{id: arrowId, type: "arrow"}`. A bound label's `containerId` must point at a shape, *and* that shape's `boundElements` must contain `{id: textId, type: "text"}`. A one-sided binding renders detached or corrupts on load. The factory's `addLabel` and `connect` helpers do both sides for you — never write a binding by hand on only one element.
- **Randomize identity per element.** `id`, `seed`, and `versionNonce` are unique per element. Never duplicate an element without minting a fresh `id` and new random `seed`/`versionNonce`: duplicate ids break selection and binding; duplicate seeds make roughjs render the two shapes as visually identical.
- **Points are relative and self-consistent.** A linear element's `points` are offsets from its own `x`/`y`; the first point is `[0, 0]`; `width`/`height` equal the bounding box of the points. Putting absolute coordinates in `points` is the single most common corruption.
- **Never hand-type element JSON — generate it, then validate it.** Build every element through the factory (correct defaults, randomized fields), and run [the validator](references/validating.md) before telling the user it's done. Treat an unvalidated file as unfinished.
- **Round-trip preserves unknown fields.** When modifying, parse → mutate only the fields you intend → re-serialize. Do not drop fields you didn't recognize; Excalidraw evolves and unknown keys are meaningful.
- **Deleting means removing references too.** Prefer splicing an element out of `elements`; then strip every dangling reference to its id from other elements' `boundElements`, `startBinding`/`endBinding`, and `containerId`. A dangling binding is a latent crash.
- **Moving is a graph operation.** Moving a shape means updating its bound label's position and re-deriving the endpoints of every arrow bound to it. Don't move a box and leave its arrows pointing at empty space.
- **Enums are closed sets.** `strokeWidth ∈ {1, 2, 4}`, `roughness ∈ {0, 1, 2}`, plus the `fillStyle` / `strokeStyle` / `fontFamily` enums (see [schema.md](references/schema.md)). A fill only shows when `backgroundColor` is not `"transparent"`.
- **Work in `/tmp`; write the deliverable only where asked.** Recipe scripts and scratch JSON go to `/tmp`; the final `.excalidraw` is written only to the user's requested path.
- **Export is out-of-process.** SVG/PNG need a browser/DOM. Document the external tool; never assert you produced a raster image in-skill.

## Workflow

Pick the track that matches the request. All tracks share the same setup — write the recipe scripts to `/tmp` and run them with `node` — and **every create or modify run ends at the validator**. The load-bearing recipes (the factory, `connect`, the validator, the summarizer) live in the reference files; write them to `/tmp` verbatim and run them.

### Track A — Inspect & Extract

1. Load the file (Read tool for small files; `node`/`jq` for large ones).
2. Run the summarize recipe to get counts by type, extracted text, the edge list, and the bounding box.
3. Answer specific questions with `jq`/`node` filters (find by type, by text, by group; list arrows and what they connect; find dangling references).
4. Optionally run the validator as a health report on a file you didn't create.

```sh
# counts by type, all free-standing text, and the connection (edge) list:
jq '.elements | group_by(.type) | map({type: .[0].type, count: length})' drawing.excalidraw
node /tmp/summarize.js drawing.excalidraw   # -> {counts, texts, edges, bbox}
```

Detail and more query patterns in [inspecting.md](references/inspecting.md).

### Track B — Create from scratch

1. Clarify the shapes, labels, and layout with the user if ambiguous.
2. Write the factory ([creating.md](references/creating.md)) to `/tmp/exc.js` and the geometry helpers ([layout-and-binding.md](references/layout-and-binding.md)) to `/tmp/connect.js`.
3. Build in dependency order: **shapes first → labels → arrows last** (so the ids exist to bind against). Use `connect(elements, fromId, toId)` for bound arrows and `addLabel(elements, shapeId, text)` for labels.
4. Wrap with `file(elements)` and write the `.excalidraw` to the requested path.
5. **Validate** (`node /tmp/validate.js out.excalidraw`).
6. Report, and tell the user to open it via excalidraw.com → File → Open (or drag-drop).

```sh
# a quick vertical flowchart from a list of labels:
node -e "const {flow}=require('/tmp/connect.js'); \
  require('fs').writeFileSync('out.excalidraw', JSON.stringify(flow(['Start','Work','Done']), null, 2));"
node /tmp/validate.js out.excalidraw
```

### Track C — Modify existing

1. Load and summarize (Track A) to understand the current graph.
2. Locate the target element(s) by id, text, or type.
3. Apply the mutation, **preserving every field you're not changing** (parse → mutate → re-serialize).
4. Repair dependent references: bound-arrow endpoints when a shape moves, label position, and the `boundElements` on both ends of any binding you add or remove.
5. Write back and **validate**.

Detail — add / remove / move / restyle / connect / relabel / group — in [modifying.md](references/modifying.md).

### Track D — Convert / Export

- **Mermaid → Excalidraw.** For simple `graph TD/LR` / `flowchart`, parse the nodes and edges and rebuild with the factory (`shape` + `addLabel` + `connect`) — reliable, no DOM needed. For richer diagrams, use the external `@excalidraw/mermaid-to-excalidraw` package (heavier; needs a DOM via `jsdom`).
- **Export to SVG/PNG.** Out-of-process. Offer the external `npx` tools (`excalidraw-to-svg`, `excalidraw_export`) or excalidraw.com → File → Export, then stop. Never claim to have produced the image yourself.

Detail in [converting-exporting.md](references/converting-exporting.md). This is the shortest track by design.

## Examples

### Example 1 — Generate a 3-node vertical flowchart from a list

User: "make me an excalidraw flowchart: Start → Work → Done."

Write `/tmp/exc.js` and `/tmp/connect.js`, then:

```sh
node -e "const {flow}=require('/tmp/connect.js'); \
  require('fs').writeFileSync('flow.excalidraw', JSON.stringify(flow(['Start','Work','Done']), null, 2));"
node /tmp/validate.js flow.excalidraw   # {ok:true, elementCount:8, errors:[]}
```

Result: 3 rounded rectangles, each with a centered bound label, connected top-to-bottom by 2 bound arrows — 8 elements, validated. Report the path and how to open it.

### Example 2 — Add a labeled box and connect it into an existing file

User: "add a 'Cache' box after the 'API' node and wire API → Cache."

Load `diagram.excalidraw`; find the `API` node's id (by its bound label text). Then, in a script that requires `/tmp/exc.js` + `/tmp/connect.js`: `const s = shape('rectangle', apiNode.x, apiNode.y + 140, 200, 64); els.push(s); addLabel(els, s.id, 'Cache'); connect(els, apiNode.id, s.id);` — write back and validate. `connect`/`addLabel` update `boundElements` on both ends automatically.

### Example 3 — Inspect and report structure + text

User: "what does this diagram show?"

```sh
node /tmp/summarize.js drawing.excalidraw
```

Report the node/edge outline from `edges` (e.g. `Start -> Work`, `Work -> Done`), the free-standing `texts`, the per-type `counts`, and the overall `bbox`. See [inspecting.md](references/inspecting.md) for pulling group/frame structure.

### Example 4 — Convert simple Mermaid

User: "turn `graph TD; A[Start]-->B{Check}-->C[Done]` into excalidraw."

Parse the node declarations (`A[Start]` → rectangle, `B{Check}` → diamond, `C[Done]` → rectangle) and the `-->` edges, then rebuild with `shape` + `addLabel` + `connect`, laying nodes out top-down. Validate. Full parser in [converting-exporting.md](references/converting-exporting.md).

## Troubleshooting

| Symptom | Reference |
|---|---|
| Arrow renders detached / floats away when a shape moves | [layout-and-binding.md](references/layout-and-binding.md) (bidirectional binding + geometry) |
| File won't open / "cannot read properties" in Excalidraw | [validating.md](references/validating.md) (missing required field, bad enum, dup id) |
| Two shapes look identical / selection grabs the wrong one | [creating.md](references/creating.md) (randomize `id`/`seed`/`versionNonce`) |
| Arrow starts at the wrong place / wrong length | [layout-and-binding.md](references/layout-and-binding.md) (points are relative; first `[0,0]`) |
| Label sits outside its shape | [layout-and-binding.md](references/layout-and-binding.md) (center + `containerId` back-ref) |
| Deleted a shape but arrows still point at it | [modifying.md](references/modifying.md) (strip dangling references) |
| Mermaid conversion loses layout | [converting-exporting.md](references/converting-exporting.md) (factory rebuild vs. package) |
| Asked for a PNG and got JSON | [converting-exporting.md](references/converting-exporting.md) (export is out-of-process) |

## Topic References

- [Schema](references/schema.md) — the `.excalidraw` file format field by field: the top-level object, the shared element base (with defaults and which fields are randomized), the enum tables, the per-subtype addenda (text / linear / freedraw / image / frame), the binding model, the fractional `index`, and the default palette. The single source of truth every other reference points back to.
- [Inspecting](references/inspecting.md) — Track A: loading, the summarize recipe (counts / text / edges / bbox), and query patterns (find by type/text/group/frame, list connections, find orphaned references).
- [Creating](references/creating.md) — Track B: the element factory (`base`/`shape`/`text`/`addLabel`/`file`), the build-order discipline (shapes → labels → arrows), a worked end-to-end build, and the flowchart auto-layout helper.
- [Modifying](references/modifying.md) — Track C: the load → mutate-in-place → re-serialize round-trip; add / remove (with reference cleanup) / move (with binding repair) / restyle / connect / relabel / group; always ending at the validator.
- [Layout and Binding](references/layout-and-binding.md) — the shared geometry: the `connect` bound-arrow recipe (box-edge intersection, gap, focus, both-sided `boundElements`), label centering + binding, grouping and z-order/`index`, and alignment/distribution math.
- [Validating](references/validating.md) — the correctness gate: the full validator recipe, the invariant catalog it enforces, and how to read and act on its `{ok, errors, warnings}` output. Run after every create or modify.
- [Converting and Exporting](references/converting-exporting.md) — Track D: Mermaid → Excalidraw (in-skill factory rebuild vs. the official package), and SVG/PNG export as an out-of-process step (external `npx` tools or the web UI) — with an explicit "never claim to have rasterized in-skill."
