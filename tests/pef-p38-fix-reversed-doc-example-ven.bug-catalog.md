# Bug catalog — F47 (reversed() doc example)

- **BUG-1 (the finding itself)**: `docs/reference/hypothesis-guide.md:164` — the
  `test_reverse_twice_is_identity` example asserts `reversed(reversed(xs)) == xs`. `reversed(xs)`
  on a `list` returns a `list_reverseiterator`, and `reversed()` on that iterator raises
  `TypeError: argument to reversed() must be a sequence` — the assertion can never execute, let
  alone pass. Wrong: `assert reversed(reversed(xs)) == xs`. Correct: `assert
  list(reversed(list(reversed(xs)))) == xs` (each `reversed()` call is re-wrapped in `list()` so
  the second `reversed()` receives a sequence again).

- **BUG-2 (partial fix)**: only one of the two `reversed()` calls gets wrapped in `list()` (e.g.
  `assert list(reversed(reversed(xs))) == xs` or `assert reversed(list(reversed(xs))) == xs`).
  The inner/outer `reversed()` call that is still unwrapped still raises `TypeError` on a `list`
  input, so the example remains broken even though it now "looks" fixed at a glance.

- **BUG-3 (silent input-type drift)**: the example's `xs` strategy is changed away from
  `st.lists(st.integers())` to something that is not list-shaped (e.g. a bare `st.integers()` or
  `st.tuples(...)`), reintroducing the same class of bug for the new element type, or masking it
  by accident (e.g. a `tuple` still supports `reversed()` on the *result* of `reversed()`
  differently than expected).

- **BUG-4 (stale comment)**: the corrected code keeps the explanatory comment ("`reversed()`
  returns an iterator, not a sequence — wrap each call in `list()`...") but the code below it no
  longer matches that description (e.g. drifts back to unwrapped `reversed()` in a later edit),
  leaving a comment that documents behavior the code no longer has.
