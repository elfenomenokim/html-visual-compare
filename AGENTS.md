# AGENTS.md

## Layout

- `src/html_visual_compare/core.py`: capture, scoring, region extraction, the `compare()` API and the CLI.
- `src/html_visual_compare/__init__.py`: the public names and the version.
- `src/html_visual_compare/__main__.py`: `python3 -m html_visual_compare`.
- `tests/`: the fixture bench suite. It loads `core.py` by path, so it runs without an install.
- `.github/workflows/`: `tests.yml` on Ubuntu, macOS and Windows, plus the review workflows.
- `docs/demo/`: the two fixture pages and a saved diff image. Never a live site or a real screenshot.
- `docs/bench/fixture.json`: saved scores for the fixture pair.
- `public.json`: export allowlist and repository metadata.

## Commands

Run from the repository root:

```sh
PYTHONPATH=src python3 -m compileall -q src
PYTHONPATH=src python3 -m html_visual_compare --help
PYTHONPATH=src python3 -m html_visual_compare \
  --reference docs/demo/a.html --candidate-html docs/demo/b.html --output-dir /tmp/vc-check --widths 1440
```

`tests/test_bench.py` re-runs the checked-in fixture pair and asserts the saved
`docs/bench/fixture.json` numbers within a small cross-platform drift. Run it with
`python3 -m pytest tests`; it skips when Playwright's own Chromium is not installed, because a
test never launches the maintainer's installed browser. Install that browser once with
`python3 -m playwright install chromium`. Use a fresh `/tmp` directory for any manual run.

## Changes

- `likeness` is the equal-weight mean of the layout and image scores. Do not reweight one without saying so
  in the README and CHANGELOG. A stored-image reference has no DOM, so its layout score is `null` with a
  reason and `likeness` is the image score alone.
- The layout signal is a 16×16 cell mean; the image signal is local 8×8 SSIM windows. Changing either
  invalidates the saved numbers in `docs/bench/fixture.json`; re-run the bench when you change them.
- A failed capture fails the run with a non-zero exit. Never reuse an older image for that width.
- Reference images are matched by width; a missing file is an error that lists every missing path.
- Region selectors come from the candidate's DOM, because the candidate is the page under review.
- Browser choice order is `--browser`, `VISUAL_COMPARE_BROWSER`, PATH, macOS locations, Playwright. Keep the
  order and keep the explicit values first.
- Every per-site value is an argument: widths, viewport height, keep height, diff threshold, title, timeout.
- Keep README.md, README.ko.md, the `pyproject.toml` description and `public.json` aligned.
- A local commit is not publication. Version bumps and PyPI uploads need the maintainer's instruction.

## Hard don'ts

- Do not point a fixture or a demo at a real site, a real account, or a page you do not own.
- Do not launch the maintainer's installed browser in a test. Pass `--browser` to a disposable one.
- Do not write outside `--output-dir`.
- Do not turn the score into a pass/fail gate inside this package; callers own their tolerances.
