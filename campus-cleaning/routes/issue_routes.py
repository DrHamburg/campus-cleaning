import datetime
from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from middleware.decorators import require_role
from services import issue_service

issues_bp = Blueprint("issues", __name__)


@issues_bp.route("/staff/issues", methods=["GET"])
@require_role("CLEANING_STAFF")
def staff_issue_list():
    status = request.args.get("status") or None
    issues = issue_service.list_issues_for_staff(session["staff_id"], status=status)
    return render_template(
        "staff/issues_list.html",
        role="CLEANING_STAFF", user_name=session.get("user_name"), active_page="issues",
        issues=issues, filter_status=status or "",
    )


@issues_bp.route("/staff/issues/new", methods=["GET"])
@require_role("CLEANING_STAFF")
def staff_issue_new():
    staff_id = session["staff_id"]
    floor_no = issue_service.get_supervisor_floor_for_staff(staff_id)
    locations = issue_service.list_locations_on_floor(floor_no) if floor_no else []
    tasks = issue_service.list_own_recent_tasks(staff_id)
    return render_template(
        "staff/issue_form.html",
        role="CLEANING_STAFF", user_name=session.get("user_name"), active_page="issues",
        locations=locations, tasks=tasks,
    )


@issues_bp.route("/staff/issues/new", methods=["POST"])
@require_role("CLEANING_STAFF")
def staff_issue_create():
    location_id = request.form.get("location_id")
    task_id = request.form.get("task_id") or None
    issue_type = request.form.get("issue_type")
    description = request.form.get("description")
    priority = request.form.get("priority")

    if not all([location_id, issue_type, priority]):
        flash("Location, issue type, and priority are required.", "error")
        return redirect(url_for("issues.staff_issue_new"))

    result = issue_service.create_issue(
        session["staff_id"], location_id, int(task_id) if task_id else None,
        issue_type, description, priority, datetime.date.today().isoformat()
    )
    flash("Issue reported successfully.", "success")
    return redirect(url_for("issues.staff_issue_list"))


@issues_bp.route("/staff/issues/<int:issue_id>", methods=["GET"])
@require_role("CLEANING_STAFF")
def staff_issue_detail(issue_id):
    issue = issue_service.get_issue_by_id(issue_id)
    if not issue or int(issue["Reported_By"]) != int(session["staff_id"]):
        flash("Forbidden.", "error")
        return redirect(url_for("issues.staff_issue_list"))
    return render_template(
        "staff/issue_detail.html",
        role="CLEANING_STAFF", user_name=session.get("user_name"), active_page="issues",
        issue=issue,
    )



@issues_bp.route("/supervisor/issues", methods=["GET"])
@require_role("SUPERVISOR")
def supervisor_issue_list():
    status = request.args.get("status") or None
    priority = request.args.get("priority") or None
    issues = issue_service.list_issues_for_supervisor(session["staff_id"], status=status, priority=priority)
    return render_template(
        "supervisor/issues_list.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="issues",
        issues=issues, filter_status=status or "", filter_priority=priority or "",
    )


@issues_bp.route("/supervisor/issues/<int:issue_id>", methods=["GET"])
@require_role("SUPERVISOR")
def supervisor_issue_detail(issue_id):
    supervisor_id = session["staff_id"]
    if not issue_service.is_issue_in_supervisor_scope(issue_id, supervisor_id):
        flash("Forbidden: this issue is outside your assigned floor.", "error")
        return redirect(url_for("issues.supervisor_issue_list"))

    issue = issue_service.get_issue_by_id(issue_id)
    return render_template(
        "supervisor/issue_detail.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="issues",
        issue=issue,
    )


@issues_bp.route("/supervisor/issues/<int:issue_id>/status", methods=["POST"])
@require_role("SUPERVISOR")
def supervisor_issue_status(issue_id):
    supervisor_id = session["staff_id"]
    if not issue_service.is_issue_in_supervisor_scope(issue_id, supervisor_id):
        flash("Forbidden: this issue is outside your assigned floor.", "error")
        return redirect(url_for("issues.supervisor_issue_list"))

    status = request.form.get("status")
    result = issue_service.update_issue_status(issue_id, status)
    if not result["ok"]:
        flash("Invalid status.", "error")
    else:
        flash("Issue status updated.", "success")
    return redirect(url_for("issues.supervisor_issue_detail", issue_id=issue_id))


@issues_bp.route("/supervisor/issues/<int:issue_id>/resolve", methods=["POST"])
@require_role("SUPERVISOR")
def supervisor_issue_resolve(issue_id):
    supervisor_id = session["staff_id"]
    if not issue_service.is_issue_in_supervisor_scope(issue_id, supervisor_id):
        flash("Forbidden: this issue is outside your assigned floor.", "error")
        return redirect(url_for("issues.supervisor_issue_list"))

    remarks = request.form.get("resolution_remarks")
    if not remarks:
        flash("Resolution remarks are required.", "error")
        return redirect(url_for("issues.supervisor_issue_detail", issue_id=issue_id))

    issue_service.resolve_issue(issue_id, remarks, datetime.date.today().isoformat())
    flash("Issue resolved.", "success")
    return redirect(url_for("issues.supervisor_issue_detail", issue_id=issue_id))
