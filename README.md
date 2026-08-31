# photoscripts

a collection of Python scripts to manage a photo/video library:

## Files

- **`rename_file.py`** - Renames files by replacing "Photo" and "Vidéo" prefixes in filenames
- **`rename_exif.py`** - Organizes media files by prepending their creation date (from EXIF metadata or file modification time) in ISO 8601 format
- **`rotate_video.py`** - Rotates videos using ffmpeg (0=90° counter-clockwise+flip, 1=90° clockwise, 2=90° counter-clockwise, 3=90° clockwise+flip)

## Installation

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
