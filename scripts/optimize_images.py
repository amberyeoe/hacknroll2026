from pathlib import Path
import tempfile

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
JPEG_QUALITY = 88


def optimize_jpeg(path):
    original_size = path.stat().st_size
    with tempfile.NamedTemporaryFile(delete=False, suffix=path.suffix) as temp:
        temp_path = Path(temp.name)

    try:
        with Image.open(path) as image:
            image.convert("RGB").save(
                temp_path,
                quality=JPEG_QUALITY,
                optimize=True,
                progressive=True,
            )
        optimized_size = temp_path.stat().st_size
        if optimized_size < original_size:
            temp_path.replace(path)
            return original_size, optimized_size
        temp_path.unlink(missing_ok=True)
        return original_size, original_size
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def optimize_png(path):
    original_size = path.stat().st_size
    with tempfile.NamedTemporaryFile(delete=False, suffix=path.suffix) as temp:
        temp_path = Path(temp.name)

    try:
        with Image.open(path) as image:
            image.save(temp_path, optimize=True, compress_level=9)
        optimized_size = temp_path.stat().st_size
        if optimized_size < original_size:
            temp_path.replace(path)
            return original_size, optimized_size
        temp_path.unlink(missing_ok=True)
        return original_size, original_size
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def main():
    total_before = 0
    total_after = 0
    optimized = 0

    for path in sorted(STATIC_DIR.rglob("*")):
        if not path.is_file():
            continue

        suffix = path.suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png"}:
            continue

        if suffix in {".jpg", ".jpeg"}:
            before, after = optimize_jpeg(path)
        else:
            before, after = optimize_png(path)

        optimized += 1
        total_before += before
        total_after += after
        print(f"{path.relative_to(ROOT)}: {before} -> {after}")

    print(
        f"Optimized {optimized} images: {total_before} -> {total_after} bytes "
        f"({total_before - total_after} saved)"
    )


if __name__ == "__main__":
    main()
