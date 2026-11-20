#!/usr/bin/env python3
"""Compare a reference page or image set with a candidate at several widths.

The score split follows the measured website-check shape in Storytold's
Craft Anything: equal layout and perceptual-image signals. Reference:
https://github.com/storytold/craft-anything (MIT/Apache-2.0). This implementation
is independent; no upstream source code is copied.

Values that differ per site are arguments, not constants: viewport widths, the
browser executable, the timeout and the changed-pixel threshold. Without
`--browser`, a Chromium this repository can start is looked for in a few common
install locations, then Playwright's own download is used.

`--keep-height` cuts each capture to its top N pixels, so a caller's stored crop
is compared with a crop on the same basis instead of against a full page. The
browser and imaging stacks are imported where they are used, so `--help` and
argument errors work on a host without them.

Layout and image are weighted equally only when the reference is a page. A still
image has no DOM, so its layout is reported as unavailable and the likeness is
the image signal alone.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

WIDTHS = (1440, 768, 390)
VIEWPORT_HEIGHT = 1000
DIFF_THRESHOLD = 28
REGION_CELL = 16
REGION_OPACITY = 0.22
LAYOUT_JS = r"""() => {
  const visible = e => { const r=e.getBoundingClientRect(), s=getComputedStyle(e);
    return r.width>2 && r.height>2 && s.display!=='none' && s.visibility!=='hidden' && +s.opacity>0; };
  const label = e => (e.innerText || e.getAttribute('aria-label') || e.getAttribute('alt') || '').replace(/\s+/g,' ').trim().slice(0,100);
  const selector = e => {
    if (e.id) return '#'+CSS.escape(e.id);
    const tag=e.tagName.toLowerCase();
    const cls=Array.from(e.classList).slice(0,3).map(x=>'.'+CSS.escape(x)).join('');
    if (cls) return tag+cls;
    const same=Array.from(e.parentElement?.children||[]).filter(x=>x.tagName===e.tagName);
    return tag+(same.length>1?`:nth-of-type(${same.indexOf(e)+1})`:'');
  };
  return {height:Math.max(document.documentElement.scrollHeight, document.body?.scrollHeight||0),
    nodes:Array.from(document.querySelectorAll('header,nav,main,footer,section,article,aside,h1,h2,h3,button,a,img,[role="main"],[role="banner"],[role="navigation"]'))
      .filter(visible).slice(0,500).map(e=>{const r=e.getBoundingClientRect(); return {tag:e.tagName.toLowerCase(),selector:selector(e),label:label(e),
        x:r.x+scrollX,y:r.y+scrollY,w:r.width,h:r.height};})};
}"""


def page_url(value: str) -> str:
    if value.startswith(("http://", "https://", "file://")):
        return value
    return Path(value).expanduser().resolve().as_uri()


def chrome_path() -> str | None:
    """First Chromium found on this machine, or None to use Playwright's own."""
    override = os.environ.get("VISUAL_COMPARE_BROWSER")
    if override:
        return override if Path(override).is_file() else None
    for name in ("google-chrome", "chromium", "chromium-browser", "google-chrome-stable"):
        found = shutil.which(name)
        if found:
            return found
    candidates = [
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        Path.home() / "Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    return str(next((p for p in candidates if p.is_file()), "")) or None


def _gpu_args(base_args: list[str]) -> list[str]:
    """Append GPU flags on darwin; the bundled shell stays CPU elsewhere."""
    if sys.platform == "darwin":
        return base_args + [a for a in ("--headless=new", "--use-angle=metal", "--enable-gpu") if a not in base_args]
    return list(base_args)


def _launch_persistent_context(pw, profile_dir: str, width: int, height: int, browser: str | None):
    """On darwin launch installed Chrome with GPU; fall back to the bundled shell when missing.

    Always uses the throwaway `profile_dir`, never the signed-in profile.
    """
    base_args = ["--password-store=basic", "--use-mock-keychain"]
    common = dict(user_data_dir=profile_dir, headless=True, viewport={"width": width, "height": height},
                  device_scale_factor=1)
    if sys.platform == "darwin":
        gpu_args = _gpu_args(base_args)
        if browser is None:
            try:
                return pw.chromium.launch_persistent_context(channel="chrome", args=gpu_args, **common)
            except Exception:
                pass
        else:
            try:
                return pw.chromium.launch_persistent_context(executable_path=browser, args=gpu_args, **common)
            except Exception:
                pass
    kwargs = dict(common, args=base_args)
    exe = browser if browser is not None else chrome_path()
    if exe:
        kwargs["executable_path"] = exe
    return pw.chromium.launch_persistent_context(**kwargs)


def crop_top(image_path: Path, keep: int) -> None:
    """Cut a saved capture to its top `keep` pixels, matching a caller's stored crops."""
    from PIL import Image

    with Image.open(image_path) as source:
        image = source.convert("RGB")
    if image.height > keep:
        image.crop((0, 0, image.width, keep)).save(image_path, "PNG", optimize=True)


def capture(url: str, width: int, image_path: Path, profile: Path, timeout: int,
            *, browser: str | None = None, height: int = VIEWPORT_HEIGHT,
            keep_height: int | None = None) -> tuple[dict, str | None]:
    from playwright.sync_api import sync_playwright

    profile.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=profile.name + "-", dir=profile.parent) as profile_dir:
        with sync_playwright() as p:
            context = _launch_persistent_context(p, profile_dir, width, height, browser)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                page.evaluate("document.fonts.ready")
                page.wait_for_timeout(350)
                layout = page.evaluate(LAYOUT_JS)
                page.screenshot(path=str(image_path), full_page=True, animations="disabled", timeout=timeout)
                if keep_height:
                    crop_top(image_path, keep_height)
                return layout, page.url
            finally:
                context.close()


