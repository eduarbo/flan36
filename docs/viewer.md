# Using the viewer

[Open Flan36](https://eduarbo.github.io/flan36/) · [Download the complete offline viewer](https://eduarbo.github.io/flan36/offline.html)

Drag to orbit, scroll or pinch to zoom, and right-drag or use two fingers to pan. **Fit view** recenters the visible parts. Changing a case, frame, keycap, color or battery keeps your camera, hidden parts and layer separation. Resizing the sidebar preserves the view too.

Hover or focus a component to highlight it, including through the case. A subtle line connects it to the sidebar. Click a component in the model or directory to inspect it; Escape clears the selection. The sidebar arrow collapses details while keeping the directory available.

The eye controls affect visibility. Open **Individual parts** to toggle one piece. **Show all** restores the assembly. **Solo** isolates the selected component. Case, frame and battery controls have explicit **Both / Left / Right** targets; the battery target follows the component you select.

**Undo / Redo** keeps 40 design steps during the current session. Ctrl/Cmd Z and Ctrl/Cmd Shift Z work outside text fields. One continuous color gesture is one step. View changes are separate from design history.

In **Files**, give your design a name and save its JSON. Load that file to return to the same shapes, per-key colors, frames and batteries. JSON also transfers selections to FreeCAD.

## Saved data and recovery

Opening the viewer never overwrites saved data. If an older or damaged value cannot be read, it stays intact and a **Save warning** links to recovery.

Two current viewer tabs cannot silently replace one another's changes. A stale tab keeps a separate recovery draft. **Files → Recover saved data** lets you download the original values and those drafts. You can load the saved version, export your current design separately, or explicitly use it as the saved version; replacement keeps a recovery copy first. Palette conflicts use the same protection. Import recovered palette files through **My palettes**.

If browser storage is unavailable, the design remains editable and exportable in that tab. Export before closing. Session undo does not survive a reload.

## Online and offline

The online viewer loads print files only when you request a print kit. A failed download can be retried without changing the design. Files are matched to the viewer version before use.

Use the **Download offline HTML** link for a complete, single-file copy. It opens without a server or network and includes configuration, GLB and print-kit export. The smaller online `index.html` alone is not the offline download.

GLB exports all installed parts assembled, regardless of hidden layers or exploded offsets. Its units are meters; use FreeCAD/STEP for solid editing.

Both use the same full-resolution geometry. Print kits preserve the exact native STL files; 3MF retains the registered material volumes. These checks do not qualify physical fit, electronics or a print process.

## Reproduce the checks

With the locked viewer dependencies installed:

```sh
node viewer/build.mjs
node viewer/config-contract-check.cjs
node viewer/rebrand-check.cjs
FLAN36_PLAYWRIGHT_MODULE=/path/to/playwright FLAN36_BROWSER=/path/to/chromium node viewer/reliability-check.cjs
FLAN36_PLAYWRIGHT_MODULE=/path/to/playwright FLAN36_BROWSER=/path/to/chromium node viewer/loading-check.cjs
```

Outputs under `build/reliability-fix/` are ignored, reproducible test artifacts. The [execution plan](reviews/reliability-plan.md) and [reliability receipt](../validation/revI-reliability.json) record scope and results at their stated revision. Historical delivery receipts retain their original hashes and scope.

After publication, pass the exact published commit to both readbacks:

```sh
python3 tools/check_public_delivery.py <published-commit>
FLAN36_PLAYWRIGHT_MODULE=/path/to/playwright FLAN36_BROWSER=/path/to/chromium node viewer/public-check.cjs <published-commit>
```

The first matches the anonymous source archive and served viewer assets against Git. The second checks the actual public scene, camera continuity, configuration export and native print-kit hashes in a disposable browser profile. `python3 tools/restore_reliability_review.py` restores the ignored advisory review artifacts from their committed receipt.

Save serialization uses the browser [Web Locks API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Locks_API). Without it, the viewer preserves a separate recovery draft and offers JSON export instead of overwriting shared saved state.
