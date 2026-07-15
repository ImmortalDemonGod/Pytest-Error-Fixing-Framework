import re
from pathlib import Path

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "reference" / "hypothesis-guide.md"

EXPECTED_ASSERTION = "list(reversed(list(reversed(xs)))) == xs"


def test_reverse_twice_is_identity_doc_example_is_correct():
    xs = [1, 2, 3]
    content = DOC_PATH.read_text()

    match = re.search(
        r"def test_reverse_twice_is_identity\(xs\):\n(?:.*\n)*?\s*assert (.+)",
        content,
    )
    assertion_expr = match.group(1).strip() if match else ""

    assert assertion_expr == EXPECTED_ASSERTION, (
        f"docs/reference/hypothesis-guide.md's test_reverse_twice_is_identity example asserts "
        f"{assertion_expr!r}; expected the roundtrip-safe {EXPECTED_ASSERTION!r} "
        f"(reversed(xs) returns a list_reverseiterator, so the second reversed() call needs a "
        f"list() wrapper to receive a sequence again)"
    )

    assert eval(assertion_expr, {"xs": xs})
