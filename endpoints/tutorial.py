from flask import Blueprint, abort, render_template

bp_tutorial = Blueprint("tutorial", __name__)

TOTAL_STEPS = 4


@bp_tutorial.route("/tutorial/<int:step>")
def tutorial_step(step: int):
    if step < 1 or step > TOTAL_STEPS:
        abort(404)

    return render_template(
        "tutorial_step.html",
        step=step,
        total_steps=TOTAL_STEPS,
        is_last_step=step == TOTAL_STEPS,
    )
