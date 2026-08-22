from pathlib import Path
from PIL import Image
import hashlib
import csv
from collections import defaultdict


IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"
}

CHARACTER_ENGINE = Path("/mnt/c/Users/Danvx/My Stuff/Character Engine")
INBOX = CHARACTER_ENGINE / "ZZ_Inbox"
REPORTS = INBOX / "reports"
GROUPS_CSV = REPORTS / "character_engine_duplicate_groups.csv"
FILES_CSV = REPORTS / "character_engine_duplicate_files.csv"
ERRORS_CSV = REPORTS / "character_engine_duplicate_errors.csv"


def image_files(root: Path):
    for path in root.rglob("*"):
        try:
            path.relative_to(INBOX)
            continue
        except ValueError:
            pass

        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def pixel_hash(path: Path):
    """
    Hash decoded pixel data so metadata, filenames, and encoding differences
    do not matter.
    """
    with Image.open(path) as img:
        img = img.convert("RGBA")

        hasher = hashlib.sha256()
        hasher.update(str(img.size).encode())
        hasher.update(img.tobytes())

        return hasher.hexdigest(), img.size


def main():
    print("\n=== Character Engine Duplicate Audit ===\n")
    print(f"Character Engine: {CHARACTER_ENGINE}")
    print(f"Ignoring:         {INBOX}")
    print(f"Reports:          {REPORTS}")
    print("\nThis script is report-only. It will not move or delete any files.\n")

    if not CHARACTER_ENGINE.exists() or not CHARACTER_ENGINE.is_dir():
        print(f"Error: Character Engine folder is invalid:\n{CHARACTER_ENGINE}")
        return

    REPORTS.mkdir(parents=True, exist_ok=True)

    confirmation = input("Start audit? [Y/n]: ").strip().lower()
    if confirmation not in ("", "y", "yes"):
        print("Cancelled.")
        return

    hash_to_files = defaultdict(list)
    errors = []
    scanned = 0

    print("\nScanning Character Engine...")

    for path in image_files(CHARACTER_ENGINE):
        try:
            digest, dimensions = pixel_hash(path)

            hash_to_files[digest].append({
                "path": path,
                "width": dimensions[0],
                "height": dimensions[1],
            })

            scanned += 1

            if scanned % 250 == 0:
                print(f"  Scanned {scanned:,} images...")

        except Exception as e:
            errors.append((str(path), str(e)))

    duplicate_groups = []
    duplicate_files = []
    group_id = 0
    extra_copies = 0

    for digest, files in hash_to_files.items():
        if len(files) < 2:
            continue

        group_id += 1
        extra_copies += len(files) - 1

        duplicate_groups.append({
            "group_id": group_id,
            "pixel_hash": digest,
            "copies": len(files),
            "width": files[0]["width"],
            "height": files[0]["height"],
            "sample_file": str(files[0]["path"]),
        })

        for item in files:
            duplicate_files.append({
                "group_id": group_id,
                "pixel_hash": digest,
                "file_path": str(item["path"]),
                "relative_path": str(item["path"].relative_to(CHARACTER_ENGINE)),
                "width": item["width"],
                "height": item["height"],
            })

    with open(GROUPS_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "group_id",
                "pixel_hash",
                "copies",
                "width",
                "height",
                "sample_file",
            ],
        )
        writer.writeheader()
        writer.writerows(duplicate_groups)

    with open(FILES_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "group_id",
                "pixel_hash",
                "file_path",
                "relative_path",
                "width",
                "height",
            ],
        )
        writer.writeheader()
        writer.writerows(duplicate_files)

    with open(ERRORS_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["file", "error"])
        writer.writerows(errors)

    print("\nDONE")
    print(f"Images scanned:          {scanned:,}")
    print(f"Duplicate groups:        {group_id:,}")
    print(f"Extra duplicate copies:  {extra_copies:,}")
    print(f"Errors:                  {len(errors):,}")
    print(f"\nReports saved to:\n{REPORTS}")
    print("\nNo files were moved or deleted.")


if __name__ == "__main__":
    main()
