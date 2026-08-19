from pathlib import Path
import csv
import shutil

REPORT_ROOT = Path("/mnt/c/Users/Danvx/Desktop/_dedupe_results")
CSV_FILE = REPORT_ROOT / "new_images.csv"
DESTINATION = Path("/mnt/c/Users/Danvx/Desktop/icloud_dump - NEW ONLY")

DESTINATION.mkdir(parents=True, exist_ok=True)


def unique_destination(destination: Path, filename: str) -> Path:
    """
    Prevent accidental overwrites if two source files somehow
    have the same filename.
    """
    target = destination / filename

    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    counter = 2

    while True:
        candidate = destination / f"{stem}_{counter}{suffix}"

        if not candidate.exists():
            return candidate

        counter += 1


copied = 0
missing = 0

with open(CSV_FILE, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)

    for row in reader:
        source = Path(row["new_file"])

        if not source.exists():
            print(f"⚠ Missing: {source}")
            missing += 1
            continue

        target = unique_destination(DESTINATION, source.name)

        # Copies the original file as-is, including its metadata.
        shutil.copy2(source, target)

        copied += 1

        if copied % 250 == 0:
            print(f"Copied {copied:,} images...")


print("\nDONE")
print(f"Copied: {copied:,}")
print(f"Missing: {missing:,}")
print(f"\nNew-only collection:\n{DESTINATION}")