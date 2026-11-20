"""Re-run the checked-in demo pair and assert the saved bench numbers.

The pair and the numbers that were measured on it are `docs/bench/fixture.json`; a changed
weight, window size or capture basis moves them, which is what this test catches. Font
rasterisation differs per platform, so the assertion allows a small absolute drift rather
than demanding an identical float.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1]
CORE_PATH = PACKAGE / "src" / "html_visual_compare" / "core.py"
BENCH = json.loads((PACKAGE / "docs" / "bench" / "fixture.json").read_text(encoding="utf-8"))

# Cross-platform font rendering moves these numbers by up to about two points of percentage.
# Measured on the M5 by re-rendering the same pair with other font stacks (serif, monospace,
# Segoe UI, DejaVu Sans 20px): the worst absolute delta was 1.42 points. The fixture pages ask
# for `system-ui`, so a runner with a different font stack lands inside this tolerance.
DRIFT = 2.5


def load_core():
    spec = importlib.util.spec_from_file_location("_bench_html_visual_compare_core", CORE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def disposable_browser() -> str:
    """Playwright's own Chromium; a test never launches the maintainer's installed browser."""

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        executable = Path(playwright.chromium.executable_path)
    if not executable.is_file():
        pytest.skip(f"Playwright's Chromium is not installed: {executable}")
    return str(executable)


def test_demo_pair_matches_saved_numbers(tmp_path):
    core = load_core()
    widths = tuple(int(width) for width in BENCH["pair"])
    payload = core.compare(
        reference=str(PACKAGE / BENCH["fixture"]["reference"]),
        candidate_html=str(PACKAGE / BENCH["fixture"]["candidate"]),
        output_dir=tmp_path,
        widths=widths,
        browser=disposable_browser(),
        title="bench",
    )
    rows = {row["width"]: row for row in payload["results"]}
    for width in widths:
        expected = BENCH["pair"][str(width)]
        for key in ("layout_similarity", "image_similarity", "likeness"):
            assert rows[width][key] == pytest.approx(expected[key], abs=DRIFT), (width, key, rows[width])
    assert (tmp_path / "report.html").is_file()
    assert (tmp_path / "results.json").is_file()


def test_help_and_arguments_work_without_the_imaging_stack(monkeypatch, capsys):
    for name in ("numpy", "PIL", "playwright", "playwright.sync_api"):
        monkeypatch.setitem(sys.modules, name, None)
    core = load_core()
    with pytest.raises(SystemExit) as raised:
        core.main(["--help"])
    assert raised.value.code == 0
    assert "--keep-height" in capsys.readouterr().out
    with pytest.raises(ValueError):
        core.parse_widths("0")


def test_keep_heights_are_one_value_or_one_per_width():
    core = load_core()
    assert core.resolve_keep_heights(None, (1440, 390)) == {1440: None, 390: None}
    assert core.resolve_keep_heights((1800,), (1440, 390)) == {1440: 1800, 390: 1800}
    assert core.resolve_keep_heights((1800, 1688), (1440, 390)) == {1440: 1800, 390: 1688}
    with pytest.raises(ValueError):
        core.resolve_keep_heights((1800, 1688, 900), (1440, 390))
