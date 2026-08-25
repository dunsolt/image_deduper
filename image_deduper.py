from pathlib import Path
from PIL import Image
import hashlib
import csv
import json
import shutil


IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"
}

CHARACTER_ENGINE = Path("/mnt/c/Users/Danvx/Character Engine")
INBOX = CHARACTER_ENGINE / "ZZ_Inbox"
NEW_ONLY = INBOX / "new_only"
REPORTS = INBOX / "reports"
ARCHIVE_CACHE = REPORTS / "archive_hash_cache.json"


def image_files(root: Path, *, exclude: Path | None = None, recursive: bool = True):
    iterator = root.rglob("*") if recursive else root.iterdir()

    for path in iterator:
        if exclude is not None:
            try:
                path.relative_to(exclude)
                continue
            except ValueError:
                pass

        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def count_images(root: Path, *, exclude: Path | None = None, recursive: bool = True):
    return sum(
        1
        for _ in image_files(
            root,
            exclude=exclude,
            recursive=recursive,
        )
    )


def pixel_hash(path: Path):
    """
    Decode the image and hash the actual pixel data.

    Metadata, filename and PNG/JPEG encoding do not affect this hash.
    """
    with Image.open(path) as img:
        img = img.convert("RGBA")

        hasher = hashlib.sha256()

        # Include dimensions so differently shaped images cannot match.
        hasher.update(str(img.size).encode())
        hasher.update(img.tobytes())

        return hasher.hexdigest(), img.size


