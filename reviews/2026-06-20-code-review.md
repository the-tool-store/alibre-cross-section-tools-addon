# alibre-cross-section-tools-addon — Code Review (Correctness)

**Date:** 2026-06-20
**Scope:** Second-opinion review, code only (correctness bugs). Files reviewed: `scripts/adding-more-geometry-types.py`, `scripts/Template.py`, `scripts/alibre_setup.py`.

**Summary: 3 bugs — 0 High, 2 Medium, 1 Low**

## Medium

**`scripts/Template.py:296` (and 282-291)** — The fallback boundary extractor `extract_face_vertices_simple` returns face vertices in **arbitrary/unordered** order, and `calculate_face_properties` (line 393-401) feeds them straight into `project_to_2d` → `PolygonProperties` with **no angular ordering**. Why it's wrong: the shoelace area/centroid/inertia formulas depend on vertices being in boundary (sequential) order; unordered input produces self-intersecting traversal and silently wrong area, centroid, and moments. (Note: file 1's `project_to_2d` does angle-sort, so it does not share this defect — but angle-sorting itself fails for concave polygons.)

**`scripts/Template.py:245-248`** — `extract_ordered_boundary_from_edges` reads only `verts[0]` and `verts[1]` from each edge and treats every edge as a straight chord between two endpoints. Why it's wrong: for any face whose boundary contains a curved edge (arc/circle/spline), the edge is collapsed to a straight segment (or, for a closed circular edge with a single/duplicate vertex set, is dropped or mis-walked), yielding an incorrect polygon and wrong cross-section properties for non-polygonal faces.

## Low

**`scripts/adding-more-geometry-types.py:68-69 vs 76-77`** — In `AnnulusProperties.__init__`, `self.outer_radius`/`self.inner_radius` are assigned **before** the `if R < r: R, r = r, R` swap. Why it's wrong: if the class is constructed with `outer_radius < inner_radius`, the inertia math uses the corrected `R`/`r` but the stored `outer_radius`/`inner_radius` attributes (used by `generate_report`, lines 500-502) report the un-swapped, mislabeled values. Currently mitigated because all call sites (lines 314, 339) pre-sort with `max`/`min`, so it is latent rather than actively triggered.

## Notes (not counted as confident bugs)

- `scripts/alibre_setup.py:8` references `CurrentSession` which is never defined/imported in the module; this is presumably injected as a global by the AlibreScript host, so it is not flagged as a definite bug.
- The area "validation" percent-diff (file 1 line 512, Template line 347) compares vertex-derived area against `face.GetArea()` without confirming both are in the same units; potential unit mismatch but not verifiable as a bug from the code alone.

---

## Fixes applied — 2026-06-20

- **[Medium] `scripts/Template.py`** — added `order_vertices_by_angle()` (mirroring file 1's angle-about-centroid sort); `extract_face_boundary` now returns `(vertices, is_ordered)` and `calculate_face_properties` angle-sorts only the unordered fallback path (the edge-walk path is left in its existing boundary order).
- **[Medium] `scripts/Template.py`** — `extract_ordered_boundary_from_edges` now uses all vertices each edge exposes (consecutive-pair segments) and detects curved edges. **Limitation:** the API exposes no curve-sampling method, so a curved edge that returns only its two endpoints is still approximated as a straight chord — this cannot be resolved without a curve-sampling API.
- **[Low] `scripts/adding-more-geometry-types.py`** — `AnnulusProperties` now stores `outer_radius`/`inner_radius` *after* the `R < r` swap.

*Caveat: changes applied to source; command execution was unavailable so edits were verified by re-reading, not by running.*
