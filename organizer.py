

import os
import shutil
from datetime import datetime

# ─── File Category Map ─────────────────────────────────────────────────────────
# Sub-folders under Documents\ get their own dedicated folder.
FILE_CATEGORIES: dict = {
    "Documents/Word":        [".doc", ".docx", ".odt", ".rtf"],
    "Documents/PDF":         [".pdf"],
    "Documents/Excel":       [".xls", ".xlsx", ".csv"],
    "Documents/PowerPoint":  [".ppt", ".pptx"],
    "Documents/Text":        [".txt", ".log", ".md"],
    "Images":                [".jpg", ".jpeg", ".png", ".gif", ".bmp",
                              ".svg", ".webp", ".ico", ".tiff", ".raw",
                              ".heic", ".psd"],
    "Movies":                [".mp4", ".mkv", ".avi", ".mov", ".wmv",
                              ".flv", ".webm", ".m4v", ".mpeg", ".m2ts"],
    "Music":                 [".mp3", ".wav", ".flac", ".aac", ".ogg",
                              ".wma", ".m4a", ".aiff"],
    "Archives":              [".zip", ".rar", ".7z", ".tar", ".gz",
                              ".bz2", ".xz"],
    "Programs":              [".exe", ".msi", ".apk", ".dmg", ".sh",
                              ".bat", ".cmd"],
    # ── Code sub-folders ──────────────────────────────────────────────────────
    "Code/Python":           [".py", ".pyw", ".pyi"],
    "Code/C++":              [".cpp", ".cxx", ".cc", ".c", ".h", ".hpp"],
    "Code/Web":              [".html", ".htm", ".css", ".js", ".ts",
                              ".jsx", ".tsx", ".vue", ".scss", ".sass"],
    "Code/Java":             [".java", ".jar", ".class"],
    "Code/C#":               [".cs", ".csproj"],
    "Code/PHP":              [".php"],
    "Code/Other Code":       [".rb", ".go", ".rs", ".swift", ".kt",
                              ".sql", ".json", ".xml", ".yaml", ".yml",
                              ".sh", ".bash"],
    "Others":                [],  # catch-all
}


def get_category(extension: str) -> str:
    """Return the relative folder path for a given file extension."""
    ext = extension.lower()
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    return "Others"


def collect_files(root_folder: str, include_subfolders: bool = False) -> list:
    """
    Return a list of absolute file paths inside *root_folder*.
    If *include_subfolders* is True, walks all sub-directories recursively.
    """
    files = []
    if include_subfolders:
        for dirpath, _, filenames in os.walk(root_folder):
            for f in filenames:
                files.append(os.path.join(dirpath, f))
    else:
        for item in os.listdir(root_folder):
            full = os.path.join(root_folder, item)
            if os.path.isfile(full):
                files.append(full)
    return files


def organize_folder(
    folder: str,
    include_subfolders: bool = False,
    save_log: bool = True,
    progress_callback=None,
) -> dict:
    """
    Move every file in *folder* into a named sub-folder by category.

    Args:
        folder:              Absolute path to the target folder.
        include_subfolders:  Whether to recurse into sub-folders.
        save_log:            Whether to write organizer_log.txt.
        progress_callback:   Optional callable(filename, category, status)
                             called for every file processed.

    Returns:
        dict with keys: moved, skipped, errors, log_path (or None).
    """
    files     = collect_files(folder, include_subfolders)
    moved     = 0
    skipped   = 0
    errors    = 0
    log_lines = []

    for src in files:
        filename = os.path.basename(src)
        _, ext   = os.path.splitext(filename)
        category = get_category(ext)

        # Build destination folder (supports nested paths like Documents/Word)
        dest_dir = os.path.join(folder, *category.split("/"))
        os.makedirs(dest_dir, exist_ok=True)

        dest = os.path.join(dest_dir, filename)

        # Already in the right place?
        if os.path.abspath(os.path.dirname(src)) == os.path.abspath(dest_dir):
            skipped += 1
            if progress_callback:
                progress_callback(filename, category, "skip")
            continue

        # Collision → add timestamp suffix
        if os.path.exists(dest):
            base, extension = os.path.splitext(filename)
            dest = os.path.join(
                dest_dir,
                f"{base}_{int(datetime.now().timestamp())}{extension}",
            )

        try:
            shutil.move(src, dest)
            moved += 1
            log_lines.append(f"{src} --> {dest}")
            if progress_callback:
                progress_callback(filename, category, "ok")
        except Exception as exc:
            errors += 1
            if progress_callback:
                progress_callback(filename, category, f"error:{exc}")

    # Persist log
    log_path = None
    if save_log and log_lines:
        log_path = os.path.join(folder, "organizer_log.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n")
            f.writelines(line + "\n" for line in log_lines)

    return {
        "moved":    moved,
        "skipped":  skipped,
        "errors":   errors,
        "log_path": log_path,
    }


def undo_organize(folder: str, progress_callback=None) -> dict:
    """
    Reverse the last organize operation by reading organizer_log.txt
    and moving every file back to its original location.

    Args:
        folder:            The folder that was previously organized.
        progress_callback: Optional callable(filename, status) for UI updates.

    Returns:
        dict with keys: restored, skipped, errors.
    """
    log_path = os.path.join(folder, "organizer_log.txt")

    if not os.path.isfile(log_path):
        return {"restored": 0, "skipped": 0, "errors": 0,
                "error_msg": "No organizer_log.txt found in this folder."}

    # Read all move records  "src --> dest"
    moves = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if " --> " in line and not line.startswith("["):
                parts = line.split(" --> ", 1)
                if len(parts) == 2:
                    moves.append((parts[0], parts[1]))

    if not moves:
        return {"restored": 0, "skipped": 0, "errors": 0,
                "error_msg": "Log file is empty – nothing to undo."}

    restored = 0
    skipped  = 0
    errors   = 0

    # Reverse in LIFO order so nested moves undo correctly
    for original_src, moved_dest in reversed(moves):
        filename = os.path.basename(moved_dest)

        if not os.path.isfile(moved_dest):
            skipped += 1
            if progress_callback:
                progress_callback(filename, "skip")
            continue

        # Recreate original parent directory if needed
        os.makedirs(os.path.dirname(original_src), exist_ok=True)

        # Collision guard
        dest = original_src
        if os.path.exists(dest):
            base, ext = os.path.splitext(filename)
            dest = os.path.join(
                os.path.dirname(original_src),
                f"{base}_restored_{int(datetime.now().timestamp())}{ext}",
            )

        try:
            shutil.move(moved_dest, dest)
            restored += 1
            if progress_callback:
                progress_callback(filename, "ok")
        except Exception as exc:
            errors += 1
            if progress_callback:
                progress_callback(filename, f"error:{exc}")

    # Remove log file after successful undo
    if restored > 0 and errors == 0:
        try:
            os.remove(log_path)
        except Exception:
            pass

    return {"restored": restored, "skipped": skipped, "errors": errors}
