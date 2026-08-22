# image_deduper

Simple workflow for importing new images into my Character Engine.

## Folder setup

New images go here:

`Character Engine/ZZ_Inbox`

Only loose images directly inside `ZZ_Inbox` are treated as new input.

The scripts ignore subfolders inside `ZZ_Inbox`.

## Process

### 1. Dedupe

Run:

```bash
python image_deduper.py
```

This:

- compares `ZZ_Inbox` against the existing Character Engine
- ignores `ZZ_Inbox` when scanning the archive
- detects duplicates within the inbox batch
- copies genuinely new images into:

`ZZ_Inbox/new_only`

Nothing in the Character Engine archive is moved or deleted.

Reports are written to:

`ZZ_Inbox/reports`

### 2. Rename

Run:

```bash
python rename_new_images.py
```

This:

- reads images from `ZZ_Inbox/new_only`
- finds the highest existing `gen_XXXXXX` number in Character Engine
- creates renamed copies in:

`ZZ_Inbox/ready_to_sort`

Example:

`gen_001234.png`

The originals in `new_only` are left untouched.

### 3. Manually sort

Open:

`ZZ_Inbox/ready_to_sort`

Move the renamed images into the appropriate Character Engine folders manually.

## Normal workflow

`ZZ_Inbox → dedupe → new_only → rename → ready_to_sort → manually sort`
