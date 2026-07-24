# Schema

The ground truth for the `.excalidraw` format. Every other reference points back here. When in doubt about a field's name, type, or default, this is the file.

## The top-level file object

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [ /* array of element objects, drawn in array order */ ],
  "appState": {
    "gridSize": null,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```

- `type` — always the literal string `"excalidraw"` (a scene file). The clipboard uses `"excalidraw/clipboard"`; a library uses `"excalidrawlib"` — both out of scope here.
- `version` — the schema version; `2` for current files.
- `source` — provenance URL; `"https://excalidraw.com"` is fine.
- `elements` — the array of elements. **Array order is z-order** (later = on top), unless `index` says otherwise.
- `appState` — editor state. Only two keys matter for generated files: `gridSize` (`null` or a number like `20`) and `viewBackgroundColor` (`"#ffffff"`). Excalidraw fills the rest on load; do not fabricate the dozens of other appState keys.
- `files` — image blob store, keyed by `fileId`. `{}` when there are no images. See the image subtype below.

## The shared element base

Every element — regardless of type — carries this base. Defaults shown are the Excalidraw defaults the factory uses; the three **randomized** fields are called out.

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | string | *(random)* | Unique per element. Any unique string; Excalidraw uses a ~21-char nanoid. |
| `type` | string | — | `rectangle` / `ellipse` / `diamond` / `text` / `arrow` / `line` / `freedraw` / `image` / `frame`. |
| `x`, `y` | number | — | Top-left of the element's bounding box, in scene coordinates. |
| `width`, `height` | number | — | Bounding-box size. For linear elements this must equal the bbox of `points`. |
| `angle` | number | `0` | Rotation in **radians**. |
| `strokeColor` | string | `"#1e1e1e"` | Stroke/text color. |
| `backgroundColor` | string | `"transparent"` | Fill color. Fill only shows when this is not `"transparent"`. |
| `fillStyle` | enum | `"solid"` | `solid` / `hachure` / `cross-hatch` / `zigzag`. |
| `strokeWidth` | enum | `2` | `1` (thin) / `2` (bold) / `4` (extra-bold). |
| `strokeStyle` | enum | `"solid"` | `solid` / `dashed` / `dotted`. |
| `roughness` | enum | `1` | `0` (architect) / `1` (artist) / `2` (cartoonist) — roughjs hand-drawn amount. |
| `opacity` | number | `100` | `0`–`100`. |
| `groupIds` | string[] | `[]` | Group membership; see [layout-and-binding.md](layout-and-binding.md). |
| `frameId` | string \| null | `null` | Owning frame's id, if inside a frame. |
| `roundness` | object \| null | `null` | `null` = sharp; `{type: 3}` = rounded rectangle; `{type: 2}` = rounded linear/arrow. |
| `seed` | number | *(random)* | 32-bit int. Seeds roughjs; **must differ per element** or shapes render identically. |
| `version` | number | `1` | Bumped by the editor on each edit; `1` is fine for generated elements. |
| `versionNonce` | number | *(random)* | 32-bit int used for reconciliation; **randomize per element**. |
| `isDeleted` | boolean | `false` | Soft-delete flag. Deleted elements stay in the array but don't render. |
| `boundElements` | array \| null | `null` | Back-references: `[{id, type: "text" \| "arrow"}]`. The other half of every binding. |
| `updated` | number | *(timestamp)* | Epoch millis of last change. `Date.now()` is fine. |
| `link` | string \| null | `null` | Optional hyperlink. |
| `locked` | boolean | `false` | Locked elements can't be selected in the UI. |
| `index` | string \| null | *(optional)* | Fractional index (`"a0"`, `"a1"`, …). Usually omit — see below. |

### Enum quick reference

```
fillStyle    : solid | hachure | cross-hatch | zigzag
strokeStyle  : solid | dashed | dotted
strokeWidth  : 1 | 2 | 4
roughness    : 0 | 1 | 2
fontFamily   : 1 (Excalifont / hand-drawn) | 2 (Nunito / normal) | 3 (Comic Shanns / code)
roundness    : null | {type: 3}  (rectangles) | {type: 2}  (linear/arrow)
arrowhead    : null | "arrow" | "triangle" | "dot" | "bar" | "diamond"
textAlign    : left | center | right
verticalAlign: top | middle | bottom
```

## Subtype addenda

Fields each subtype adds on top of the base.

**`rectangle` / `diamond` / `ellipse`** — nothing beyond the base. (Rectangles conventionally set `roundness: {type: 3}` for rounded corners; diamonds and ellipses use `roundness: null`.)

**`text`**

| Field | Type | Default | Notes |
|---|---|---|---|
| `text` | string | — | The displayed text. |
| `originalText` | string | — | The unwrapped source text; keep in sync with `text`. |
| `fontSize` | number | `20` | 16 (S) / 20 (M) / 28 (L) / 36 (XL) are the UI presets, but any number is valid. |
| `fontFamily` | enum | `1` | See enum table. |
| `textAlign` | enum | `"left"` | `left` / `center` / `right`. |
| `verticalAlign` | enum | `"top"` | `top` / `middle` / `bottom`. For a bound label use `middle`. |
| `containerId` | string \| null | `null` | Id of the shape this text is a label *inside*. The other half is the container's `boundElements`. |
| `lineHeight` | number | `1.25` | Multiplier. |
| `autoResize` | boolean | `true` | Whether the box auto-fits the text. |

**`arrow` / `line`** (linear elements)

| Field | Type | Default | Notes |
|---|---|---|---|
| `points` | number[][] | — | Vertices **relative to the element's `x`/`y`**; first point is `[0, 0]`. |
| `lastCommittedPoint` | number[] \| null | `null` | Editor scratch; `null` is fine. |
| `startBinding` | object \| null | `null` | `{elementId, focus, gap}` — see the binding model below. |
| `endBinding` | object \| null | `null` | Same shape as `startBinding`. |
| `startArrowhead` | enum \| null | `null` | Arrowhead at the start. |
| `endArrowhead` | enum \| null | `"arrow"` (arrows) / `null` (lines) | Arrowhead at the end. |

`line` additionally has `polygon: boolean` in newer builds; `arrow` additionally has `elbowed: boolean`. Both are optional and default falsey — omit unless you need them.

**`freedraw`** — `points: number[][]`, `pressures: number[]`, `simulatePressure: boolean`. Rarely generated by hand; keep an existing freedraw's fields intact when modifying.

**`image`** — `fileId: string | null` (key into the top-level `files`), `status: "pending" | "saved" | "error"` (use `"saved"`), `scale: [number, number]` (`[1, 1]` normal; negatives flip). The actual bytes live in `files[fileId] = {mimeType, id, dataURL, created, lastRetrieved}` where `dataURL` is a base64 data URL.

**`frame`** — `name: string | null`. Child elements set their `frameId` to the frame's id.

## The binding model (read this twice)

Bindings are the only truly error-prone part of the format, because **each binding is stored on two elements and both must agree**.

**Arrow ↔ shape.** An arrow bound between shapes A and B has:

```json
{ "type": "arrow", "id": "arrow-1",
  "startBinding": { "elementId": "A", "focus": 0, "gap": 8 },
  "endBinding":   { "elementId": "B", "focus": 0, "gap": 8 } }
```

and *each* shape lists the arrow back:

```json
{ "type": "rectangle", "id": "A", "boundElements": [{ "id": "arrow-1", "type": "arrow" }] }
{ "type": "rectangle", "id": "B", "boundElements": [{ "id": "arrow-1", "type": "arrow" }] }
```

- `elementId` — the bound shape's id.
- `focus` — where along the shape the arrow attaches, roughly `-1`..`1`; `0` is centered. The editor recomputes this on drag, so `0` is a safe generated default.
- `gap` — pixels between the arrow endpoint and the shape's edge.

This is the **classic** binding shape and the most widely compatible. (Newer builds can also use `fixedPoint: [nx, ny]` normalized edge coordinates instead of `focus`/`gap`; prefer `focus`/`gap` unless you specifically need a pinned edge point.)

**Text ↔ container (label).** A label inside a shape:

```json
{ "type": "text", "id": "t-1", "containerId": "A", "verticalAlign": "middle", "textAlign": "center" }
{ "type": "rectangle", "id": "A", "boundElements": [{ "id": "t-1", "type": "text" }] }
```

**Never** use a `"label": {...}` property on a shape — it is not a valid Excalidraw field, is silently ignored, and produces a blank shape. Always use the `containerId` + `boundElements` container binding. The factory's `addLabel` and `connect` helpers ([creating.md](creating.md), [layout-and-binding.md](layout-and-binding.md)) write both sides for you.

## The `index` field (usually omit)

`index` is a **fractional index** — a short string like `"a0"`, `"a1"`, `"a2"` that gives a stable global z-order independent of array position. You can almost always **omit it**: Excalidraw's `restore()` backfills valid indices from array order on load. Only set indices explicitly if you need a z-order that differs from array order, and if you do, they must be strictly increasing in the intended stacking order.

## Default color palette

The Excalidraw default swatches, handy for coloring generated diagrams:

```
stroke / text : #1e1e1e (default)  #e03131 (red)  #2f9e44 (green)  #1971c2 (blue)  #f08c00 (orange)
background    : transparent (default)  #ffc9c9 (red)  #b2f2bb (green)  #a5d8ff (blue)  #ffec99 (yellow)
```

Set `backgroundColor` to a non-`transparent` value *and* a `fillStyle` to get a visible fill.
