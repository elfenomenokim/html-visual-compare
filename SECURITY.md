# Security policy

## Supported versions

Security fixes go into the latest release. Upgrade before reporting, in case the problem is
already fixed.

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |
| Older | No |

## Reporting a vulnerability

Report it privately, not in a public issue: use the
[Report a vulnerability](https://github.com/elfenomenokim/html-visual-compare/security/advisories/new)
form on the repository's Security tab.

Include the inputs you used, the version, and what an attacker could do with the result. You get a reply
within a few days.

## In scope

- A page under test that reads or writes files outside the `--output-dir` you passed.
- A page that escapes the browser sandbox, or a browser launched with a profile that holds real data.
- A URL that reaches a host the caller did not name, for example through a redirect chain in the capture.
- A crafted page that makes the report write script into `report.html` beyond escaping.
- Reference-image paths that resolve outside the directory the caller named.

## Not a vulnerability

- A low score for a page that really does look different.
- Fetching the reference or candidate URL you asked for. The tool loads exactly what you name.
- The candidate page being able to run its own JavaScript. That is the page under test doing what it does.
- Using a real Chrome install when you did not pass `--browser` or `VISUAL_COMPARE_BROWSER`. Discovery is
  documented; set the variable to pin one.

## Disclosure

Once a fix is released, the advisory is published with credit to the reporter unless they prefer
otherwise.
