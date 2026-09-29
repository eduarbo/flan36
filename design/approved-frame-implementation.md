# Approved R4 implementation

The owner approved Talavera, Game Boy, SNES, 2000s Phone and iPod. Flan, Tape, Orbit, Manga, NES and Walkman remain deferred. Their existing artwork and palettes stay available.

The [scope contract](approved-frame-master-r4.json) binds the exact approved master. The shared shell gains 0.20 mm height and a 0.40 mm pin cover; the glass stays at Z13.39. The whole display mating chain moves 0.20 mm toward the frame center on each half. The native configuration, cap placement, battery, MCU and mount datums remain unchanged.

## Why the transfer changed

The previous generator fitted artwork to a backed-roof mask and resolved overlaps by color-role priority. That could cut motifs and could not represent the approved through-color collar or covered pins. The R4 builder consumes the original curves and painter order directly, with separate ordinary, collar and cover thickness domains. It compares finished material faces against both the JSON and the saved planar approval file.

Inspection also found that the old installer reset configuration. This migration captures the original selection and colors before editing and compares them after saving and reopening. Browser tests separately verify camera and view continuity.

A failed isolated candidate caught a wrong assumption that left and right native drill indices matched. No production CAD was changed by that candidate. J2 drills are now found by their physical centers and radius, and checked against the translated socket pins and the actual KiCad STEP export. Repeating the migration on an already migrated source is rejected before edits.

The final review also caught a stale viewer checker that still required every color volume to fit a uniform 0.4 mm band. Its replacement checks the approved ordinary, collar and cover domains, includes negative controls below each permitted floor, and samples the new motifs. The native geometry and viewer bytes did not change for this checker correction.

## Acceptance boundary

Current receipts cover exact approved faces, preservation of deferred artwork, native save/reopen, nominal assembly collisions, conservative cap travel, registered STEP/STL/3MF geometry, PCB placement and viewer state transitions. Digital acceptance does not establish a working keyboard, physical print fit, connector tolerances or PCB fabrication readiness. Public delivery is checked separately against the published commit.

The earlier proposal and installation receipts retain their original snapshots. They are not rewritten to claim acceptance of the current files.
