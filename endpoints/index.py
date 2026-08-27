from flask import Blueprint, redirect, url_for

bp_index = Blueprint("index", __name__)


@bp_index.route("/", methods=["GET"])
def index():
    return redirect(url_for("tags.map_view"))
