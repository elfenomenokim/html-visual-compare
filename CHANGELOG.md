# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-20

### Added

- `--keep-height` (library `keep_heights`) crops every capture to its top N pixels, so a stored
  crop is compared with a crop on the same basis instead of against a full page. One value applies
  to every width; one value per width follows `--widths` order.
- `tests/test_bench.py` re-runs the checked-in demo pair and asserts the saved `docs/bench/fixture.json`
  numbers within a small cross-platform drift; it also covers `--help` and argument errors without
  the imaging stack.
- `.github/workflows/tests.yml` runs that suite on Ubuntu, macOS and Windows with Playwright's own
  Chromium; `claude.yml` and `opencode-review.yml` give the repository its review checks.
- `[project.optional-dependencies] dev = ["pytest>=7"]` and `testpaths = ["tests"]`.

### Changed

- A stored-image reference has no DOM, so its `layout_similarity` is reported as `null` with a
  `layout_unavailable` reason and `likeness` is the image score alone, instead of scoring palette
  placement as if it measured layout.
- `numpy`, `Pillow` and `playwright` are imported where they are used, so `--help`, argument errors
  and the pure helpers work on a host without them.

## [0.1.0] - 2026-11-19

### Added

- Captures a reference and a candidate page at several viewport widths and writes a self-contained
  `report.html` with reference, candidate and diff images per width.
- Scores coarse layout (16×16 cell means) and detailed pixels (local 8×8 SSIM windows) separately;
  `likeness` is their equal-weight mean.
- Merges changed pixels into regions and labels each with the candidate node selector and text under its
  centre, ranked by changed-cell count.
- Compares against saved screenshot sets through `--reference-images`, matched by width.
- `--widths`, `--viewport-height`, `--diff-threshold`, `--browser` and `--title` replace fixed values;
  `VISUAL_COMPARE_BROWSER` pins a browser without a flag.
- Browser discovery also checks PATH and common Linux names, not only the macOS application paths.
- `compare()` exposes the whole measurement to Python callers with the same payload the command prints.

[Unreleased]: https://github.com/elfenomenokim/html-visual-compare/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/elfenomenokim/html-visual-compare/releases/tag/v0.2.0
[0.1.0]: https://github.com/elfenomenokim/html-visual-compare/releases/tag/v0.1.0
