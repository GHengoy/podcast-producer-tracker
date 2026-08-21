"""Validation for the packaged product ZIP (tracker CSV + guide)."""
import csv
import io
import sys
import zipfile
from pathlib import Path

REQUIRED_FILES = {"tracker.csv", "guide.html"}
REQUIRED_CSV_COLUMNS = {"date", "notes"}


def validate_product(zip_path) -> list[str]:
    """Check the product ZIP contains the required files and the tracker has the required columns."""
    errors = []
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        missing = REQUIRED_FILES - names
        if missing:
            errors.append(f"missing files in product zip: {sorted(missing)}")
            return errors

        with zf.open("tracker.csv") as f:
            reader = csv.reader(io.TextIOWrapper(f, encoding="utf-8"))
            header = set(next(reader, []))
            missing_cols = REQUIRED_CSV_COLUMNS - header
            if missing_cols:
                errors.append(f"tracker.csv missing required columns: {sorted(missing_cols)}")

        with zf.open("guide.html") as f:
            guide_text = f.read().decode("utf-8")
            if len(guide_text.split()) < 300:
                errors.append("guide.html is too short (minimum 300 words)")

    return errors


def main(argv):
    if len(argv) != 2:
        print("usage: validate_product.py <zip_path>", file=sys.stderr)
        return 2
    try:
        errors = validate_product(Path(argv[1]))
    except (OSError, zipfile.BadZipFile) as e:
        print(f"could not read zip: {e}", file=sys.stderr)
        return 2
    if errors:
        print(f"INVALID: {argv[1]}")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK: {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
