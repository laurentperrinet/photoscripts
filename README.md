# photoscripts

a collection of Python scripts to manage a photo/video library:

## Files

- **`rename_exif.py`** - Organizes media files by prepending their creation date (from EXIF metadata or file modification time) in ISO 8601 format. Processes pictures (jpg, jpeg, png) using EXIF data first, falling back to file modification time. For movies (mp4, mpg, mov, 3gp), extracts creation time via ffprobe. Cleans existing date prefixes from filenames to avoid duplicates.

- **`rename_file.py`** - Renames files by replacing "Photo" and "Vidéo" prefixes in filenames. Supports dry-run mode and verbose output for safe preview before renaming.

- **`rotate_video.py`** - Rotates videos using ffmpeg. Supports 4 rotation modes: 0=90° counter-clockwise+vertical flip (default), 1=90° clockwise, 2=90° counter-clockwise, 3=90° clockwise+vertical flip. Accepts `-c` flag for counter-clockwise rotation.

## Installation

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
