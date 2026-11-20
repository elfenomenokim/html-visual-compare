"""Screenshot a reference and a candidate, then score and report the difference.

`main()` is the command line; `compare()` runs the same measurement from Python.
Layout and perceptual-image signals carry equal weight when the reference is a
page; a stored-image reference has no layout, so its likeness is the image score.
Every changed region is reported with the candidate selector under its centre.
"""

from .core import (
    DIFF_THRESHOLD,
    VIEWPORT_HEIGHT,
    WIDTHS,
    chrome_path,
    compare,
    main,
    parse_keep_heights,
    parse_widths,
    page_url,
)

__all__ = [
    "DIFF_THRESHOLD",
    "VIEWPORT_HEIGHT",
    "WIDTHS",
    "chrome_path",
    "compare",
    "main",
    "parse_keep_heights",
    "parse_widths",
    "page_url",
]

__version__ = "0.2.0"
