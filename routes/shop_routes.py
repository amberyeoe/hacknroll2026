from flask import jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from db import get_db
from shop_items import (
    SHOP_ITEM_CATEGORIES,
    SHOP_ITEM_ORDER,
    SHOP_ITEMS,
    avatar_path_for_items,
    normalize_item_key,
    normalize_item_keys,
)


def register_shop_routes(app):
    @app.route("/shop")
    @login_required
    def shop():
        db = get_db()

        profile = db.execute(
            """
            SELECT credits, avatar_path
            FROM profiles
            WHERE user_id = ?
            """,
            (current_user.id,),
        ).fetchone()
        if not profile:
            return redirect(url_for("onboarding"))

        owned = db.execute(
            """
            SELECT item_path FROM owned_items
            WHERE user_id = ?
            """,
            (current_user.id,),
        ).fetchall()

        equipped = db.execute(
            """
            SELECT item_path FROM equipped_items
            WHERE user_id = ?
            """,
            (current_user.id,),
        ).fetchall()

        owned_items = normalize_item_keys(row["item_path"] for row in owned)
        equipped_items = normalize_item_keys(row["item_path"] for row in equipped)
        if not equipped_items:
            equipped_items = normalize_item_keys([profile["avatar_path"]])

        for item_key in equipped_items:
            if item_key not in owned_items:
                owned_items.append(item_key)

        return render_template(
            "shop.html",
            credits=profile["credits"],
            avatar_path=avatar_path_for_items(equipped_items),
            owned_items=owned_items,
            equipped_items=equipped_items,
            shop_items=SHOP_ITEMS,
            item_order=SHOP_ITEM_ORDER,
            item_categories=SHOP_ITEM_CATEGORIES,
        )

    @app.route("/shop/save", methods=["POST"])
    @login_required
    def save_shop():
        data = request.get_json(silent=True) or {}

        try:
            credits = int(data.get("credits", 0))
        except (TypeError, ValueError):
            return jsonify({"message": "Invalid credits"}), 400

        owned_items = normalize_item_keys(data.get("owned_items", []))
        equipped_items = normalize_item_keys(data.get("equipped_items", []))

        for item_key in equipped_items:
            if item_key not in owned_items:
                owned_items.append(item_key)

        avatar_path = avatar_path_for_items(equipped_items)
        db = get_db()

        db.execute(
            """
            UPDATE profiles
            SET credits = ?, avatar_path = ?
            WHERE user_id = ?
            """,
            (credits, avatar_path, current_user.id),
        )

        db.execute("DELETE FROM owned_items WHERE user_id = ?", (current_user.id,))
        for item in owned_items:
            db.execute(
                """
                INSERT INTO owned_items (user_id, item_path)
                VALUES (?, ?)
                """,
                (current_user.id, item),
            )

        db.execute("DELETE FROM equipped_items WHERE user_id = ?", (current_user.id,))
        for item in equipped_items:
            db.execute(
                """
                INSERT INTO equipped_items (user_id, item_path)
                VALUES (?, ?)
                """,
                (current_user.id, item),
            )

        db.commit()
        return jsonify({"avatar_path": avatar_path}), 200

    @app.route("/purchase_items", methods=["POST"])
    @login_required
    def purchase_items():
        data = request.get_json(silent=True) or {}
        avatar_path = data.get("avatar_path")
        try:
            price = int(data.get("price", 0))
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Invalid price"}), 400

        item_key = normalize_item_key(avatar_path)
        if not item_key:
            return jsonify({"success": False, "message": "Invalid item"}), 400

        db = get_db()
        row = db.execute(
            "SELECT credits FROM profiles WHERE user_id = ?",
            (current_user.id,),
        ).fetchone()

        if not row or row["credits"] < price:
            return jsonify({"success": False, "message": "Insufficient Credits"}), 400

        new_credits = row["credits"] - price
        db.execute(
            "UPDATE profiles SET credits = ? WHERE user_id = ?",
            (new_credits, current_user.id),
        )

        equipped = db.execute(
            """
            SELECT item_path FROM equipped_items
            WHERE user_id = ?
            """,
            (current_user.id,),
        ).fetchall()
        equipped_items = normalize_item_keys(
            [row["item_path"] for row in equipped] + [item_key]
        )
        avatar_path = avatar_path_for_items(equipped_items)

        db.execute(
            """
            INSERT OR IGNORE INTO owned_items (user_id, item_path)
            VALUES (?, ?)
            """,
            (current_user.id, item_key),
        )

        db.execute("DELETE FROM equipped_items WHERE user_id = ?", (current_user.id,))
        for equipped_item in equipped_items:
            db.execute(
                """
                INSERT INTO equipped_items (user_id, item_path)
                VALUES (?, ?)
                """,
                (current_user.id, equipped_item),
            )

        db.execute(
            "UPDATE profiles SET avatar_path = ? WHERE user_id = ?",
            (avatar_path, current_user.id),
        )

        db.commit()

        return jsonify(
            {"success": True, "credits": new_credits, "avatar_path": avatar_path}
        )
