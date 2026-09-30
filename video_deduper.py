from pathlib import Path
import csv
import re
import shutil


VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".wmv"
}

CHARACTER_ENGINE = Path("/mnt/c/Users/Danvx/Character Engine")
INBOX = CHARACTER_ENGINE / "ZZ_Inbox"
VIDEO_NEW_ONLY = INBOX / "video_new_only"
REPORTS = INBOX / "reports"

COPY_SUFFIX_PATTERN = re.compile(
    r"(?:\s*\(\d+\)|\s*-\s*copy(?:\s*\(\d+\))?|\s+copy(?:\s*\(\d+\))?|_copy(?:_?\d+)?)$",
    re.IGNORECASE,
)


def video_files(root: Path, *, exclude: Path | None = None, recursive: bool = True):
    iterator = root.rglob("*") if recursive else root.iterdir()

    for path in iterator:
        if exclude is not None:
            try:
                path.relative_to(exclude)
                continue
            except ValueError:
                pass

        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
            yield path


def normalise_filename(path: Path) -> str:
    """
    Return a conservative comparison name for a video.

    Common duplicate-download suffixes are removed repeatedly, so names such as
    'clip (1).mp4' and 'clip - Copy.mp4' both compare as 'clip'.
    """
    name = path.stem.strip()

    while True:
        cleaned = COPY_SUFFIX_PATTERN.sub("", name).strip()
        if cleaned == name:
            break
        name = cleaned

    return name.casefold()


def copy_new_video(source: Path) -> tuple[Path, bool]:
    """Copy a new video without overwriting an existing file."""
    target = VIDEO_NEW_ONLY / source.name

    if not target.exists():
        shutil.copy2(source, target)
        return target, True

    source_stat = source.stat()
    target_stat = target.stat()

    if source_stat.st_size == target_stat.st_size:
        return target, False

    stem = source.stem
    suffix = source.suffix
    counter = 2

    while True:
        candidate = VIDEO_NEW_ONLY / f"{stem}_{counter}{suffix}"

        if not candidate.exists():
            shutil.copy2(source, candidate)
            return candidate, True

        if candidate.stat().st_size == source_stat.st_size:
            return candidate, False

        counter += 1


def write_report(filename: str, fieldnames: list[str], rows: list[dict]):
    with open(
        REPORTS / filename,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    print("\n=== Video Deduper ===\n")

    if not CHARACTER_ENGINE.exists() or not CHARACTER_ENGINE.is_dir():
        print(f"Error: Character Engine folder is invalid:\n{CHARACTER_ENGINE}")
        return

    if not INBOX.exists() or not INBOX.is_dir():
        print(f"Error: ZZ_Inbox folder is invalid:\n{INBOX}")
        return

    archive_videos = list(video_files(CHARACTER_ENGINE, exclude=INBOX))
    inbox_videos = list(video_files(INBOX, recursive=False))

    print(f"Character Engine: {len(archive_videos):,} videos")
    print(f"ZZ_Inbox:        {len(inbox_videos):,} videos")
    print(f"Video new-only:  {VIDEO_NEW_ONLY}")
    print(f"Reports folder:  {REPORTS}")

    if not inbox_videos:
        print("\nNothing to scan. Drop videos directly into ZZ_Inbox first.")
        return

    confirmation = input("\nStart video scan? [Y/n]: ").strip().lower()

    if confirmation not in ("", "y", "yes"):
        print("Cancelled.")
        return

    VIDEO_NEW_ONLY.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    archive_by_name = {}
    errors = []

    for path in archive_videos:
        try:
            key = normalise_filename(path)
            archive_by_name.setdefault(key, []).append({
                "path": path,
                "size": path.stat().st_size,
            })
        except Exception as e:
            errors.append((str(path), str(e)))

    likely_duplicates = []
    possible_duplicates = []
    new_videos = []
    inbox_seen = {}

    for path in inbox_videos:
        try:
            key = normalise_filename(path)
            size = path.stat().st_size

            candidates = list(archive_by_name.get(key, []))
            candidates.extend(inbox_seen.get(key, []))

            if candidates:
                same_size = [item for item in candidates if item["size"] == size]

                if same_size:
                    for match in same_size:
                        likely_duplicates.append({
                            "inbox_file": str(path),
                            "matching_file": str(match["path"]),
                            "normalised_name": key,
                            "inbox_size": size,
                            "matching_size": match["size"],
                        })
                else:
                    for match in candidates:
                        possible_duplicates.append({
                            "inbox_file": str(path),
                            "matching_file": str(match["path"]),
                            "normalised_name": key,
                            "inbox_size": size,
                            "matching_size": match["size"],
                        })

                inbox_seen.setdefault(key, []).append({
                    "path": path,
                    "size": size,
                })
                continue

            inbox_seen.setdefault(key, []).append({
                "path": path,
                "size": size,
            })

            new_videos.append({
                "new_file": str(path),
                "normalised_name": key,
                "size": size,
            })

        except Exception as e:
            errors.append((str(path), str(e)))

    write_report(
        "video_likely_duplicates.csv",
        ["inbox_file", "matching_file", "normalised_name", "inbox_size", "matching_size"],
        likely_duplicates,
    )
    write_report(
        "video_possible_duplicates.csv",
        ["inbox_file", "matching_file", "normalised_name", "inbox_size", "matching_size"],
        possible_duplicates,
    )
    write_report(
        "new_videos.csv",
        ["new_file", "normalised_name", "size"],
        new_videos,
    )

    copied_count = 0
    already_copied_count = 0

    for row in new_videos:
        source = Path(row["new_file"])

        try:
            _, copied = copy_new_video(source)
            if copied:
                copied_count += 1
            else:
                already_copied_count += 1
        except Exception as e:
            errors.append((str(source), f"Copy to video_new_only failed: {e}"))

    with open(
        REPORTS / "video_errors.csv",
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["file", "error"])
        writer.writerows(errors)

    print("\nDONE")
    print(f"Archive videos scanned:  {len(archive_videos):,}")
    print(f"ZZ_Inbox checked:        {len(inbox_videos):,}")
    print(f"Likely duplicates:       {len(likely_duplicates):,}")
    print(f"Possible duplicates:     {len(possible_duplicates):,}")
    print(f"New videos:              {len(new_videos):,}")
    print(f"Copied to video_new_only:{copied_count:>6,}")
    print(f"Already copied:          {already_copied_count:>6,}")
    print(f"Errors:                  {len(errors):,}")
    print(f"\nNew videos copied to:\n{VIDEO_NEW_ONLY}")
    print(f"\nReports saved to:\n{REPORTS}")


if __name__ == "__main__":
    main()
