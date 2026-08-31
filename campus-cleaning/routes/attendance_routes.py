from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from middleware.decorators import require_role
from services import attendance_service

attendance_bp = Blueprint("attendance", __name__)

@attendance_bp.route("/staff/attendance", methods=["GET"])
@require_role("CLEANING_STAFF")
def staff_attendance():
    staff_id = session["staff_id"]
    date = request.args.get("date") or None
    status = request.args.get("status") or None

    shifts = attendance_service.get_active_shifts()
    today_records = attendance_service.get_today_records_for_staff(staff_id)
    history = attendance_service.list_attendance_for_staff(staff_id, date=date, status=status)

    return render_template(
        "staff/attendance.html",
        role="CLEANING_STAFF", user_name=session.get("user_name"), active_page="attendance",
        shifts=shifts, today_records=today_records, history=history,
        filter_date=date or "", filter_status=status or "",
    )


@attendance_bp.route("/staff/attendance/check-in", methods=["POST"])
@require_role("CLEANING_STAFF")
def staff_check_in():
    staff_id = session["staff_id"]
    shift_id = request.form.get("shift_id")

    if not shift_id:
        flash("Please select a shift.", "error")
        return redirect(url_for("attendance.staff_attendance"))

    result = attendance_service.check_in(staff_id, int(shift_id))

    if not result["ok"]:
        messages = {
            "already_checked_in": "You've already checked in for this shift today.",
            "invalid_shift": "That shift is not available.",
        }
        flash(messages.get(result["reason"], "Could not check in."), "error")
    else:
        flash(f"Checked in successfully — marked as {result['status']}.", "success")

    return redirect(url_for("attendance.staff_attendance"))


@attendance_bp.route("/staff/attendance/<int:attendance_id>/check-out", methods=["POST"])
@require_role("CLEANING_STAFF")
def staff_check_out(attendance_id):
    staff_id = session["staff_id"]
    result = attendance_service.check_out(attendance_id, staff_id)

    if not result["ok"]:
        messages = {
            "not_found": "Attendance record not found.",
            "not_your_record": "Forbidden: this record is not yours.",
            "not_checked_in": "You must check in before checking out.",
            "already_checked_out": "You've already checked out for this shift.",
        }
        flash(messages.get(result["reason"], "Could not check out."), "error")
    else:
        flash("Checked out successfully.", "success")

    return redirect(url_for("attendance.staff_attendance"))



@attendance_bp.route("/supervisor/attendance", methods=["GET"])
@require_role("SUPERVISOR")
def supervisor_attendance():
    supervisor_id = session["staff_id"]
    date = request.args.get("date") or None
    status = request.args.get("status") or None

    records = attendance_service.list_attendance_for_supervisor(supervisor_id, date=date, status=status)

    return render_template(
        "supervisor/attendance.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="attendance",
        records=records, filter_date=date or "", filter_status=status or "",
    )
