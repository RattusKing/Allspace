# Floor Plan 2D → 3D Rendering — Diagnosis

_A full review of why Allspace renders floor plans inaccurately, with file:line
references and a remediation roadmap. This document describes the codebase **as it
actually is**, which differs significantly from what the other docs claim._

---

## Status (kept current)

- ✅ **Phase 1 — Docs**: the MiDaS/PyTorch/Open3D claims have been corrected across
  README and the setup guides.
- ✅ **Phase 2 — Quick wins**: aspect-ratio squash fixed, input cap raised 640→1024px
  with crisp (INTER_NEAREST) wall-mask downscaling, viewer given an isometric camera +
  neutral lighting + load/error handling, and the broken FBX download replaced with a
  real OBJ export. The `complexity`/`interiors` UI controls are now wired up.
  _Note: the GLB up-axis was investigated and found to be **correct** (exported Y-up
  with an identity transform) — that hypothesis from §"Bucket A" did not reproduce._
- ✅ **Phase 3 — Wall-detection robustness rebuilt**: `_floorplan_depth` now
  normalizes polarity (blueprints / dark-theme exports), thresholds adaptively with
  Otsu (grey / low-contrast walls), and keeps the connected wall network to drop
  text/furniture. A `mode=floor_plan` override lets users force the path when
  auto-detection misroutes. Measured on a synthetic style matrix, blueprint wall-mask
  IoU went 0.00 → 0.88 and noisy 0.71 → 0.80, with classic/grey/coloured holding 0.88.
  _Still open (true vectorization): walls are traced as blob outlines rather than
  centerlines, openings are inferred from pixel brightness, and automatic metric scale
  needs a detected scale bar/DPI rather than the 96 DPI assumption._

The analysis below documents the original state; line numbers refer to it.

---

## TL;DR

1. **The docs are wrong about the engine.** `README.md`, `RENDER-FIX.md`,
   `HF-SETUP.md`, and `test_setup.py` all describe a **MiDaS / PyTorch deep-learning
   depth model**. There is no PyTorch, no MiDaS, and no neural network anywhere in the
   code. `requirements.txt` is `trimesh + numpy + scipy + opencv + Pillow`. The real
   engine (`backend/models/depth_estimator.py`) is **hand-written classical computer
   vision**. Debugging this as if it were an AI model was chasing a ghost.

2. **The approach is _not_ fundamentally wrong.** There is a genuine floor-plan
   path that detects walls and **extrudes them into real 3D geometry**
   (`mesh_generator._architectural_mesh`), with door/window detection and per-room
   floors. This is salvageable — it is not "depth-mapping a photo into a lumpy
   heightfield."

3. **The inaccuracy comes from a chain of brittle heuristics plus presentation bugs.**
   Some of what looks "inaccurate" is actually the _viewer_ (camera/orientation/
   lighting) making a fine model look wrong. The rest is the wall detector being tuned
   to exactly one drawing style and one resolution.

---

## What the pipeline actually does (floor plan path)

| Step | Where | What happens |
|------|-------|--------------|
| 1. Upload | `app.py:157` (`POST /generate`) | Saves the image to `uploads/`. |
| 2. **Shrink** | `depth_estimator.py:46-54` | Image hard-resized so longest side = **640px**, before any analysis. |
| 3. Classify | `depth_estimator.py:127` (`_detect_scene_type`) | Heuristic guess: `floor_plan` / `building_facade` / `indoor_room` / photo, from brightness + saturation + Hough line counts. |
| 4. **Wall mask** | `depth_estimator.py:271` (`_floorplan_depth`) | Binary mask: threshold dark pixels (`gray < 120`) → morphology close → keep blobs by area. `1.0` = wall, `0.0` = floor. |
| 5. **Extrude** | `mesh_generator.py:382` (`_architectural_mesh`) | `findContours` on the mask → `approxPolyDP` → extrude each edge into vertical wall quads; detect openings; build per-room floor tiles. |
| 6. Export | `exporter.py:18` | Writes GLB (+ a broken FBX). |
| 7. Display | `index.html:612, 790` | Google `<model-viewer>` shows the GLB. |

---

## Root causes, ranked

### Bucket A — "Looks wrong even when geometry is OK" (cheap, high impact)

These are presentation bugs. A perfectly correct model can still look broken.

1. **Viewer never shows a top-down / isometric view.** `<model-viewer>` is given only
   `camera-controls shadow-intensity tone-mapping` (`index.html:612`) — no
   `camera-orbit`, `camera-target`, or `environment-image`. A floor plan auto-frames
   head-on and reads as a flat poster instead of a plan you can see into.

