import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import csv
import io
import tempfile
import unittest
import zipfile

from validate_product import validate_product


def _make_zip(path, tracker_header=("date", "notes"), tracker_rows=None, guide_words=300):
    tracker_rows = tracker_rows or [["2026-08-21", "example"]]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(tracker_header)
    writer.writerows(tracker_rows)
    guide_text = "word " * guide_words
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("tracker.csv", buf.getvalue())
        zf.writestr("guide.html", f"<p>{guide_text}</p>")


class TestValidateProduct(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.zip_path = Path(self.tmp.name) / "product.zip"

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_product_has_no_errors(self):
        _make_zip(self.zip_path)
        self.assertEqual(validate_product(self.zip_path), [])

    def test_missing_file_flagged(self):
        with zipfile.ZipFile(self.zip_path, "w") as zf:
            zf.writestr("tracker.csv", "date,notes\n2026-08-21,example\n")
        errors = validate_product(self.zip_path)
        self.assertTrue(any("missing files" in e for e in errors))

    def test_missing_column_flagged(self):
        _make_zip(self.zip_path, tracker_header=("date",))
        errors = validate_product(self.zip_path)
        self.assertTrue(any("missing required columns" in e for e in errors))

    def test_short_guide_flagged(self):
        _make_zip(self.zip_path, guide_words=10)
        errors = validate_product(self.zip_path)
        self.assertTrue(any("too short" in e for e in errors))

    def test_missing_zip_raises_error(self):
        """Validate that missing zip file raises OSError."""
        nonexistent = Path(self.tmp.name) / "nonexistent.zip"
        with self.assertRaises(OSError):
            validate_product(nonexistent)


if __name__ == "__main__":
    unittest.main()
