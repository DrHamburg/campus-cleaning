

import datetime
from flask import Blueprint, request, session, render_template
from middleware.decorators import require_role
from services import schedule_service, task_service

schedule_bp = Blueprint("schedule", __name__)


@schedule_bp.route("/supervisor/schedule", methods=["GET"])
@require_role("SUPERVISOR")
def supervisor_schedule():
    supervisor_id = session["staff_id"]
    date = request.args.get("date") or datetime.date.today().isoformat()
    block = request.args.get("block") or None
    shift_id = request.args.get("shift_id") or None

    rows, blocks = schedule_service.get_floor_schedule(
        supervisor_id, date, block=block, shift_id=int(shift_id) if shift_id else None
    )
    shifts = task_service.list_shifts()

    return render_template(
        "supervisor/schedule.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="schedule",
        rows=rows, blocks=blocks, shifts=shifts,
        filter_date=date, filter_block=block or "", filter_shift=shift_id or "",
    )
