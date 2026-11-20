## What and why

<!-- One paragraph. Link the issue when there is one. -->

## How to check it

<!-- The fixture pair and the command a reviewer runs. -->

## Checklist

- [ ] The change is exercised with the checked-in `docs/demo/` pages, writing to a fresh `/tmp` directory.
- [ ] `likeness` still carries equal weight on layout and image, or the change says why it moved.
- [ ] A failed capture still exits non-zero instead of reusing an older image.
- [ ] A line is added under Unreleased in CHANGELOG.md when a caller will notice.
- [ ] README.md and README.ko.md still describe the behaviour.
- [ ] Platforms not tested are named here.
