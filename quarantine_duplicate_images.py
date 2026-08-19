from pathlib import Path
import csv
import shutil
from collections import defaultdict

CHARACTER_ENGINE = Path(
    r"C:\Users\Danvx\My Stuff\Character Engine"
)

DUPLICATE_REPORT = Path(
    r"C:\Users\Danvx\Desktop\image_deduper\_dedupe_results\character_engine_duplicate_files.csv"
)

QUARANTINE = Path(
    r"C:\Users\Danvx\Desktop\Character Engine - DUPLICATES"
)

MANIFEST = Path(
    r"C:\Users\Danvx\Desktop\image_deduper\_dedupe_results\duplicate_quarantine_manifest.csv"
)

QUARANTINE.mkdir(parents=True, exist_ok=True)
MANIFEST.parent.mkdir(parents=True, exist_ok=True)


def unique_destination(target: Path) -> Path:
    """
    Never overwrite an existing quarantined file.
    """
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    counter = 2

    while True:
        candidate = target.parent / f"{stem}_{counter}{suffix}"

        if not candidate.exists():
            return candidate

        counter += 1


groups = defaultdict(list)

with open(DUPLICATE_REPORT, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)

    for row in reader:
        groups[row["group_id"]].append(Path(row["file_path"]))


print(f"Duplicate groups found: {len(groups):,}")
print("Quarantining extra copies...\n")

rows = []
moved = 0
missing = 0
groups_processed = 0

for group_id, files in groups.items():
    existing_files = [p for p in files if p.exists()]

    if len(existing_files) < 2:
        missing += len(files) - len(existing_files)
        continue

    # Keep the first listed file as the canonical copy.
    kept_file = existing_files[0]

    for duplicate_file in existing_files[1:]:
        try:
            relative_path = duplicate_file.relative_to(CHARACTER_ENGINE)

            target = QUARANTINE / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)

            final_target = unique_destination(target)

            shutil.move(str(duplicate_file), str(final_target))

            rows.append({
                "group_id": group_id,
                "kept_file": str(kept_file),
                "moved_from": str(duplicate_file),
                "moved_to": str(final_target),
            })

            moved += 1

        except Exception as e:
            print(f"ERROR moving:\n{duplicate_file}")
            print(e)

    groups_processed += 1

    if groups_processed % 50 == 0:
        print(
            f"Processed {groups_processed:,} groups "
            f"| moved {moved:,} duplicates..."
        )


with open(MANIFEST, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "group_id",
            "kept_file",
            "moved_from",
            "moved_to",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)


print("\nDONE")
print(f"Groups processed: {groups_processed:,}")
print(f"Duplicates moved: {moved:,}")
print(f"Missing files: {missing:,}")
print(f"\nQuarantine folder:\n{QUARANTINE}")
print(f"\nManifest:\n{MANIFEST}")