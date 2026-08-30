# Validating

The correctness gate. Run it after **every** create or modify run — a file that hasn't passed the validator is unfinished. It can also serve as a health check on a file you didn't produce (Track A).

## The validator recipe

Write to `/tmp/validate.js`. Prints `{ok, elementCount, errors, warnings}` and exits `1` if there are any errors, `0` otherwise — so it works both as a report and as a shell gate (`node /tmp/validate.js f.excalidraw && echo pass`).

```js
// node /tmp/validate.js file.excalidraw  -> prints {ok, errors, warnings}; exit 1 on error.
const doc = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const errors = [], warnings = [];

if (doc.type !== 'excalidraw') errors.push(`top-level type must be "excalidraw", got ${JSON.stringify(doc.type)}`);
if (doc.version !== 2) warnings.push(`top-level version is ${doc.version} (expected 2)`);
if (!Array.isArray(doc.elements)) { console.log(JSON.stringify({ ok: false, errors: ['elements missing'] })); process.exit(1); }

const els = doc.elements, byId = new Map();
for (const e of els) { if (byId.has(e.id)) errors.push(`duplicate id: ${e.id}`); byId.set(e.id, e); }

const ENUMS = { fillStyle: ['solid', 'hachure', 'cross-hatch', 'zigzag'],
                strokeStyle: ['solid', 'dashed', 'dotted'], strokeWidth: [1, 2, 4], roughness: [0, 1, 2] };
const REQ = ['id', 'type', 'x', 'y', 'width', 'height', 'angle', 'strokeColor', 'backgroundColor',
  'fillStyle', 'strokeWidth', 'strokeStyle', 'roughness', 'opacity', 'groupIds',
  'seed', 'version', 'versionNonce', 'isDeleted'];

for (const e of els) {
  const at = `element ${e.id} (${e.type})`;
  for (const k of REQ) if (!(k in e)) errors.push(`${at}: missing required field "${k}"`);
  for (const [k, ok] of Object.entries(ENUMS))
    if (k in e && !ok.includes(e[k])) errors.push(`${at}: ${k}=${JSON.stringify(e[k])} not in {${ok.join(',')}}`);
  if ('label' in e) errors.push(`${at}: has a "label" property — that is a Skeleton-only field; run convertToExcalidrawElements or bind a text element via containerId`);
  if (typeof e.seed !== 'number')         errors.push(`${at}: seed must be a number`);
  if (typeof e.versionNonce !== 'number') errors.push(`${at}: versionNonce must be a number`);
  if (!Array.isArray(e.groupIds))         errors.push(`${at}: groupIds must be an array`);

  if (e.type === 'arrow' || e.type === 'line') {
    if (!Array.isArray(e.points) || e.points.length < 2) errors.push(`${at}: needs >=2 points`);
    else if (e.points[0][0] !== 0 || e.points[0][1] !== 0)
      warnings.push(`${at}: first point ${JSON.stringify(e.points[0])} should be [0,0] (points are relative)`);
  }

  if (e.type === 'text' && e.containerId) {
    const c = byId.get(e.containerId);
    if (!c) errors.push(`${at}: containerId ${e.containerId} not found`);
    else if (!(c.boundElements || []).some(b => b.id === e.id && b.type === 'text'))
      errors.push(`${at}: container ${e.containerId} does not back-reference this text (binding not bidirectional)`);
  }

  for (const b of (e.boundElements || [])) {
    const t = byId.get(b.id);
    if (!t) { errors.push(`${at}: boundElements references missing id ${b.id}`); continue; }
    if (b.type === 'text' && t.containerId !== e.id)
      errors.push(`${at}: lists text ${b.id}, but its containerId is ${JSON.stringify(t.containerId)}`);
    if (b.type === 'arrow' &&
        !((t.startBinding && t.startBinding.elementId === e.id) ||
          (t.endBinding   && t.endBinding.elementId   === e.id)))
      errors.push(`${at}: lists arrow ${b.id}, but that arrow binds neither end to ${e.id}`);
  }

  for (const [end, bnd] of [['startBinding', e.startBinding], ['endBinding', e.endBinding]]) {
    if (!bnd) continue;
    const s = byId.get(bnd.elementId);
    if (!s) { errors.push(`${at}: ${end}.elementId ${bnd.elementId} not found`); continue; }
    if (!(s.boundElements || []).some(b => b.id === e.id && b.type === 'arrow'))
      errors.push(`${at}: ${end} binds ${bnd.elementId} but that shape omits this arrow from boundElements (not bidirectional)`);
  }
}

console.log(JSON.stringify({ ok: errors.length === 0, elementCount: els.length, errors, warnings }, null, 2));
process.exit(errors.length ? 1 : 0);
```

## The invariant catalog

Errors (file is wrong; fix before shipping):

- **Top-level shape** — `type === "excalidraw"`, `elements` is an array.
- **Unique ids** — no two elements share an `id`.
- **Required base fields** — every element has all of them ([schema.md](schema.md)).
- **Closed enums** — `fillStyle` / `strokeStyle` / `strokeWidth` / `roughness` are in range.
- **Numeric identity** — `seed` and `versionNonce` are numbers; `groupIds` is an array.
- **Linear points** — arrows/lines have ≥2 points.
- **No unconverted skeletons** — no element carries a `label` property (valid as *input* to `convertToExcalidrawElements`, never valid in a saved file; see [skeleton-api.md](skeleton-api.md)).
- **Text↔container bidirectional** — a text's `containerId` resolves *and* that container lists the text in `boundElements`.
- **`boundElements` reciprocate** — every entry resolves, and the target actually points back (text via `containerId`, arrow via one of its bindings).
- **Arrow bindings reciprocate** — every `startBinding`/`endBinding.elementId` resolves *and* that shape lists the arrow in `boundElements`.

Warnings (usually a mistake, occasionally legitimate):

- **`version !== 2`** — older/newer schema; typically fine, but check.
- **First point not `[0,0]`** — the classic "absolute coordinates in `points`" corruption; the arrow will render offset. Fix by rebasing points to the element origin (or regenerate with `connect`).

## Reading the output

```jsonc
{ "ok": true,  "elementCount": 8, "errors": [], "warnings": [] }   // ship it
{ "ok": false, "elementCount": 8,
  "errors": [ "element <id> (arrow): startBinding binds <id> but that shape omits this arrow from boundElements (not bidirectional)" ] }
```

Each error names the offending element and the exact broken invariant. The most common ones and their fixes:

| Error | Fix |
|---|---|
| `…not bidirectional` (arrow or text) | Add the missing back-reference — push `{id, type}` into the shape's `boundElements`, or set the text's `containerId`. Prefer regenerating via `connect`/`addLabel`, which never leave one side out. |
| `duplicate id` | Re-mint the id (and `seed`/`versionNonce`) with the factory; never copy an element without minting fresh identity. |
| `has a "label" property` | The skeleton was written straight to disk. Run it through `convertToExcalidrawElements` ([skeleton-api.md](skeleton-api.md)), or replace the `label` with an `addLabel` text binding. |
| `…not in {…}` (enum) | Snap the value to a legal enum member ([schema.md](schema.md)). |
| `boundElements references missing id` / `elementId not found` | A dangling reference — the target was deleted. Strip the stale entry (see [modifying.md](modifying.md) delete rules). |
| `first point … should be [0,0]` (warning) | Rebase `points` so the first is `[0,0]` and `x`/`y` absorb the offset. |

If the validator passes, the file's graph is internally consistent and will open. For the strongest possible check (feeding the elements through Excalidraw's own `restore()`), see [converting-exporting.md](converting-exporting.md).
