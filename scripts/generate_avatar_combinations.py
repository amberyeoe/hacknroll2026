from itertools import combinations
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
AVATAR_DIR = ROOT / "static" / "avatar"
OUTPUT_DIR = AVATAR_DIR / "combinations"

ITEM_ORDER = [
    "headband",
    "headphones",
    "wristband",
    "watch",
    "nikeshirt",
    "nikesinglet",
]

LAYER_ORDER = [
    "nikeshirt",
    "nikesinglet",
    "headband",
    "headphones",
    "wristband",
    "watch",
]

TOP_ITEMS = ["nikeshirt", "nikesinglet"]
ACCESSORY_ITEMS = ["headband", "headphones", "wristband", "watch"]

ITEMS = {
    "headband": {
        "source": "headband.png",
        "threshold": 55,
        "focus": (430, 50, 590, 155),
        "min_area": 20,
    },
    "headphones": {
        "source": "headphone.png",
        "threshold": 55,
        "focus": (410, 40, 620, 210),
        "min_area": 20,
    },
    "wristband": {
        "source": "wristband.png",
        "threshold": 55,
        "focus": (340, 450, 430, 570),
        "min_area": 20,
    },
    "watch": {
        "source": "watch.png",
        "threshold": 55,
        "focus": (610, 425, 685, 575),
        "min_area": 20,
    },
    "nikeshirt": {
        "source": "nikeshirt.png",
        "threshold": 55,
        "focus": (360, 210, 665, 420),
        "min_area": 400,
    },
    "nikesinglet": {
        "source": "nikesinglet.png",
        "threshold": 55,
        "focus": (360, 210, 640, 420),
        "min_area": 200,
    },
}


def intersects(first, second):
    ax1, ay1, ax2, ay2 = first
    bx1, by1, bx2, by2 = second
    return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


def changed_pixel_mask(base, image, threshold):
    diff = ImageChops.difference(base, image)
    width, height = diff.size
    diff_pixels = diff.load()
    mask = bytearray(width * height)

    for y in range(height):
        row = y * width
        for x in range(width):
            if max(diff_pixels[x, y]) > threshold:
                mask[row + x] = 1

    return mask, width, height


def selected_component_mask(base, image, config):
    mask, width, height = changed_pixel_mask(base, image, config["threshold"])
    seen = bytearray(width * height)
    selected = Image.new("L", (width, height), 0)
    selected_pixels = selected.load()

    for idx, value in enumerate(mask):
        if not value or seen[idx]:
            continue

        stack = [idx]
        seen[idx] = 1
        pixels = []
        min_x = width
        min_y = height
        max_x = 0
        max_y = 0

        while stack:
            current = stack.pop()
            pixels.append(current)
            x = current % width
            y = current // width
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

            for next_y in (y - 1, y, y + 1):
                if next_y < 0 or next_y >= height:
                    continue
                for next_x in (x - 1, x, x + 1):
                    if next_x < 0 or next_x >= width or (next_x == x and next_y == y):
                        continue
                    next_idx = next_y * width + next_x
                    if mask[next_idx] and not seen[next_idx]:
                        seen[next_idx] = 1
                        stack.append(next_idx)

        bbox = (min_x, min_y, max_x + 1, max_y + 1)
        if len(pixels) < config["min_area"] or not intersects(bbox, config["focus"]):
            continue

        for pixel_idx in pixels:
            selected_pixels[pixel_idx % width, pixel_idx // width] = 255

    return selected.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(1.2))


def combo_filename(keys):
    ordered = [key for key in ITEM_ORDER if key in keys]
    return "__".join(ordered) + ".png"


def valid_combinations():
    for top_item in [None, *TOP_ITEMS]:
        for count in range(len(ACCESSORY_ITEMS) + 1):
            for accessory_keys in combinations(ACCESSORY_ITEMS, count):
                keys = list(accessory_keys)
                if top_item:
                    keys.append(top_item)
                if keys:
                    yield [key for key in ITEM_ORDER if key in keys]


def main():
    base = Image.open(AVATAR_DIR / "default.jpg").convert("RGB")
    sources = {
        key: Image.open(AVATAR_DIR / config["source"]).convert("RGB")
        for key, config in ITEMS.items()
    }
    masks = {
        key: selected_component_mask(base, sources[key], config)
        for key, config in ITEMS.items()
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in OUTPUT_DIR.glob("*.png"):
        old_file.unlink()

    generated = 0
    for keys in valid_combinations():
        composite = base.convert("RGBA")

        for key in LAYER_ORDER:
            if key not in keys:
                continue
            layer = sources[key].convert("RGBA")
            layer.putalpha(masks[key])
            composite = Image.alpha_composite(composite, layer)

        composite.convert("RGB").save(OUTPUT_DIR / combo_filename(keys), optimize=True)
        generated += 1

    print(f"Generated {generated} avatar combinations in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
