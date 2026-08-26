from flask import Blueprint, current_app, send_from_directory

bp_assets = Blueprint("assets", __name__)


@bp_assets.route("/assets/images/<path:relative_path>")
def serve_image(relative_path: str):
    return send_from_directory(current_app.config["IMAGES_ROOT"], relative_path)
