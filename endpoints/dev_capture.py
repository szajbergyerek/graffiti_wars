import os
from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template, request

bp_dev_capture = Blueprint("dev_capture", __name__)


@bp_dev_capture.route("/dev/capture")
def dev_capture_page():
    return render_template("dev_capture.html")


@bp_dev_capture.route("/dev/capture/upload", methods=["POST"])
def dev_capture_upload():
    photo = request.files.get("photo")
    lat = request.form.get("lat", type=float)
    lon = request.form.get("lon", type=float)
    captured_at_raw = request.form.get("captured_at")

    if photo is None or photo.filename == "" or lat is None or lon is None or not captured_at_raw:
        return jsonify({"error": "missing_fields"}), 400

    try:
        captured_at = datetime.fromisoformat(captured_at_raw.replace("Z", "+00:00"))
    except ValueError:
        captured_at = datetime.utcnow()

    # No verification of any kind here by design - this is a raw dev tool for
    # quickly collecting geotagged test photos, not a game action.
    timestamp_part = captured_at.strftime("%Y%m%d_%H%M%S") + f"_{captured_at.microsecond // 1000:03d}"
    filename = f"{lat:.6f}_{lon:.6f}_{timestamp_part}.jpg"

    target_dir = os.path.join(current_app.config["IMAGES_ROOT"], "dev_captures")
    os.makedirs(target_dir, exist_ok=True)
    photo.save(os.path.join(target_dir, filename))

    return jsonify({"ok": True, "filename": filename})
