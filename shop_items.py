from itertools import combinations


SHOP_ITEMS = [
    {
        "key": "headband",
        "name": "Headband",
        "desc": "Keeps sweat off",
        "price": 50,
        "category": "accessory",
        "preview_image": "images/shop/items/headband.png",
    },
    {
        "key": "headphones",
        "name": "Headphones",
        "desc": "Workout soundtrack",
        "price": 180,
        "category": "accessory",
        "preview_image": "images/shop/items/headphones.png",
    },
    {
        "key": "wristband",
        "name": "Wristband",
        "desc": "Grip & comfort",
        "price": 60,
        "category": "accessory",
        "preview_image": "images/shop/items/wristband.png",
    },
    {
        "key": "watch",
        "name": "Sports Watch",
        "desc": "Track your runs",
        "price": 220,
        "category": "accessory",
        "preview_image": "images/shop/items/watch.png",
    },
    {
        "key": "nikeshirt",
        "name": "Nike T-Shirt",
        "desc": "Classic training fit",
        "price": 140,
        "category": "top",
        "preview_image": "images/shop/items/nikeshirt.png",
    },
    {
        "key": "nikesinglet",
        "name": "Nike Singlet",
        "desc": "Light & breathable",
        "price": 130,
        "category": "top",
        "preview_image": "images/shop/items/nikesinglet.png",
    },
]

SHOP_ITEM_ORDER = [item["key"] for item in SHOP_ITEMS]
SHOP_ITEM_BY_KEY = {item["key"]: item for item in SHOP_ITEMS}
SHOP_ITEM_CATEGORIES = {item["key"]: item["category"] for item in SHOP_ITEMS}
TOP_ITEM_KEYS = {
    item["key"] for item in SHOP_ITEMS if item["category"] == "top"
}
ACCESSORY_ITEM_KEYS = [
    item["key"] for item in SHOP_ITEMS if item["category"] != "top"
]
ITEM_KEY_ALIASES = {
    "headband": "headband",
    "headphones": "headphones",
    "headphone": "headphones",
    "wristband": "wristband",
    "watch": "watch",
    "nikeshirt": "nikeshirt",
    "nikesinglet": "nikesinglet",
}


def item_keys_from_value(value):
    if not value:
        return []

    raw_value = str(value).replace("\\", "/").lower()
    if raw_value in SHOP_ITEM_BY_KEY:
        return [raw_value]

    filename = raw_value.rsplit("/", 1)[-1]
    stem = filename.rsplit(".", 1)[0]
    if "__" in stem:
        return [
            ITEM_KEY_ALIASES[item_key]
            for item_key in stem.split("__")
            if item_key in ITEM_KEY_ALIASES
        ]

    item_key = ITEM_KEY_ALIASES.get(stem)
    return [item_key] if item_key else []


def normalize_item_key(value):
    keys = item_keys_from_value(value)
    return keys[0] if keys else None


def normalize_item_keys(values):
    normalized = []
    seen = set()
    selected_top = None

    for value in values or []:
        for key in item_keys_from_value(value):
            if not key:
                continue

            if key in TOP_ITEM_KEYS:
                if selected_top and selected_top in seen:
                    normalized = [
                        item_key for item_key in normalized if item_key != selected_top
                    ]
                    seen.remove(selected_top)
                selected_top = key

            if key not in seen:
                normalized.append(key)
                seen.add(key)

    return [key for key in SHOP_ITEM_ORDER if key in seen]


def avatar_filename_for_items(item_keys):
    normalized = normalize_item_keys(item_keys)
    if not normalized:
        return "avatar/default.jpg"
    return "avatar/combinations/" + "__".join(normalized) + ".png"


def avatar_path_for_items(item_keys):
    return "/static/" + avatar_filename_for_items(item_keys)


def valid_item_combinations():
    for top_item in [None, *[key for key in SHOP_ITEM_ORDER if key in TOP_ITEM_KEYS]]:
        for count in range(len(ACCESSORY_ITEM_KEYS) + 1):
            for accessory_keys in combinations(ACCESSORY_ITEM_KEYS, count):
                keys = list(accessory_keys)
                if top_item:
                    keys.append(top_item)
                if keys:
                    yield [key for key in SHOP_ITEM_ORDER if key in keys]


def expected_avatar_filenames():
    return [avatar_filename_for_items(keys) for keys in valid_item_combinations()]
