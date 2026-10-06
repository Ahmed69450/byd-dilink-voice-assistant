#!/usr/bin/env python3
"""
Helper script to download and extract the Arabic acoustic model for Vosk STT.

Downloads vosk-model-small-ar-0.22.zip from alphacephei.com and extracts
it directly into android/app/src/main/assets/model-ar/ with a live progress bar.
"""

import argparse
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

# Ensure UTF-8 output across environments
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-ar-0.22.zip"
DEFAULT_MODEL_NAME = "vosk-model-small-ar-0.22"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DEST_DIR = PROJECT_ROOT / "android" / "app" / "src" / "main" / "assets" / "model-ar"


def print_progress_bar(
    iteration: int,
    total: int,
    prefix: str = "Downloading",
    suffix: str = "",
    length: int = 40,
) -> None:
    """Renders a terminal progress bar."""
    if total > 0:
        percent = min(1.0, iteration / total)
        filled_len = int(round(length * percent))
        bar = "=" * (filled_len - 1) + ">" if filled_len > 0 else ""
        bar = bar.ljust(length, " ")
        percent_str = f"{percent * 100:5.1f}%"
        output = f"\r{prefix} [{bar}] {percent_str} {suffix}"
    else:
        mb = iteration / (1024 * 1024)
        output = f"\r{prefix}: {mb:6.1f} MB downloaded {suffix}"

    sys.stdout.write(output)
    sys.stdout.flush()


def download_model_zip(
    url: str,
    zip_dest: Path,
    chunk_size: int = 64 * 1024,
) -> Path:
    """
    Downloads the model zip file from url to zip_dest with a live progress bar.
    """
    zip_dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (VoskModelDownloader; BYD-DiLink)"},
    )

    print(f"Connecting to {url}...")
    with urllib.request.urlopen(req, timeout=60) as response:
        total_size = int(response.headers.get("Content-Length", 0))
        total_mb = total_size / (1024 * 1024) if total_size > 0 else 0.0

        downloaded = 0
        with open(zip_dest, "wb") as out_f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                out_f.write(chunk)
                downloaded += len(chunk)
                suffix = f"({downloaded / (1024 * 1024):5.1f}MB / {total_mb:5.1f}MB)" if total_size > 0 else ""
                print_progress_bar(downloaded, total_size, prefix="Downloading", suffix=suffix)

    print()  # newline after progress bar
    print(f"Download complete: {zip_dest} ({zip_dest.stat().st_size / (1024 * 1024):.1f} MB)")
    return zip_dest


def extract_model_archive(
    zip_path: Path,
    dest_dir: Path,
    clean_target: bool = False,
) -> None:
    """
    Extracts the Vosk model zip file into dest_dir, stripping the single
    root enclosing directory if present (e.g. vosk-model-small-ar-0.22/).
    """
    if clean_target and dest_dir.exists():
        print(f"Cleaning existing target directory: {dest_dir}...")
        shutil.rmtree(dest_dir)

    dest_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.infolist()
        if not members:
            raise ValueError(f"Zip archive is empty: {zip_path}")

        # Detect if all items share a single top-level directory
        top_dirs = {
            m.filename.split("/")[0]
            for m in members
            if "/" in m.filename and not m.filename.startswith("/")
        }
        strip_prefix = ""
        if len(top_dirs) == 1:
            candidate_prefix = list(top_dirs)[0] + "/"
            if all(m.filename.startswith(candidate_prefix) or m.filename == list(top_dirs)[0] for m in members):
                strip_prefix = candidate_prefix

        total_members = len(members)
        print(f"Extracting {total_members} files to {dest_dir}...")

        for idx, member in enumerate(members, start=1):
            rel_name = member.filename
            if strip_prefix and rel_name.startswith(strip_prefix):
                rel_name = rel_name[len(strip_prefix):]

            if not rel_name:
                continue

            target_file = dest_dir / rel_name

            # Prevent directory traversal vulnerability (zip slip)
            try:
                target_file.resolve().relative_to(dest_dir.resolve())
            except ValueError:
                raise ValueError(f"Illegal path in zip archive: {member.filename}")

            if member.is_dir():
                target_file.mkdir(parents=True, exist_ok=True)
            else:
                target_file.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as source_stream, open(target_file, "wb") as target_stream:
                    shutil.copyfileobj(source_stream, target_stream)

            print_progress_bar(idx, total_members, prefix="Extracting ", suffix=f"({idx}/{total_members})")

    print()  # newline after progress bar
    print(f"Extraction successfully completed: {dest_dir}")


def verify_model_dir(dest_dir: Path) -> bool:
    """Verifies that model files exist in target directory."""
    if not dest_dir.is_dir():
        return False
    # Check for non-empty directory or common vosk model structure
    items = list(dest_dir.iterdir())
    return len(items) > 0


def print_cli_instructions(dest_dir: Path) -> None:
    """Prints usage and build instructions."""
    print("=" * 65)
    print(" Vosk Arabic Model Ready for BYD DiLink Assistant")
    print("=" * 65)
    print(f"Model location : {dest_dir.resolve()}")
    print()
    print("Next Steps:")
    print("1. Android Asset Integration:")
    print("   The model files are now stored under:")
    print("   android/app/src/main/assets/model-ar/")
    print()
    print("2. Runtime Behavior:")
    print("   On app startup, STTEngine will automatically unpack the model")
    print("   into internal app storage and initialize offline Arabic recognition.")
    print()
    print("3. Build the Android Application:")
    print("   cd android && ./gradlew assembleDebug")
    print("=" * 65)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download and extract offline Arabic Vosk speech model for BYD DiLink Assistant."
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_MODEL_URL,
        help=f"URL to vosk model zip archive (default: {DEFAULT_MODEL_URL})",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(DEFAULT_DEST_DIR),
        help=f"Destination directory for extracted model (default: {DEFAULT_DEST_DIR})",
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="Optional cache directory to keep downloaded zip archive",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing output directory before extraction",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download and overwrite even if model files already exist",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download if zip archive is already cached locally",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if model is already installed in output directory",
    )

    args = parser.parse_args()
    dest_path = Path(args.output).resolve()

    if args.check:
        if verify_model_dir(dest_path):
            print(f"[OK] Vosk model files found at: {dest_path}")
            return 0
        else:
            print(f"[MISSING] No model files found at: {dest_path}")
            return 1

    if not args.force and verify_model_dir(dest_path):
        print(f"Model already present at {dest_path}.")
        print("Use --force to re-download and re-extract, or --clean to clean target.")
        print_cli_instructions(dest_path)
        return 0

    cache_dir = Path(args.cache_dir).resolve() if args.cache_dir else (Path(tempfile.gettempdir()) / "vosk_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    zip_dest = cache_dir / "vosk-model-small-ar-0.22.zip"

    # Step 1: Download
    if args.skip_download and zip_dest.is_file() and zip_dest.stat().st_size > 0:
        print(f"Using cached zip: {zip_dest}")
    else:
        try:
            download_model_zip(args.url, zip_dest)
        except Exception as e:
            print(f"\nError downloading model from {args.url}: {e}", file=sys.stderr)
            return 1

    # Step 2: Extract
    try:
        extract_model_archive(zip_dest, dest_path, clean_target=args.clean)
    except Exception as e:
        print(f"\nError extracting zip file: {e}", file=sys.stderr)
        return 1

    # Step 3: Instructions
    print_cli_instructions(dest_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
