# Responsive viewer audit and restyle

Scope: the existing FLAN36 viewer, following the 2026-10-09 request to correct its mobile responsiveness and restyle the final design. Baseline: `80f43d3d88a93da135663317855489f6ed3bf043`. The repository was clean.

## Findings and changes

| Finding | Change | Acceptance |
| --- | --- | --- |
| Camera projection kept a fixed vertical extent while the available aspect ratio changed. A previously fitted scene could be cropped. | Adapt the orthographic projection by the ratio of old/new projected bounds. Preserve camera position, orientation, target and zoom. | Rendered model pixels remain inside the canvas through viewport and sidebar transitions, without Reset. |
| Mobile stage height included three rows of tools, leaving little space for the model. | Give the canvas its own height; keep Assembled, Inside, Stack and Fit visible; put secondary tools in View settings. | No overlap; explicit canvas height and reachable controls. |
| Four narrow component columns compressed text and visibility targets. | Two horizontally scrollable rows on compact layouts; a vertical rail on wide screens; 44px visibility targets. | Every component can be selected and hidden using touch. |
| Short landscape inherited a fixed sidebar and excessive minimum height. | Compact sidebar, shorter header, and normal page flow when secondary tools open. | Primary buttons fit the viewport; expanded controls stay inside the stage. |
| Editing farther down a mobile page loses sight of the model. | A Back to model action appears when the canvas is offscreen. | Return after editing without changing selection, camera or history. |
| Selection lines could point to offscreen directory entries. | Intersect component anchors with the directory and viewport; invalidate on scrolling. | Visible → clipped/hidden → visible in horizontal and vertical scroll. |

The visual system now uses a warm neutral canvas, clearer headings, a quieter header, larger selection cards and consistent green active states. It retains the existing models, palettes, parts and downloads.

Two independent read-only reviews agreed on this bounded change and normal delivery to the configured `main`/`docs` GitHub Pages source. Implementation review identified the mobile return action, short-landscape containment and the ancestor clipping case; all are addressed by dedicated checks. Review snapshots were hashed before and checked after review. No architecture, infrastructure, storage schema or geometry changes were needed.

## Verification

Run from the repository root with the locked viewer dependencies:

```sh
node viewer/build.mjs
node viewer/config-contract-check.cjs
node viewer/rebrand-check.cjs
FLAN36_PLAYWRIGHT_MODULE=/path/to/playwright FLAN36_BROWSER=/path/to/chromium node viewer/responsive-check.cjs
FLAN36_ENGINE=webkit FLAN36_PLAYWRIGHT_MODULE=/path/to/playwright node viewer/responsive-check.cjs
FLAN36_PLAYWRIGHT_MODULE=/path/to/playwright node viewer/reliability-check.cjs
```

The completed responsive checks passed in Chromium 151.0.7922.34 (the full browser in headless mode) and WebKit 26.5. On this Mac, the separate Chromium headless shell stalled in its GPU process during component sweeps; the full Chromium executable completed the same assertions. Set `FLAN36_BROWSER` to that executable when reproducing.

The responsive test covers 320×568, 390×690, 390×844, 768×1024, 844×390, 1024×768 and 1440×960. It checks actual rendered pixels and camera/state invariants across transitions, controls, touch orbit/pinch in Chromium, directory clipping and returning from color editing. Pixel sampling uses an inset crop to exclude the fractional CSS boundary shared with the toolbar; the required model clearance remains independently asserted.

The existing reliability test retains exact camera assertions for design changes. Only deliberate layout transitions permit the projection extent to change; position, orientation, target, zoom, selection, layer state and hidden objects must remain exact. It also checks JSON/GLB, native print-kit hashes, undo/redo, storage errors, conflicting tabs and recovery.

`validation/revI-responsive.json` records the final source hashes and measured results. Test screenshots/logs/downloads under `build/responsive-review/` and `build/reliability-fix/` are ignored, reproducible artifacts. No user screenshots, credentials or browser profiles are published. The embedded scene and print payload are byte-identical to the baseline. Public readback is recorded separately after normal synchronization.

Browser emulation does not establish physical iPhone acceptance. The approximately 50 MiB online viewer still includes the existing full-resolution scene; this change does not claim a reduction in loading cost.

## Bounded retrospective

The earlier checks verified a fresh load or explicitly reset before narrow-screen inspection. They did not protect a fitted view through orientation/layout transitions, and exact camera-field equality alone could not reveal projection clipping. The prevention is the bounded pixel/state transition test, plus checks for controls and both scroll clipping owners. No ongoing automation was added.

During tool setup, Playwright's default cache cleanup removed the prior Chromium 1228 cache. The exact version was restored from its published Playwright 1.61.1 manifest; subsequent installs disabled cache garbage collection. Test runtimes remain local and do not change viewer dependencies. Preserve that setting when preparing additional browser engines.
