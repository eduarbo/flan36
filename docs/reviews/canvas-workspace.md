# Canvas workspace correction

Request: `user:20261010:canvas-space-and-static-drawer`. Parent: `user:20261009:revisa-flan32-visor-responsivo`.
Baseline: `8f31ac75cb6692b32e6bacf89b35f44df880bd6a`, clean `main`.

The user rejected the previous mobile layout: the permanent header, floating view toolbar and open editor left the 3D model in a strip. Earlier browser checks verified controls and state continuity but accepted a canvas as short as 100 px. Those checks did not establish the requested spatial priority. The previous mobile audit remains historical evidence, not design acceptance.

## Changes

- The editor starts closed. One 52 px tool strip remains below the canvas, plus the device safe-area inset. No header, floating toolbar, permanent component directory or saved-status row takes workspace space.
- Design, Parts, Files and About open a temporary editor. Selecting the current destination or its close button closes it. The editor has explicit Expand/Compact controls, a draggable separator and keyboard resizing. Portrait uses a bottom panel; landscape and desktop use a narrow side panel.
- The compact portrait editor takes 38% of available workspace. The default side panel is at most 360 px and 40% of the viewport width. Files and About initially open larger in portrait for reading; both can be compacted or closed.
- The category selector replaces a second navigation strip. Undo/Redo belongs to the editor. Assembled/Inside/Stack moved into View; Fit remains directly accessible.
- Closing remembers category, per-section scroll and size for the session. Modal Escape precedes panel Escape; closing preserves selection and returns focus. Closed content is hidden from layout and keyboard navigation. Save failures retain an actionable warning even with the editor closed.
- Projection adapts to the actual canvas. Fit projects each visible mesh's bounds, avoiding conservative empty corners between halves. Orbit, pan, relative zoom, configuration, selection, visibility and history survive layout changes.

The two halves remain in their actual relative positions. Their naturally wide silhouette does not fill every pixel of a portrait canvas. The available canvas is interactive and unobstructed; the model is neither stretched nor rearranged to inflate occupancy.

## Acceptance and evidence

`viewer/responsive-check.cjs` measures actual canvas area, center hit-testing, editor overlap, rendered model bounds and touch targets. It checks 320×568, 390×690, 430×820, 844×390, 768×1024, 1024×768 and 1440×960 in Chromium and WebKit. It exercises closed/compact/expanded states, drag and keyboard sizing, category/scroll restoration, orientation, text entry, dialogs, presets, one-half editing, history and component visibility.

The acceptance floor is 85% unobstructed viewport area while closed; compact portrait retains at least 55% and 220 px of canvas height. These measure the available canvas, not a hidden canvas behind overlays. Model pixels must stay within margins and use the limiting dimension. Full screenshots retain the actual controls. A delayed geometry decode verifies visible loading feedback followed by its removal. Home/End and drag extremes at 701×390, 844×390 and 1440×960 verify that every dock control stays inside the viewport and remains reachable. Narrow headers move Undo/Redo to a second row instead of clipping Close.

`viewer/reliability-check.cjs` retains configuration, atomic import, camera continuity, save recovery/conflicts, offline operation, GLB and exact native STL checks. `viewer/public-check.cjs` verifies served online/offline bytes and actual public exports. Exact commands and ignored reproducible output paths are in [the viewer guide](../viewer.md).

The validation receipt records actual results, source hashes, baseline comparison and reviewer dispositions. Browser emulation does not constitute physical iPhone testing or user design acceptance.

## Bounded retrospective

The prior acceptance checked minimum operability without measuring how much screen space the main task received. The correction replaces that weak criterion with default-closed canvas occupancy and panel lifecycle checks. This is limited to the viewer; CAD, print geometry, saved configuration schemas and existing authorship/license notices remain unchanged.

## Recorded local result

Chromium 151 and WebKit 26.5 each pass 42 layout/pixel checks, with no page errors. At 390×690, the closed canvas is 390×638 (92.46% of the viewport); the compact editor leaves 390×395.56 (57.33%). At 320×568 these values are 90.85% and 56.32%. The previous 390×690 canvas was about 124 px high.

The two independent reviewers agreed on the direction and identified two medium issues: the narrow side dock could clip Close, and slow startup lacked visible feedback. Both were corrected and tested. The original and implementation review scopes were compared against recorded hashes; changes were attributable to root implementation and the delegated two-file test adaptation. No unexplained reviewer mutation was observed.
