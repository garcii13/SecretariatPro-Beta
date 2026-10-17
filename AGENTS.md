# SecretariatPro common baseline

This workspace combines Mac Live beta 8 (`4ac82de`) and Windows Live beta 10
(`3d4c10a`), plus the later local OCR clock-consensus fixes. Treat this union as
the minimum supported feature set. The tracked source checkout is `.publish-repo/`;
the parent directory is the local runnable copy. Keep changed application source
synchronized between them; never copy private runtime/settings files into Git.

Preserve OCR (all models, sources, regions, perspective, confidence and clock
progression), DPI-correct window capture, Mac camera startup, manual scoring,
penalties/periods, account and competition isolation, Manager publication,
rosters/imports, graphic queues, OBS, multicamera replay, templates, library and
export. See `docs/BASELINE_COMPATIBILITY.md` for the acceptance matrix.

For application changes run `python packaging/run_regressions.py`, JavaScript
syntax checks for `script.js`, `webapp/app.js` and `manager_app/app.js`, and
`node --test tests/ocr_preview.test.cjs tests/overlay_presentation.test.cjs tests/manager_identity.test.cjs`.
Do not remove existing coverage to make a change pass. Keep platform-specific
requirements separate. Windows-only tests must run on Windows before calling a
cross-platform release validated. Installed application checks and an OBS/camera
session remain necessary before distributing new installers.

International flags must remain complete and undistorted. On the scoreboard,
both flags have the same visible width, capped at 1.5 times its height. If either
flag requires more height, reduce the common width of both. Keep the scoreboard
height unchanged. Preserve club crests separately in all competition modes.

Goal presentation belongs to BroadcastFlow: replay/confirmed live (or configured
delay), goal intro, full configured scorer duration, bottom hidden, scoreboard
restored. Cancellation must prevent stale graphics from returning.
