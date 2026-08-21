import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import unittest
from validate_post import validate_post, strip_tags, MIN_WORD_COUNT


class TestStripTags(unittest.TestCase):
    def test_removes_tags(self):
        self.assertEqual(strip_tags("<p>hello <b>world</b></p>"), " hello  world  ")


class TestValidatePost(unittest.TestCase):
    def _long_enough_text(self, extra=""):
        return ("word " * MIN_WORD_COUNT) + extra

    def test_valid_post_has_no_errors(self):
        html = f"<p>{self._long_enough_text()}</p><a href='https://gumroad.com/l/x'>Buy</a>"
        self.assertEqual(validate_post(html), [])

    def test_too_short_flagged(self):
        html = "<p>word word word</p><a href='https://gumroad.com/l/x'>Buy</a>"
        errors = validate_post(html)
        self.assertTrue(any("minimum is" in e for e in errors))

    def test_denylisted_phrase_flagged(self):
        html = f"<p>{self._long_enough_text('you should administer medicine')}</p><a href='https://gumroad.com/l/x'>Buy</a>"
        errors = validate_post(html)
        self.assertTrue(any("denylisted phrase" in e for e in errors))

    def test_missing_product_link_flagged(self):
        html = f"<p>{self._long_enough_text()}</p>"
        errors = validate_post(html)
        self.assertTrue(any("gumroad.com" in e for e in errors))

    def test_multiple_errors_accumulated(self):
        html = "<p>word you should administer</p>"
        errors = validate_post(html)
        self.assertGreater(len(errors), 1)
        self.assertTrue(any("minimum is" in e for e in errors))
        self.assertTrue(any("denylisted phrase" in e for e in errors))
        self.assertTrue(any("gumroad.com" in e for e in errors))

    def test_denylisted_phrase_case_insensitive(self):
        html = f"<p>{self._long_enough_text('You SHOULD ADMINISTER medicine')}</p><a href='https://gumroad.com/l/x'>Buy</a>"
        errors = validate_post(html)
        self.assertTrue(any("denylisted phrase" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
