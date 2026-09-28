# Viewer reliability plan

Requested September 28, 2026: fix the general review findings and related bugs, preserve the current inspection when changing design options, and start immediately.

This plan covers the complete viewer follow-up to the [general review](2026-09-28.md). Mechanical geometry stays at its existing revision; this work does not qualify fabrication.

| Step | Required result | Acceptance |
|---|---|---|
| 1 · Protect designs | Rejected saved data survives startup; simultaneous tabs cannot silently replace one another's work. | Disposable browser tests compare the original bytes, exercise conflicting writes and recover each design. Storage failures leave the current design exportable. |
| 2 · Apply safely | Invalid imports leave the scene, configuration and saved state unchanged. JavaScript and Python agree on types and legacy Solid cases with covers. | Negative input corpus; before/after configuration and exported GLB comparisons; native configuration validation parity. |
| 3 · Preserve inspection | Case, frame, keycap, battery, theme and color changes preserve zoom, pan, orientation, selected part, hidden parts and exploded position. Sidebar and viewport resizing do not refit. | Browser measurements before/after each transition. Explicit Fit, view presets and reset still work. |
| 4 · Clarify controls | Battery target is explicit and respected. Component descriptions and delivery links match their actual scope. | Left/right/both battery tests; copy and evidence review. |
| 5 · Make experiments reversible | Undo/redo and named JSON designs cover full configurations without resetting the view. | Round trips across mixed halves, colors, geometry, imports and defaults; saved JSON design reload. |
| 6 · Reduce loading cost | Inspection does not eagerly parse printable files. Online loading is smaller; a complete offline artifact remains available. | Comparable startup/heap/size measurements, online and disconnected offline configuration, GLB and exact print-kit tests. |
| 7 · Deliver | Validate related regressions, preserve audit history, and publish the tested source and viewer. | Explicit staged-file review, normal main push, authoritative remote hash and published functional checks. |

New reproducible defects found during these checks were included in the same bounded pass. The results below distinguish local acceptance from public readback.

Execution started from `4d17638357f200a53fe4d6baddc9753209019ca6` with a clean working tree. Both independent reviews recommended the same bounded route. [Review record](../../validation/revI-reliability-review.json).

## Results

All seven steps are verified. The public source and viewer at `75d2c24e07e51175ed826b0ea0d4a76b24890363` passed anonymous file readback and functional browser checks. [Public delivery receipt](../../validation/revI-reliability-public.json).

- GR01–07 corrected. Opening does not write; stale tabs preserve a separate draft; invalid data and missing resources leave the live scene unchanged; legacy configurations use Solid covers; battery targets are explicit; current documentation identifies historical evidence correctly.
- Related palette data loss uses the same protection. A synchronous draft also survives closing a tab while its shared save is queued. Storage denial and browsers without locks remain editable/exportable and report the limitation.
- Seventeen camera/configuration transitions preserve the inspection. Session undo/redo, named JSON designs, 112 JavaScript/Python fixtures, 40 cap-direction measurements, full UI controls, key colors, HEX copy/paste and mobile emulation pass.
- The public readback matched all 1,238 archive files and the online, offline and print assets. The published viewer retained its camera across case/frame changes and exported matching JSON and exact native STL files without runtime errors.
- Online print files load on demand with a version hash and retry. The offline HTML exports the same native STLs and 3MF contents with all network requests blocked. Eighteen identical meshes are shared; no geometry was simplified.

[Exact source-bound acceptance and loading measurements](../../validation/revI-reliability.json). The measurements use three interleaved desktop runs per mode, not a physical phone or a remote-network benchmark.

The cause of the data-loss failures was coupling restore/apply with unconditional persistence. View jumps came from implicit fit/reveal operations in option handlers and resize. The prevention is a single guarded persistence path, a prepared scene commit, separate design/view state, and regression checks for the failed transitions.

Reproduce ignored test outputs with the commands in the [viewer guide](../viewer.md), the broader UI mirror in [customization](../customize.md), and `python3 tools/record_viewer_reliability.py`. The review receipt preserves the independent advisory findings; it does not substitute for the browser tests.
