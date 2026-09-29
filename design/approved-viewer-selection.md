# Approved viewer selection

The gallery withdrawal did not update the main viewer's separate frame catalog.
Flan, Tape, Orbit, Manga, NES and Walkman therefore remained selectable, and Flan
remained the fallback. Tape still had its old border; it was not repaired.

The active viewer now derives its catalog from `frame-selection.json`. It delivers
only Talavera (default), Game Boy, SNES, Phone and iPod, including previews and
print assets. Hanafuda remains approved and pending integration. No new artwork
or mechanical geometry is introduced by this correction.

Saved and imported retired shapes resolve directly to Talavera. Explicit colors,
implicit old accent palettes, cases, batteries and caps are preserved. Startup
does not rewrite storage; the first subsequent edit preserves the original saved
JSON before migration. Camera, layer and visibility behavior is unchanged.

The native CAD, its source catalog and historical receipts retain the earlier
collection as provenance. Viewer exports materialize all colors and remain valid
inputs to the native configuration reader. Old hashed print payloads remain for
cached historical pages; the new viewer references only its approved payload.

Two independent read-only reviews agreed on this scope: derive the active catalog,
preserve original configuration bytes and colors, and require actual browser and
print-export readback. Their shared baseline was clean commit
`3e2554982e4dbd80dbc93d65aa09b246d43943b0`; all enumerated file hashes remained
unchanged after review. Their migration, fallback, stale-preset and public-delivery
concerns are covered by the checks below. No material objection remained.

## Reproduce

Use the Python rendering dependencies and the viewer's pinned npm dependencies.
Set `FLAN36_PLAYWRIGHT_MODULE` and `FLAN36_BROWSER` if reusing an installed browser
runtime.

```sh
python tools/build_viewer_revI.py
node viewer/build.mjs
node viewer/config-contract-check.cjs
node viewer/frame-collection-check.cjs
node viewer/reliability-check.cjs
# After publication:
node viewer/public-check.cjs <published-commit>
```

Ignored scenes, screenshots, 3MF/GLB/ZIP examples and test receipts under `build/`
are reproducible with those commands. Validate against the hashes and acceptance
results in [the selection receipt](../validation/revI-approved-selection.json).
The original collection and R4 delivery receipts describe their historical
snapshots and are not acceptance of the current viewer.
