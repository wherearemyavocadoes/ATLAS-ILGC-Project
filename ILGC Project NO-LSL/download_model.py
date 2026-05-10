"""
download_model.py — Downloads the MobileNet-SSD Caffe model files.

Run this ONCE before running main.py.
Downloads ~23 MB of model weights + network architecture
into the models/ directory.

Usage (in Thonny or terminal):
    python3 download_model.py

Run target: Raspberry Pi / Thonny
"""

import os
import sys
import urllib.request

# ──────────────────────────────────────────────
#  Verified working URLs (chuanqi305/MobileNet-SSD)
# ──────────────────────────────────────────────
PROTOTXT_URL = (
    "https://raw.githubusercontent.com/chuanqi305/"
    "MobileNet-SSD/master/deploy.prototxt"
)

# jsDelivr CDN — reliable for large GitHub files
CAFFEMODEL_URL = (
    "https://cdn.jsdelivr.net/gh/chuanqi305/"
    "MobileNet-SSD@master/mobilenet_iter_73000.caffemodel"
)

MODEL_DIR = "models"

# Output filenames (what our detector.py expects)
PROTOTXT_FILE = "deploy.prototxt"
CAFFEMODEL_FILE = "mobilenet_iter_73000.caffemodel"


def download_file(url, dest_path):
    """Download a file with progress feedback."""
    if os.path.exists(dest_path):
        size = os.path.getsize(dest_path)
        if size > 1000:
            print(f"  [SKIP] {os.path.basename(dest_path)} "
                  f"already exists ({size:,} bytes)")
            return True

    print(f"  Downloading: {os.path.basename(dest_path)}")
    print(f"  From: {url}")

    try:
        def progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(100, downloaded * 100 // total_size)
                bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
                sys.stdout.write(
                    f"\r  [{bar}] {pct}%  "
                    f"({downloaded:,}/{total_size:,} bytes)"
                )
                sys.stdout.flush()

        urllib.request.urlretrieve(url, dest_path, reporthook=progress)
        print()

        size = os.path.getsize(dest_path)
        print(f"  Saved: {dest_path} ({size:,} bytes)")
        return True

    except Exception as e:
        print(f"\n  [ERROR] Download failed: {e}")
        print(f"  Try manually: wget {url}")
        return False


def main():
    print("=" * 50)
    print("  ILGC Navigation — Model Downloader")
    print("=" * 50)
    print()

    os.makedirs(MODEL_DIR, exist_ok=True)
    print(f"Model directory: {os.path.abspath(MODEL_DIR)}")
    print()

    print("[1/2] Network architecture (.prototxt)")
    ok1 = download_file(
        PROTOTXT_URL,
        os.path.join(MODEL_DIR, PROTOTXT_FILE)
    )
    print()

    print("[2/2] Model weights (.caffemodel) — ~23 MB")
    ok2 = download_file(
        CAFFEMODEL_URL,
        os.path.join(MODEL_DIR, CAFFEMODEL_FILE)
    )
    print()

    print("=" * 50)
    if ok1 and ok2:
        print("  All model files ready!")
        print("  You can now run: python3 main.py")
    else:
        print("  Some downloads failed.")
        print("  Fallback: clone the repo directly:")
        print("  git clone https://github.com/"
              "chuanqi305/MobileNet-SSD")
        print("  Then copy deploy.prototxt and")
        print("  mobilenet_iter_73000.caffemodel "
              "into models/")
    print("=" * 50)


if __name__ == "__main__":
    main()
