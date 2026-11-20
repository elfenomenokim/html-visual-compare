#!/usr/bin/env bash
# Fake fixture for the demo: no real site, no network.
set -euo pipefail
cd "$(dirname "$0")"
echo "fixture: a.html (reference) and b.html (candidate) are checked in"
