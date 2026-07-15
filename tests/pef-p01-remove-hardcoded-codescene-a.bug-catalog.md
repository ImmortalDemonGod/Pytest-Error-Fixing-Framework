# Bug catalog — F13: hardcoded CodeScene access token in `scripts/analyze_code.sh`

- **Hardcoded credential literal committed to the tracked script.**
  `scripts/analyze_code.sh:119` — Wrong: the line `export CS_ACCESS_TOKEN="Njk0NjM-MjAyNi0wMS0xN1QxOTo1Mzo1Mw-I3sicmVmYWN0b3IuYWNjZXNzIiAiY2xpLmFjY2VzcyJ9.30-SmgU-Ybio83czYew_WCtu_QvyPWyWlSQQD63_gZA"` bakes a real CodeScene API access token into git history, so every checkout, `git blame`, and CI log exposes it. Correct: no credential-shaped literal appears anywhere in the file.

- **Missing-token path silently injects the baked-in secret instead of failing.**
  `scripts/analyze_code.sh:117-122` — Wrong: when `CS_ACCESS_TOKEN` is unset, the `if [ -z "$CS_ACCESS_TOKEN" ]` block prints `"CS_ACCESS_TOKEN not set. Setting a default..."`, exports the hardcoded token, and lets execution continue — so a caller who forgot to set their own token unknowingly runs with the leaked credential. Correct: the same unset-token condition must print an explicit error naming `CS_ACCESS_TOKEN` to stderr and `exit 1`, with no fallback value ever assigned.
