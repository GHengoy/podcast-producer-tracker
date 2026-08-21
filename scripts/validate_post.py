"""Content-safety and structure validation for blog post HTML fragments."""
import re
import sys
from pathlib import Path

MIN_WORD_COUNT = 500

DENYLISTED_PHRASES = [
    "should administer",
    "diagnos",
    "treats your pet",
    "cures",
    "prescri",
    "dosage",
    "veterinary diagnosis",
]

TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(html: str) -> str:
    """Remove HTML tags, returning plain text for word-count/phrase checks."""
    return TAG_RE.sub(" ", html)


def validate_post(html: str) -> list[str]:
    """Check a post's HTML body against content-safety and structure rules."""
    errors = []
    text = strip_tags(html)
    word_count = len(text.split())
    if word_count < MIN_WORD_COUNT:
        errors.append(f"post is {word_count} words, minimum is {MIN_WORD_COUNT}")

    lowered = html.lower()
    for phrase in DENYLISTED_PHRASES:
        if phrase in lowered:
            errors.append(f"contains denylisted phrase: '{phrase}'")

    if "gumroad.com" not in lowered:
        errors.append("missing a gumroad.com product link")

    return errors


def main(argv):
    if len(argv) != 2:
        print("usage: validate_post.py <path>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    try:
        html = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"could not read file: {e}", file=sys.stderr)
        return 2
    errors = validate_post(html)
    if errors:
        print(f"INVALID: {path}")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