def load_reference_images(path: Path, widths: tuple[int, ...] = WIDTHS) -> dict[int, Path]:
    if path.is_dir():
        result = {w: path / f"{w}.png" for w in widths}
    elif path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        result = {w: (path.parent / raw[str(w)]).resolve() for w in widths}
    else:
        raise ValueError("reference image input must be a directory with "
                         + ", ".join(f"{w}.png" for w in widths) + ", or a JSON width map")
    missing = [str(result[w]) for w in widths if not result[w].is_file()]
    if missing:
        raise ValueError("missing reference images: " + ", ".join(missing))
    return result


def common_images(a: Image.Image, b: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    import numpy as np
    from PIL import Image

    a, b = a.convert("RGB"), b.convert("RGB")
    width = max(a.width, b.width)
    height = max(a.height, b.height)
    size = (width, height)
    aa = Image.new("RGB", size, "white")
    bb = Image.new("RGB", size, "white")
    aa.paste(a, (0, 0)); bb.paste(b, (0, 0))
    return np.asarray(aa, dtype=np.float32), np.asarray(bb, dtype=np.float32)


def ssim_score(a: np.ndarray, b: np.ndarray) -> float:
    # Average local 8x8 SSIM windows so matching page areas are not swamped by one
    # whole-page mean/variance calculation. The edge remainder is excluded.
    import numpy as np

    window = 8
    h, w = a.shape[:2]
    h, w = h - h % window, w - w % window
    x = a[:h, :w].mean(axis=2).reshape(h // window, window, w // window, window).transpose(0, 2, 1, 3)
    y = b[:h, :w].mean(axis=2).reshape(h // window, window, w // window, window).transpose(0, 2, 1, 3)
    mx, my = x.mean(axis=(2, 3)), y.mean(axis=(2, 3))
    vx, vy = x.var(axis=(2, 3)), y.var(axis=(2, 3))
    cov = ((x - mx[:, :, None, None]) * (y - my[:, :, None, None])).mean(axis=(2, 3))
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    score = ((2 * mx * my + c1) * (2 * cov + c2)) / ((mx * mx + my * my + c1) * (vx + vy + c2))
    return max(0.0, min(1.0, float(score.mean())))


def layout_score(a: np.ndarray, b: np.ndarray) -> float:
    # Coarse 16x16 cell colours keep the large visual composition separate from detail.
    import numpy as np

    scores = []
    h, w = a.shape[:2]
    for row in range(16):
        for col in range(16):
            x0, x1 = col * w // 16, (col + 1) * w // 16
            y0, y1 = row * h // 16, (row + 1) * h // 16
            ma = a[y0:y1, x0:x1].mean(axis=(0, 1))
            mb = b[y0:y1, x0:x1].mean(axis=(0, 1))
            scores.append(1.0 - float(np.abs(ma - mb).mean()) / 255.0)
    return max(0.0, min(1.0, float(np.mean(scores))))


def make_diff(a: Image.Image, b: Image.Image, path: Path, *, threshold: int = DIFF_THRESHOLD,
              cell: int = REGION_CELL, opacity: float = REGION_OPACITY) -> tuple[list[dict], int, int]:
    import numpy as np
    from PIL import Image, ImageDraw

    aa, bb = common_images(a, b)
    delta = np.abs(aa - bb).mean(axis=2)
    mask = Image.fromarray((delta > threshold).astype(np.uint8) * 255)
    # Merge changed pixels into broad regions, so the report ranks useful areas instead of noise.
    scale = cell
    small = mask.resize((max(1, mask.width // scale), max(1, mask.height // scale)), Image.Resampling.BOX)
    pix = np.asarray(small) > 16
    regions = []
    seen: set[tuple[int, int]] = set()
    for y, x in zip(*np.nonzero(pix)):
        if (y, x) in seen: continue
        stack, cells = [(y, x)], []
        seen.add((y, x))
        while stack:
            cy, cx = stack.pop(); cells.append((cy, cx))
            for ny, nx in ((cy-1,cx),(cy+1,cx),(cy,cx-1),(cy,cx+1)):
                if 0 <= ny < pix.shape[0] and 0 <= nx < pix.shape[1] and pix[ny,nx] and (ny,nx) not in seen:
                    seen.add((ny,nx)); stack.append((ny,nx))
        ys, xs = [c[0] for c in cells], [c[1] for c in cells]
        regions.append({"x": int(min(xs))*scale, "y": int(min(ys))*scale, "width": int(max(xs)-min(xs)+1)*scale,
                        "height": int(max(ys)-min(ys)+1)*scale, "changed_cells": len(cells)})
    regions.sort(key=lambda r: r["changed_cells"], reverse=True)
    gray = np.uint8(np.clip((aa.mean(axis=2) + bb.mean(axis=2)) * opacity, 0, 255))
    diff_rgb = np.repeat(gray[:, :, None], 3, axis=2)
    diff_rgb[delta > threshold] = (255, 28, 45)
    diff = Image.fromarray(diff_rgb, mode="RGB")
    draw = ImageDraw.Draw(diff)
    for r in regions[:12]: draw.rectangle((r["x"], r["y"], r["x"]+r["width"], r["y"]+r["height"]), outline=(255, 235, 0), width=3)
    diff.save(path)
    return regions, aa.shape[1], aa.shape[0]


def node_regions(layout: dict) -> list[dict]:
    return layout.get("nodes", [])[:]


def attach_selectors(regions: list[dict], candidate: dict) -> None:
    nodes = node_regions(candidate)
    for region in regions:
        cx = region["x"] + region["width"] / 2
        cy = region["y"] + region["height"] / 2
        hits = [n for n in nodes if n["x"] <= cx <= n["x"]+n["w"] and n["y"] <= cy <= n["y"]+n["h"]]
        hits.sort(key=lambda n: n["w"]*n["h"])
        region["selector"] = hits[0]["selector"] if hits else None
        region["label"] = hits[0]["label"] if hits else ""


def escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def write_report(out: Path, results: list[dict], *, title: str = "Visual comparison") -> None:
    sections = []
    for row in results:
        w = row["width"]
        ref = row["reference_image"]
        if Path(ref).is_absolute():
            ref = Path(ref).resolve().as_uri()
        regions = "".join(f"<li><b>{escape(r.get('selector') or 'region')}</b> {escape(r.get('label') or '')} — {r['width']}×{r['height']} at ({r['x']},{r['y']})</li>" for r in row["regions"][:8]) or "<li>No large pixel regions detected.</li>"
        layout = row["layout_similarity"]
        signals = (f"Layout {layout:.1f}% · image {row['image_similarity']:.1f}%" if layout is not None else
                   f"Layout unavailable — reference is a still image · image {row['image_similarity']:.1f}%")
        sections.append(f"""<section><h2>{w}px · likeness {row['likeness']:.1f}%</h2><p>{signals}</p>
          <div class="pair"><figure><figcaption>Reference</figcaption><img src="{escape(ref)}"/></figure><figure><figcaption>Candidate</figcaption><img src="{escape(row['candidate_image'])}"/></figure><figure><figcaption>Diff</figcaption><img src="{escape(row['diff_image'])}"/></figure></div><h3>Largest differing regions</h3><ol>{regions}</ol></section>""")
    html = f"""<!doctype html><meta charset="utf-8"><title>{escape(title)}</title><style>
      body{{font:15px system-ui;margin:24px;background:#f4f3ef;color:#18201e}}section{{margin:24px 0;padding:20px;background:white;border:1px solid #bbc5bf;border-radius:8px}}h1{{font-size:28px}}.pair{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}}figure{{margin:0}}img{{width:100%;height:360px;object-fit:contain;object-position:top;background:#ddd;border:1px solid #999}}figcaption{{font-weight:700;margin:5px 0}}@media(max-width:800px){{.pair{{grid-template-columns:1fr}}}}
      </style><h1>{escape(title)}</h1>""" + "".join(sections)
    (out / "report.html").write_text(html, encoding="utf-8")


def resolve_keep_heights(keep_heights: tuple[int, ...] | None,
                         widths: tuple[int, ...]) -> dict[int, int | None]:
    """Map each width to the top-crop height applied to both captures of that width."""

    if not keep_heights:
        return {width: None for width in widths}
    if len(keep_heights) == 1:
        values = keep_heights * len(widths)
    elif len(keep_heights) == len(widths):
        values = keep_heights
    else:
        raise ValueError("keep heights must be one value or one value per width")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 120 for value in values):
        raise ValueError("keep heights must be integers of at least 120 pixels")
    return dict(zip(widths, values))


def compare(
    *,
    reference: str | None = None,
    reference_images: str | Path | None = None,
    candidate: str | None = None,
    candidate_html: str | Path | None = None,
    output_dir: str | Path,
    widths: tuple[int, ...] = WIDTHS,
    browser: str | None = None,
    viewport_height: int = VIEWPORT_HEIGHT,
    keep_heights: tuple[int, ...] | None = None,
    diff_threshold: int = DIFF_THRESHOLD,
    title: str = "Visual comparison",
    timeout_ms: int = 45000,
) -> dict:
    """Capture, score and report; returns the same payload the command line prints.

    `keep_heights` crops each capture to its top N pixels so a caller's stored crops
    compare on their own basis. A stored image reference has no DOM: its layout score
    is null with a reason and the likeness is the image score alone.
    """
    from PIL import Image

    if (reference is None) == (reference_images is None):
        raise ValueError("pass exactly one of reference or reference_images")
    if (candidate is None) == (candidate_html is None):
        raise ValueError("pass exactly one of candidate or candidate_html")
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    keeps = resolve_keep_heights(keep_heights, widths)
    ref_images = None
    if reference_images is not None:
        ref_images = load_reference_images(Path(reference_images).expanduser().resolve(), widths)
    ref_url = page_url(reference) if reference else None
    cand_url = page_url(str(candidate or candidate_html))
    results = []
    for width in widths:
        keep = keeps[width]
        candidate_path = out / f"candidate-{width}.png"
        candidate_layout, candidate_final = capture(
            cand_url, width, candidate_path, out / "profiles" / f"candidate-{width}",
            timeout_ms, browser=browser, height=viewport_height, keep_height=keep)
        if ref_url:
            ref_path = out / f"reference-{width}.png"
            _, ref_final = capture(ref_url, width, ref_path, out / "profiles" / f"reference-{width}",
                                  timeout_ms, browser=browser, height=viewport_height, keep_height=keep)
        else:
            ref_path = ref_images[width]
            ref_final = None
        a, b = Image.open(ref_path), Image.open(candidate_path)
        aa, bb = common_images(a, b)
        image = ssim_score(aa, bb)
        if ref_url:
            layout = layout_score(aa, bb)
            layout_unavailable = None
        else:
            layout = None
            layout_unavailable = ("reference is a stored image, so there is no reference layout; "
                                 "likeness uses the image signal alone")
        diff_name = f"diff-{width}.png"
        regions, _, _ = make_diff(a, b, out / diff_name, threshold=diff_threshold)
        attach_selectors(regions, candidate_layout)
        results.append({"width": width,
            "layout_similarity": None if layout is None else round(layout * 100, 2),
            "layout_unavailable": layout_unavailable,
            "image_similarity": round(image * 100, 2),
            "likeness": round(image * 100, 2) if layout is None else round((layout + image) * 50, 2),
            "reference_image": ref_path.name if ref_url else str(ref_path),
            "candidate_image": candidate_path.name, "diff_image": diff_name,
            "reference_url": ref_final, "candidate_url": candidate_final,
            "candidate_layout": candidate_layout, "regions": regions[:20]})
    (out / "results.json").write_text(
        json.dumps({"schema": "visual-compare/1", "widths": list(widths),
                    "keep_heights": [keeps[width] for width in widths], "results": results},
                   indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(out, results, title=title)
    return {"output_dir": str(out), "report": str(out / "report.html"),
            "results": [{k: r[k] for k in ("width", "layout_similarity", "image_similarity", "likeness")}
                        for r in results]}


def parse_widths(value: str) -> tuple[int, ...]:
    """Read a comma-separated width list and refuse values too small to be a page."""

    try:
        widths = tuple(int(item) for item in value.split(",") if item.strip())
    except ValueError:
        raise ValueError("--widths must be comma-separated integers") from None
    if not widths or any(width < 120 for width in widths):
        raise ValueError("--widths must list widths of at least 120 pixels")
    return widths


def parse_keep_heights(value: str) -> tuple[int, ...]:
    """Read a comma-separated top-crop height list; its length is checked against the widths."""

    try:
        heights = tuple(int(item) for item in value.split(",") if item.strip())
    except ValueError:
        raise ValueError("--keep-height must be comma-separated integers") from None
    if not heights:
        raise ValueError("--keep-height must list at least one height")
    return heights


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    reference = parser.add_mutually_exclusive_group(required=True)
    reference.add_argument("--reference", help="reference URL")
    reference.add_argument("--reference-images", help="directory of <width>.png files or JSON width map")
    candidate = parser.add_mutually_exclusive_group(required=True)
    candidate.add_argument("--candidate", help="candidate URL")
    candidate.add_argument("--candidate-html", help="candidate local HTML file")
    parser.add_argument("--output-dir", required=True, help="caller-owned directory for all captures and reports")
    parser.add_argument("--widths", default=",".join(str(w) for w in WIDTHS),
                        help="comma-separated viewport widths in pixels (default: %(default)s)")
    parser.add_argument("--browser", default=None,
                        help="browser executable to drive; explicit value wins, otherwise one is detected")
    parser.add_argument("--viewport-height", type=int, default=VIEWPORT_HEIGHT,
                        help="viewport height in pixels (default: %(default)s)")
    parser.add_argument("--keep-height", default=None,
                        help="crop each capture to its top N pixels, one value or one per width "
                             "(comma-separated, in --widths order); default: full page")
    parser.add_argument("--diff-threshold", type=int, default=DIFF_THRESHOLD,
                        help="per-pixel mean channel difference counted as changed (0-255, default: %(default)s)")
    parser.add_argument("--title", default="Visual comparison", help="report heading")
    parser.add_argument("--timeout-ms", type=int, default=45000)
    args = parser.parse_args(argv)
    try:
        widths = parse_widths(args.widths)
    except ValueError as error:
        parser.error(str(error))
    keep_heights = None
    if args.keep_height:
        try:
            keep_heights = parse_keep_heights(args.keep_height)
            resolve_keep_heights(keep_heights, widths)
        except ValueError as error:
            parser.error(str(error))
    if not 0 <= args.diff_threshold <= 255:
        parser.error("--diff-threshold must be between 0 and 255")
    if args.browser is not None and not Path(args.browser).is_file():
        parser.error(f"--browser is not a file: {args.browser}")
    try:
        payload = compare(
            reference=args.reference,
            reference_images=args.reference_images,
            candidate=args.candidate,
            candidate_html=args.candidate_html,
            output_dir=args.output_dir,
            widths=widths,
            browser=args.browser,
            viewport_height=args.viewport_height,
            keep_heights=keep_heights,
            diff_threshold=args.diff_threshold,
            title=args.title,
            timeout_ms=args.timeout_ms,
        )
    except Exception as error:
        print(f"visual_compare: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2))
    return 0
