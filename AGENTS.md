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
`node --test tests/ocr_preview.test.cjs tests/overlay_presentation.test.cjs tests/manager_identity.test.cjs tests/overlay_motion.test.cjs`.
Do not remove existing coverage to make a change pass. Keep platform-specific
requirements separate. Windows-only tests must run on Windows before calling a
cross-platform release validated. Installed application checks and an OBS/camera
session remain necessary before distributing new installers.

Security changes also run `npm ci --prefix security_tests` and
`npm test --prefix security_tests` (the invitation SQL executes on PostgreSQL).
Do not update the OCR Lab as part of application audit fixes.

For renderer changes first run `npm ci --prefix broadcast_renderer` and
`npm run verify --prefix broadcast_renderer`. Keep the generated `overlay_studio/`
assets and their source/build manifest synchronized in both checkouts. Node is
a build dependency only; the installed overlay must work using local bundled assets.

International flags use one centered crop frame based on the minimum source
width and minimum source height of both flags. Scale it to fill the unchanged
scoreboard height, cap its width at 1.5 times that height, and crop without
stretching or leaving gutters. Match this in Manager preview. Keep uploaded
originals and club crests separately in all competition modes. International
mode belongs to competitions.is_international and each team owns its flag_url;
visual themes only style the graphics and must not override competition mode.

Goal presentation belongs to BroadcastFlow: replay/confirmed live (or configured
delay), goal intro, GOAL_REVEAL handoff, full configured scorer duration, bottom hidden, scoreboard
restored. Cancellation must prevent stale graphics from returning.
