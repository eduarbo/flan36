# Mobile viewer redesign and CAD authorship correction

Request: the original 2026-10-09 responsive/design audit, followed by Eduardo's explicit rejection of the first delivery as saturated, hard to navigate and insufficiently redesigned. The second request also corrects CAD authorship. Baseline: `e5c7e0833582fab0f4f55b332cc163cec097f8d2`, clean main.

The original objective remains in scope: usable responsive viewing, a coherent design, preserved functionality and verified delivery. The first responsive measurements remain historical evidence; they did not establish acceptable mobile information architecture.

## Design findings and resolution

| Finding | User-visible result | Acceptance |
| --- | --- | --- |
| Twelve component groups, visibility tools and page navigation competed above every editor. | Persistent **Customize / Parts / Files / About** navigation. Only Parts displays the component directory. | All destinations checked at seven sizes; active destination, heading and navigation remain identifiable. |
| Inspection and editing were conflated. | Customize has Case, Frame, Keys, Colors and Battery categories. Parts shows information, visibility and an explicit **Customize this part** action. | Touch all twelve groups; select, hide, solo, restore and edit; camera and configuration preserved. |
| A long mobile page separated edits from their preview. | Model stays visible while the editor scrolls. **Hide 3D / Show 3D** expands the editor; a short viewport with a focused text field hides the preview until explicitly restored. | One-half color change, short keyboard-sized viewport, navigation and preview restoration. |
| Every setting demanded attention at once. | Style previews lead; colors, finishes, per-key shape and recovery expand on demand. | Review entry states and expanded color/key forms. |
| Files mixed recovery, save and manufacturing into one long disclosure. | Separate Save your design, Print your parts, 3D & offline cards; recovery remains available below them. | JSON, recovery bytes, assembled GLB and exact native print-kit contents. |
| About inherited a parts directory, an editing status and run-together links. | Dedicated authored-product introduction, specifications, original-design credit, optional technical status and separate resource rows. | About after a selection; no editing status, selected-part controls or directory leak into the page. |
| Licenses opened every full text and scrolled away the close button. | Separate source summaries, individually collapsed full texts, persistent title/Close and focus restoration. | Scroll an expanded GPL text, close via button/Escape, return to opener. |
| Blanket “CAD derived from Piantor” misattributed Eduardo's work. | Original CAD credited to Eduardo in About, credits, README, attribution and exported GLB. Piantor is inspiration for key count. | Generated viewer and GLB wording checked; third-party notices and historical coordinate metadata retained. |

The same scene, camera, configuration and history survive navigation; no duplicate canvas or controls were introduced. On mobile, Files/About use the full workspace. On desktop the model and content remain side by side. Borders, spacing, headings and active states distinguish navigation, model, editor categories, previews and supplementary information.

## Independent review and corrections

Two independent read-only reviewers used constructive design and adversarial reliability lenses. Both recommended the same four-destination information architecture and a bounded authorship correction preserving source notices. They inspected the implementation and screenshots across phone, landscape and desktop, including every editor. Both found the new View dialog exposed an old Escape handler that cleared selection; one also identified the residual selected-row attribute. Both are corrected and covered by state assertions. The scrolling directory now clips its links to the inspector viewport as well as the directory; hiding the 3D preview suppresses the link. Stale component instructions were aligned with the explicit Customize action.

Known root edits were compared against recorded before/after hashes; neither reviewer mutated files. Their review was advisory. Screenshots and browser assertions do not represent Eduardo's design approval or testing on a physical iPhone.

## Verification and reproduction

```sh
node viewer/build.mjs
node viewer/config-contract-check.cjs
node viewer/rebrand-check.cjs
FLAN36_PLAYWRIGHT_MODULE=/path/to/playwright FLAN36_BROWSER=/path/to/full-chromium node viewer/responsive-check.cjs
FLAN36_ENGINE=webkit FLAN36_PLAYWRIGHT_MODULE=/path/to/playwright node viewer/responsive-check.cjs
FLAN36_PLAYWRIGHT_MODULE=/path/to/playwright FLAN36_BROWSER=/path/to/full-chromium node viewer/reliability-check.cjs
```

Use full Chromium headless, not the separate headless shell on this Mac. Existing test runtime versions: Chromium 151.0.7922.34 and WebKit 26.5; no project dependencies were changed. If preparing additional Playwright browsers, preserve existing caches with `PLAYWRIGHT_SKIP_BROWSER_GC=1`.

The responsive matrix is 320×568, 390×690, 430×820, 768×1024, 844×390, 1024×768 and 1440×960. It covers 28 destination layouts plus the model after gestures; captures every destination, both dialogs and the five editors, including expanded forms. It checks actual rendered model bounds, persistent navigation, section scroll, camera and saved design invariants, twelve visibility controls, one-half color editing, history, selection, dialog Escape/focus and clipping of links. Keyboard space is simulated by viewport reduction; a physical iOS keyboard was not tested.

`validation/revI-mobile-redesign.json` binds source hashes and results. Generated scene geometry, imported sources, layout metadata and print payload remain unchanged. Browser downloads, logs and full screenshot matrices in ignored `build/mobile-redesign/` and `build/reliability-fix/` are regenerated with these commands. Selected public screenshots under `docs/images/viewer-mobile-*.png` are copied from the 390 px WebKit capture. No user screenshots or browser profiles enter Git.

## Bounded retrospective

The prior audit emphasized framing, overflow and target dimensions while under-sampling information architecture and full user journeys. That allowed a technically responsive but crowded interface, a misleading About page and an unusable license presentation to pass. The prevention is a finite four-destination visual matrix plus editor, dialog and selection flows, not another blanket “responsive passed” claim. Historical receipts are preserved and explicitly superseded for design acceptance. CAD authorship was corrected across current user-facing descriptions and exports without rewriting geometry or third-party provenance.
