# The Skeleton API (`convertToExcalidrawElements`)

Excalidraw ships an **official** simplified authoring format — the [`ExcalidrawElementSkeleton`](https://github.com/excalidraw/excalidraw/blob/master/packages/element/src/transform.ts) — plus a converter that expands it into fully-qualified elements. A skeleton carries only the interesting fields (`type`, `x`, `y`, a `label`, a `start`/`end` binding); the converter fills in ids, seeds, version nonces, `points`, label centering, both halves of every binding, and frame bounds using Excalidraw's own code.

**Read the scope note before you plan around it.** `convertToExcalidrawElements` runs in a **bundler or browser** context — it is what you call when you are writing app code that mounts `<Excalidraw>`. It does **not** load under plain `node`, with or without `jsdom`; see [Where this API actually runs](#where-this-api-actually-runs) for the verified failure modes. So:

| You are… | Use |
|---|---|
| writing app code that renders `<Excalidraw>` | `convertToExcalidrawElements` — this file documents it |
| producing a `.excalidraw` **file on disk** from Node | the [factory](creating.md), or the [local expander](#skeleton-shape-without-the-dependency) below, which takes the same skeleton shape |

The skeleton is worth knowing either way: it is the vocabulary Excalidraw's own tooling speaks (`@excalidraw/mermaid-to-excalidraw` emits skeletons, not elements), and it is the clearest description of what a "correct" element graph looks like — a `label` instead of a hand-wired text binding, a `start`/`end` instead of hand-computed arrow geometry.

> **Beta.** The API has been stable in practice since [PR #6546](https://github.com/excalidraw/excalidraw/pull/6546), but upstream still labels it beta and reserves the right to change it. Pin the version you test against.

## Signature

```ts
convertToExcalidrawElements(
  elements: ExcalidrawElementSkeleton[] | null,
  opts?: { regenerateIds: boolean },   // default: { regenerateIds: true }
): ExcalidrawElement[]
```

```js
import { convertToExcalidrawElements } from "@excalidraw/excalidraw";
```

- **`elements` is an array.** (The published docs page writes the parameter type in the singular — `elements: ExcalidrawElementSkeleton` — but the implementation takes `ExcalidrawElementSkeleton[]`.) Passing `null` returns `[]`.
- **`opts.regenerateIds` defaults to `true`**, so *every* element comes back with a freshly minted id even for skeletons where you supplied one. Your ids still work as cross-references — the converter maps old → new internally for `start.id`, `end.id`, and frame `children` — but the ids in the **output** are not the ones you wrote. Pass `{ regenerateIds: false }` when you need to address the result by your own ids afterwards (e.g. a second pass that edits specific elements).
- The return value is an array of ordinary Excalidraw elements: hand it to `initialData.elements` / `updateScene`, or drop it straight into the `elements` array of a `.excalidraw` file ([schema.md](schema.md)).

## Supported skeleton types

| `type` | Required | What the converter fills in |
|---|---|---|
| `rectangle` / `ellipse` / `diamond` | `type`, `x`, `y` | `width`/`height` default to **100**. With a `label` and no explicit size, the container is **auto-sized to fit the text** instead. |
| `text` | `type`, `x`, `y`, `text` | `width`/`height` measured from the string; `fontFamily` defaults to `5` (Excalifont), `fontSize` to `20`. |
| `line` | `type`, `x`, `y` | `width` **100**, `height` **0**, `points: [[0,0],[w,h]]`. |
| `arrow` | `type`, `x`, `y` | Same defaults as `line`, plus `endArrowhead: "arrow"`. Accepts `label`, `start`, `end`. |
| `image` | `type`, `x`, `y`, `fileId` | `width`/`height` default to **100**. The bytes must exist separately in the scene's `files[fileId]` — the converter does not create them. |
| `frame` | `type`, `children` (array of ids) | `x`/`y`/`width`/`height` computed from the children's bounding box **+ 10px padding**, unless you set them. `name` optional. |
| `magicframe` | `type`, `children` | Same as `frame`. |
| `freedraw` / `iframe` / `embeddable` | *(a complete element)* | **Nothing.** These have no simplified form — they are passed through unchanged, so supply fully-qualified elements per [schema.md](schema.md). |

Any other field from the real element type may be added to decorate the shape (`backgroundColor`, `strokeStyle`, `roughness`, `opacity`, `angle`, …), staying inside the [enums](schema.md).

## Labels — text containers and labelled arrows

`label` is the skeleton's headline convenience. It works on `rectangle` / `ellipse` / `diamond` **and on `arrow`**:

```js
convertToExcalidrawElements([
  { type: "rectangle", x: 300, y: 290, label: { text: "RECTANGLE TEXT CONTAINER" } },
  { type: "diamond", x: -120, y: 100, width: 270, backgroundColor: "#fff3bf",
    label: { text: "STYLED DIAMOND", strokeColor: "#099268", fontSize: 20 } },
  { type: "arrow", x: 100, y: 100, label: { text: "LABELED ARROW" } },
]);
```

- `label.text` is required; `fontSize`, `fontFamily`, `textAlign`, `verticalAlign`, `strokeColor` and the other text props are optional.
- The label defaults to centered/middle, and **inherits the container's `strokeColor`** unless you override it.
- The converter writes *both* halves of the binding (`containerId` on the text, `{id, type:"text"}` in the container's `boundElements`) — the same invariant [validate.js](validating.md) enforces.
- Omit the container's `width`/`height` to let it size itself around the label.

> **`label` is a skeleton-only field.** It is not part of the `.excalidraw` element schema. A `label` still sitting on an element in a saved file means the skeleton was never converted — the shape renders blank. See the note in [schema.md](schema.md).

## Arrow bindings — `start` and `end`

Give an arrow a `start` and/or `end` and the converter creates or looks up the endpoint shape and binds to it. Each takes **either `type` or `id`** (or both):

```js
// (a) by type — the endpoint shapes are created for you
convertToExcalidrawElements([
  { type: "arrow", x: 255, y: 239, label: { text: "HELLO WORLD!!" },
    start: { type: "rectangle" }, end: { type: "ellipse" } },
]);

// (b) by id — bind several arrows into shapes declared in the same array
convertToExcalidrawElements([
  { type: "ellipse", id: "ellipse-1", x: 390, y: 356, width: 150, height: 150,
    strokeColor: "#66a80f", backgroundColor: "#d8f5a2" },
  { type: "diamond", id: "diamond-1", x: -30, y: 380, width: 100, strokeColor: "#9c36b5" },
  { type: "arrow", x: 60, y: 420, width: 330, strokeColor: "#e67700",
    start: { id: "diamond-1" }, end: { id: "ellipse-1" } },
]);
```

- **Bindable endpoint types:** `rectangle`, `ellipse`, `diamond`, and `text` (`{type: "text", text: "…"}` creates a bound text endpoint). `image`, `frame`, `magicframe`, `embeddable` and `iframe` are **not** valid endpoints.
- **Placement when you omit coordinates** — endpoints are positioned relative to the arrow: `start` at `(arrow.x - width, arrow.y - height/2)`, `end` at `(arrow.x + arrow.width, arrow.y - height/2)`, with `width`/`height` defaulting to 100. Set `x`/`y`/`width`/`height` *inside* `start`/`end` to override.
- **An `id` that doesn't resolve is not fatal** — the converter logs `No element for start binding with id … found` to the console and skips the binding. Nothing throws, so check stderr and count your output.
- Declaration order does not matter for `id` binding: all elements are created first, bindings are resolved in a second pass.

## Frames

```js
convertToExcalidrawElements([
  { type: "rectangle", x: 10, y: 10, strokeWidth: 2, id: "1" },
  { type: "diamond", x: 120, y: 20, backgroundColor: "#fff3bf", strokeWidth: 2, id: "2",
    label: { text: "HELLO EXCALIDRAW", strokeColor: "#099268", fontSize: 30 } },
  { type: "frame", children: ["1", "2"], name: "My frame" },
]);
```

- Every id in `children` must belong to an element in the same array — an unmapped id **throws** (unlike a bad arrow binding, which only logs).
- Children get `frameId` set, and so do their bound labels and arrows.
- Frames are processed last, after all children exist, so the bounding box is exact.
- Supplying `x`/`y`/`width`/`height` yourself overrides the computed box; omit all four to get the automatic fit.

## Gotchas

- **Duplicate input ids silently drop elements.** A repeated `id` logs `Duplicate id found for <id>` and the *later* element is discarded. Always compare `output.length` against what you expected.
- **It needs a DOM with a working canvas.** Text measurement calls `document.createElement("canvas").getContext("2d")`. In a browser that is free; under `jsdom`, `getContext` returns `null`. The package exports `setCustomTextMetricsProvider({ getLineWidth(text, fontString) })` to swap in your own width function — useful in a test harness, but it does not make the package loadable outside a bundler (next section).
- **The output is elements, not a scene.** Wrap it in the top-level file object yourself ([schema.md](schema.md)); `convertToExcalidrawElements` never produces `appState` or `files`.
- **Still validate.** The converter's output is schema-valid by construction, but the wrapping, the `files` map, and anything you post-process are yours. Finish at [validate.js](validating.md) like every other run.

## Where this API actually runs

The Skeleton API is built for a **bundler or browser** context — a React app that mounts `<Excalidraw>`, or any page that already loads the package. That is the shape every example on the docs page takes:

```jsx
import { Excalidraw, convertToExcalidrawElements } from "@excalidraw/excalidraw";

const elements = convertToExcalidrawElements([
  { type: "rectangle", x: 100, y: 250, label: { text: "API" } },
  { type: "ellipse", x: 100, y: 400, label: { text: "Cache" } },
]);

<Excalidraw initialData={{ elements, appState: { zenModeEnabled: true }, scrollToContent: true }} />
```

The same array also goes to `excalidrawAPI.updateScene({ elements })` on an already-mounted editor.

**It does not run under plain `node`, with or without `jsdom`.** Verified against `@excalidraw/excalidraw@0.18.1` on Node 25: the published bundle targets a bundler's resolver and fails three independent ways — it imports `open-color/open-color.json` without `with { type: "json" }`, it imports some dependencies extensionless (`roughjs/bin/rough`), and requiring it trips a named-export interop error on `@excalidraw/laser-pointer`. The split-out `@excalidraw/element` package is no better: its sub-packages don't expose their runtime subpaths through `exports`. So do not write a recipe that `require`s it from Node, and do not claim one works. If you need a `.excalidraw` file **on disk**, use the expander below or the [factory](creating.md) directly.

## Skeleton shape without the dependency

You can still author in the skeleton's ergonomics and expand locally. Write this to `/tmp/skeleton.js` (it needs `/tmp/exc.js` and `/tmp/connect.js`):

```js
// /tmp/skeleton.js — expand ExcalidrawElementSkeleton-shaped JSON with the local
// factory. Requires /tmp/exc.js and /tmp/connect.js. See references/skeleton-api.md.
const { base, shape, text, addLabel, file } = require('/tmp/exc.js');
const { connect } = require('/tmp/connect.js');

const DIM = 100, LINE_W = 100, LINE_H = 0, PAD = 8, FRAME_PAD = 10;

function labelBox(label) {                       // size a container around its label
  const t = text(label.text, 0, 0, label);
  return { width: Math.max(t.width + 2 * PAD, DIM), height: Math.max(t.height + 2 * PAD, 50) };
}

function expand(skeletons, opts = {}) {
  const els = [], pairs = [];                     // pairs: [skeleton, element]
  const byKey = new Map();                        // skeleton id -> real element
  const deferred = [];

  for (const sk of skeletons) {
    let el;
    switch (sk.type) {
      case 'rectangle': case 'ellipse': case 'diamond': {
        const auto = sk.label?.text && sk.width === undefined && sk.height === undefined
          ? labelBox(sk.label) : null;
        const { type, x, y, label, id, ...rest } = sk;
        el = shape(type, x, y, sk.width ?? auto?.width ?? DIM,
                             sk.height ?? auto?.height ?? DIM, rest);
        break;
      }
      case 'text': {
        const { type, x, y, text: str, id, ...rest } = sk;
        el = text(str, x, y, rest);
        break;
      }
      case 'line': case 'arrow': {
        const w = sk.width ?? LINE_W, h = sk.height ?? LINE_H;
        const { type, x, y, label, start, end, id, ...rest } = sk;
        el = base({
          type, x, y, width: Math.abs(w), height: Math.abs(h),
          points: [[0, 0], [w, h]], lastCommittedPoint: null, roundness: { type: 2 },
          startArrowhead: null, endArrowhead: type === 'arrow' ? 'arrow' : null,
          startBinding: null, endBinding: null, ...rest,
        });
        break;
      }
      case 'frame': deferred.push(sk); continue;
      default: throw new Error(`skeleton type "${sk.type}" not supported by this expander`);
    }
    if (opts.regenerateIds === false && sk.id) el.id = sk.id;
    els.push(el);
    pairs.push([sk, el]);
    if (sk.id) byKey.set(sk.id, el);
  }

  // pass 2 — labels and arrow bindings, once every id exists
  for (const [sk, el] of pairs) {
    if (sk.type === 'arrow') {
      for (const [side, spec] of [['start', sk.start], ['end', sk.end]]) {
        if (!spec) continue;
        let target = spec.id ? byKey.get(spec.id) : null;
        if (!target && spec.type && spec.type !== 'text') {
          const w = spec.width ?? DIM, h = spec.height ?? DIM;
          const x = spec.x ?? (side === 'start' ? el.x - w : el.x + el.width);
          const y = spec.y ?? el.y - h / 2;
          target = shape(spec.type, x, y, w, h, spec);
          els.push(target);
          if (spec.id) byKey.set(spec.id, target);
        }
        if (!target) { console.error(`no element for ${side} binding ${JSON.stringify(spec)}`); continue; }
        el[`${side}Binding`] = { elementId: target.id, focus: 0, gap: PAD };
        target.boundElements = (target.boundElements || []).concat({ id: el.id, type: 'arrow' });
      }
      // both ends known -> re-derive clean geometry with connect()
      const a = el.startBinding && els.find(e => e.id === el.startBinding.elementId);
      const b = el.endBinding && els.find(e => e.id === el.endBinding.elementId);
      if (a && b) {
        a.boundElements = a.boundElements.filter(x => x.id !== el.id);
        b.boundElements = b.boundElements.filter(x => x.id !== el.id);
        els.splice(els.indexOf(el), 1);
        const arrow = connect(els, a.id, b.id, { gap: PAD });
        Object.assign(arrow, { strokeColor: el.strokeColor, strokeWidth: el.strokeWidth });
        if (sk.label?.text) addLabel(els, arrow.id, sk.label.text, sk.label);
        continue;
      }
    }
    if (sk.label?.text) addLabel(els, el.id, sk.label.text, sk.label);
  }

  // pass 3 — frames, after their children have final geometry
  for (const sk of deferred) {
    const kids = sk.children.map(k => {
      const e = byKey.get(k);
      if (!e) throw new Error(`frame child "${k}" wasn't mapped — no skeleton declared that id`);
      return e;
    });
    const owned = [...kids];
    for (const k of kids) for (const b of (k.boundElements || [])) {
      const e = els.find(x => x.id === b.id); if (e) owned.push(e);
    }
    const minX = Math.min(...owned.map(e => e.x)) - FRAME_PAD;
    const minY = Math.min(...owned.map(e => e.y)) - FRAME_PAD;
    const maxX = Math.max(...owned.map(e => e.x + e.width)) + FRAME_PAD;
    const maxY = Math.max(...owned.map(e => e.y + e.height)) + FRAME_PAD;
    const frame = base({
      type: 'frame', name: sk.name ?? null,
      x: sk.x ?? minX, y: sk.y ?? minY,
      width: sk.width ?? maxX - minX, height: sk.height ?? maxY - minY,
    });
    for (const e of owned) e.frameId = frame.id;
    els.unshift(frame);
  }
  return els;
}

module.exports = { expand, expandToFile: (s, o) => file(expand(s, o)) };
```

```sh
node -e "const {expandToFile}=require('/tmp/skeleton.js'); const fs=require('fs');
  fs.writeFileSync('out.excalidraw', JSON.stringify(
    expandToFile(JSON.parse(fs.readFileSync('/tmp/skeleton.json','utf8'))), null, 2));"
node /tmp/validate.js out.excalidraw
```

**Coverage.** `rectangle` / `ellipse` / `diamond` / `text` / `line` / `arrow` / `frame`, with `label`, `start` / `end` (by `id` or by `type`), and `opts.regenerateIds`. Unsupported skeleton types throw rather than emit something wrong — `image`, `magicframe`, `embeddable`, `iframe`, `freedraw` — build those with the factory.

**Deliberate deviations from upstream**, so you don't expect identical output:

- **Arrow geometry.** When both endpoints resolve to shapes, the arrow's own `x`/`y`/`width`/`height` are discarded and re-derived with [`connect`](layout-and-binding.md) — box-edge intersection with a gap, which looks right without hand-tuning. Upstream keeps the coordinates you supplied. An arrow with one free end keeps its skeleton geometry.
- **Container auto-size.** A labelled container with no explicit size gets the label's *estimated* box plus padding, floored at 100×50; upstream measures the real font.
- Everything else matches the semantics above: `regenerateIds` defaults to `true`, missing binding ids log and skip, a frame child that was never declared throws, frames fit their children with 10px padding, and both halves of every binding are written.

The `skeletons → elements` count is the cheap sanity check either way: labels and auto-created arrow endpoints *add* elements. Then, as always, finish at [validate.js](validating.md).
