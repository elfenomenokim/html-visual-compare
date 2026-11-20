# Contributing to html-visual-compare

Bug reports and patches are welcome. You do not need to ask before opening a pull request for a bug fix.

## Before you start

- **A capture failed, or a score looks wrong:** open an issue with the reference and candidate inputs (or
  two small HTML files that reproduce them), the widths, and the `results.json` you got. The images the
  run wrote are the most useful evidence.
- **A change to how the score is computed:** open an issue first. A changed weight moves every stored score.
- **A security problem:** do not open a public issue. See [SECURITY.md](SECURITY.md).

## Set up

```sh
git clone https://github.com/elfenomenokim/html-visual-compare
cd html-visual-compare
python3 -m pip install . pytest
python3 -m playwright install chromium
python3 -m pytest -q tests
PYTHONPATH=src python3 -m html_visual_compare --help
PYTHONPATH=src python3 -m html_visual_compare \
  --reference docs/demo/a.html --candidate-html docs/demo/b.html --output-dir /tmp/vc-check
```

`python3 -m pytest tests` re-runs the checked-in fixture pair and asserts the saved bench numbers. Never
point it at a live site you do not own, and write every manual run to a fresh `/tmp` directory.

## Rules a patch must keep

- `likeness` stays the equal-weight mean of the layout and image signals. Do not reweight one silently.
- A capture failure fails the run with a non-zero exit; it never reuses an older image for that width.
- Reference images are matched by width. A missing `<width>.png` is an error that names the missing files.
- Chrome discovery is a fallback chain: `--browser`, then `VISUAL_COMPARE_BROWSER`, then PATH, then the
  macOS locations, then Playwright's own download. A test never drives a browser it did not choose.
- Region selectors come from the candidate's DOM, not from the reference, because the candidate is the
  page being changed.
- Every value that differs per site is an argument: widths, viewport height, diff threshold, title.

## What a good patch has

- **A fixture page pair** that shows the wrong behaviour before the change and the right one after it.
- **A line under Unreleased** in [CHANGELOG.md](CHANGELOG.md) when a caller will notice.
- **The platforms you did not test** written in the pull request. A contributor's own run is usually
  macOS or Linux; `.github/workflows/tests.yml` adds Windows, 3.9 and 3.13 on every pull request.

## Licence

Contributions are licensed under the MIT licence in [LICENSE](LICENSE).