def load_archive_cache():
    """Load the archive hash cache, or return an empty cache if unavailable."""
    if not ARCHIVE_CACHE.exists():
        return {}

    try:
        with open(ARCHIVE_CACHE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("Cache root is not a dictionary")

        return data

    except Exception as e:
        print(f"  Cache unavailable; rebuilding it ({e})")
        return {}


def save_archive_cache(cache):
    """Write the cache atomically so an interrupted run cannot corrupt it."""
    temporary = ARCHIVE_CACHE.with_suffix(".json.tmp")

    with open(temporary, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, sort_keys=True)

    temporary.replace(ARCHIVE_CACHE)


def copy_new_image(source: Path, digest: str) -> tuple[Path, bool]:
    """
    Copy a genuinely new image into new_only without overwriting anything.

    If an identical copy is already present, return it instead of creating
    another numbered copy. The boolean indicates whether a new copy was made.
    """
    target = NEW_ONLY / source.name

    if not target.exists():
        shutil.copy2(source, target)
        return target, True

    try:
        existing_digest, _ = pixel_hash(target)
        if existing_digest == digest:
            return target, False
    except Exception:
        pass

    stem = source.stem
    suffix = source.suffix
    counter = 2

    while True:
        candidate = NEW_ONLY / f"{stem}_{counter}{suffix}"

        if not candidate.exists():
            shutil.copy2(source, candidate)
            return candidate, True

        try:
            existing_digest, _ = pixel_hash(candidate)
            if existing_digest == digest:
                return candidate, False
        except Exception:
            pass

        counter += 1


def main():
    print("\n=== Image Deduper ===\n")

    if not CHARACTER_ENGINE.exists():
        print(
            "Error: Character Engine folder does not exist:\n"
            f"{CHARACTER_ENGINE}"
        )
        return

    if not CHARACTER_ENGINE.is_dir():
        print(
            "Error: Character Engine path is not a directory:\n"
            f"{CHARACTER_ENGINE}"
        )
        return

    if not INBOX.exists():
        print(f"Error: ZZ_Inbox folder does not exist:\n{INBOX}")
        return

    if not INBOX.is_dir():
        print(f"Error: ZZ_Inbox path is not a directory:\n{INBOX}")
        return

    print("Checking folders...")

    organised_count_preview = count_images(
        CHARACTER_ENGINE,
        exclude=INBOX,
    )

    # Only loose images directly inside ZZ_Inbox are treated as incoming.
    # Subfolders such as new_only and reports are ignored.
    inbox_count_preview = count_images(
        INBOX,
        recursive=False,
    )

    print(f"\nCharacter Engine: {organised_count_preview:,} images")
    print(f"ZZ_Inbox:        {inbox_count_preview:,} images")
    print(f"New-only folder: {NEW_ONLY}")
    print(f"Reports folder:  {REPORTS}")

    if inbox_count_preview == 0:
        print("\nNothing to scan. Drop images directly into ZZ_Inbox first.")
        return

    confirmation = input("\nStart scan? [Y/n]: ").strip().lower()

    if confirmation not in ("", "y", "yes"):
        print("Cancelled.")
        return

    NEW_ONLY.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    print("\nIndexing Character Engine (excluding ZZ_Inbox)...")

    old_cache = load_archive_cache()
    new_cache = {}
    organised_hashes = {}
    organised_count = 0
    cache_hits = 0
    freshly_hashed = 0
    errors = []

    for path in image_files(CHARACTER_ENGINE, exclude=INBOX):
        try:
            stat = path.stat()
            relative_path = str(path.relative_to(CHARACTER_ENGINE))
            cached = old_cache.get(relative_path)

            if (
                isinstance(cached, dict)
                and cached.get("size") == stat.st_size
                and cached.get("mtime_ns") == stat.st_mtime_ns
                and isinstance(cached.get("pixel_hash"), str)
                and isinstance(cached.get("width"), int)
                and isinstance(cached.get("height"), int)
            ):
                digest = cached["pixel_hash"]
                dimensions = (cached["width"], cached["height"])
                cache_hits += 1
            else:
                digest, dimensions = pixel_hash(path)
                freshly_hashed += 1

            new_cache[relative_path] = {
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "pixel_hash": digest,
                "width": dimensions[0],
                "height": dimensions[1],
            }

            organised_hashes.setdefault(digest, []).append({
                "path": path,
                "dimensions": dimensions,
            })

            organised_count += 1

            if organised_count % 250 == 0:
                print(
                    f"  Indexed {organised_count:,} organised images "
                    f"| cached: {cache_hits:,} "
                    f"| hashed: {freshly_hashed:,}"
                )

        except Exception as e:
            errors.append((str(path), str(e)))

    try:
        save_archive_cache(new_cache)
    except Exception as e:
        errors.append((str(ARCHIVE_CACHE), f"Could not save archive cache: {e}"))
        print(f"WARNING: Could not save archive cache: {e}")

    print(f"\nIndexed {organised_count:,} organised images.")
    print(f"Archive cache hits:       {cache_hits:,}")
    print(f"Archive images hashed:    {freshly_hashed:,}")
    print("\nComparing ZZ_Inbox...")

    archive_matches = []
    batch_duplicates = []
    new_images = []
    inbox_hashes = {}
    checked_count = 0

    for path in image_files(INBOX, recursive=False):
        try:
            digest, dimensions = pixel_hash(path)
            checked_count += 1

            if digest in organised_hashes:
                for existing in organised_hashes[digest]:
                    archive_matches.append({
                        "inbox_file": str(path),
                        "existing_file": str(existing["path"]),
                        "pixel_hash": digest,
                        "width": dimensions[0],
                        "height": dimensions[1],
                    })
                continue

            if digest in inbox_hashes:
                original = inbox_hashes[digest]
                batch_duplicates.append({
                    "duplicate_file": str(path),
                    "first_file": str(original["path"]),
                    "pixel_hash": digest,
                    "width": dimensions[0],
                    "height": dimensions[1],
                })
                continue

            inbox_hashes[digest] = {
                "path": path,
                "dimensions": dimensions,
            }

            new_images.append({
                "new_file": str(path),
                "pixel_hash": digest,
                "width": dimensions[0],
                "height": dimensions[1],
            })

            if checked_count % 250 == 0:
                print(
                    f"  Checked {checked_count:,} inbox images "
                    f"| in archive: {len(archive_matches):,} "
                    f"| batch duplicates: {len(batch_duplicates):,} "
                    f"| new: {len(new_images):,}"
                )

        except Exception as e:
            errors.append((str(path), str(e)))

    with open(
        REPORTS / "already_in_archive.csv",
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "inbox_file",
                "existing_file",
                "pixel_hash",
                "width",
                "height",
            ],
        )
        writer.writeheader()
        writer.writerows(archive_matches)

    with open(
        REPORTS / "duplicates_within_inbox.csv",
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "duplicate_file",
                "first_file",
                "pixel_hash",
                "width",
                "height",
            ],
        )
        writer.writeheader()
        writer.writerows(batch_duplicates)

    with open(
        REPORTS / "new_images.csv",
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "new_file",
                "pixel_hash",
                "width",
                "height",
            ],
        )
        writer.writeheader()
        writer.writerows(new_images)

    with open(
        REPORTS / "errors.csv",
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["file", "error"])
        writer.writerows(errors)

    print("\nCopying genuinely new images to new_only...")

    copied_count = 0
    already_copied_count = 0

    for row in new_images:
        source = Path(row["new_file"])

        try:
            _, copied = copy_new_image(source, row["pixel_hash"])

            if copied:
                copied_count += 1
            else:
                already_copied_count += 1

        except Exception as e:
            errors.append((str(source), f"Copy to new_only failed: {e}"))
            print(f"ERROR copying to new_only:\n{source}\n{e}")

    # Rewrite errors.csv so copy errors are included too.
    with open(
        REPORTS / "errors.csv",
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["file", "error"])
        writer.writerows(errors)

    print("\nDONE")
    print(f"Character Engine scanned: {organised_count:,} images")
    print(f"Archive cache hits:       {cache_hits:,}")
    print(f"Archive images hashed:    {freshly_hashed:,}")
    print(f"ZZ_Inbox checked:         {checked_count:,} images")
    print(f"Already in archive:       {len(archive_matches):,}")
    print(f"Duplicates within inbox:  {len(batch_duplicates):,}")
    print(f"Genuinely new:            {len(new_images):,}")
    print(f"Copied to new_only:       {copied_count:,}")
    print(f"Already in new_only:      {already_copied_count:,}")
    print(f"Errors:                   {len(errors):,}")
    print(f"\nNew images copied to:\n{NEW_ONLY}")
    print(f"\nReports saved to:\n{REPORTS}")


if __name__ == "__main__":
    main()