2. **Probable up-axis flip on GLB export.** Walls are authored Y-up (floor in XZ, walls
   rising +Y; `mesh_generator.py:422-479`), but `mesh.export(file_type='glb')`
   (`exporter.py:35`) can re-rotate that depending on trimesh's version → the plan
   loads standing on its edge. _(Verify empirically; symptom = "my plan is sideways.")_

3. **No load/error handling in the viewer** (`index.html:790-796`). A failed GLB load
   shows an empty scene that looks like a broken/inaccurate result.

### Bucket B — "The geometry itself is approximate" (the accuracy ceiling)

4. **640px downscale destroys thin walls** (`depth_estimator.py:46-54`). 1–2px CAD
   lines go sub-pixel and vanish before detection runs. Hard cap on achievable accuracy.

5. **Wall detection is a single global threshold** (`gray < 120`) + morphology + blob
   area filter (`depth_estimator.py:271-351`). Only works for dark walls on a clean
   white background near one DPI/scale. Blueprints, colored real-estate plans,
   gray-filled walls, and photographed plans all break it.

6. **Walls can't be told apart from furniture / text / dimensions.** They are separated
   only by connected-component _area_ (`depth_estimator.py:325-337`), so door swings,
   furniture, stair hatching, and large labels can extrude as phantom walls.

7. **Misclassification routes floor plans to a photo path → garbage.** A colored or blue
   plan fails the bright-white-background test (`depth_estimator.py:206-242`) and is
   handled as a landscape/photo heightfield. No manual override exists.

8. **Walls traced as blob _outlines_, not centerlines** (`mesh_generator.py:415-492`)
   with a fixed thickness `0.08` unrelated to the drawing. Rounds corners, inflates room
   sizes, can double up interior walls.

9. **Aspect ratio squashed in default ("auto") mode.** `scale_x = 2/w`, `scale_z = 2/h`
   (`mesh_generator.py:434-437`) force any plan into a square footprint regardless of the
   image's true proportions — a wide plan comes out square.

10. **Openings guessed from pixel brightness** along the wall (`mesh_generator.py:599`),
    so white paper / room interiors get mistaken for doors and windows.

11. **Scale is unreliable.** Real metres only when the user manually picks a scale, and
    it assumes a hard-coded 96 DPI (`app.py:193-202`).

---

## Secondary bugs (worth fixing, not the core issue)

- **FBX downloads are broken.** trimesh cannot write FBX, so `export_fbx` silently
  writes an `.obj` (`exporter.py:96-119`) while the job advertises a `.fbx` URL
  (`app.py:222`) that points to a file that was never created → 404 on download.
- **Three UI controls do nothing.** `complexity`, "interior elements", and
  `wall_thickness` are collected (`app.py:179-184`) but never read by the mesh generator.
- **Stale `test_setup.py`** checks for `torch`, `torchvision`, `open3d`
  (`test_setup.py:13-24`) — none are installed or used.
- **In-memory job store** (`app.py:43`) is lost on restart; valid output files become
  undownloadable (404 "Invalid job_id").

---

## Remediation roadmap

### Phase 1 — Docs (low risk)
Stop claiming MiDaS/PyTorch/Open3D. Describe the real classical-CV pipeline so future
debugging starts from reality.

### Phase 2 — Quick wins (high impact / low risk)
- Set an isometric `camera-orbit` + `camera-target`, add `environment-image`/`exposure`,
  and add `load`/`error` handlers to `<model-viewer>`.
- Make GLB export orientation correct (author Z-up or apply the right transform), verified
  by loading the exported GLB back.
- Remove/raise the 640px input cap; stop deleting thin walls on downscale.
- Preserve aspect ratio in normalized mode.
- Fix the FBX download (export real OBJ and label/serve it correctly, or drop FBX).

### Phase 3 — Wall-detection rebuild (the real accuracy fix)
Treat the plan as a 2D **vector drawing**, not a height image:
- Work at/near native resolution; accept vector input (SVG/DXF/PDF) where possible.
- Detect walls by line/double-line geometry + centerline extraction (robust to line
  weight, color, fill style, anti-aliasing, DPI) instead of one global threshold.
- Remove non-wall symbols (text, dimensions, furniture, door swings) explicitly.
- Detect doors/windows from their drawn symbols, not pixel brightness.
- Reconstruct room topology, snap corners, regularize angles, extrude watertight wall
  prisms with real per-wall thickness and per-storey height.
- Establish true scale from a scale bar / dimensions / explicit user input + detected DPI.

---

_Generated as part of the floor-plan rendering review. See the per-file notes above for
exact locations._
