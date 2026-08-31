

from flask import Blueprint, session, render_template
from middleware.decorators import require_role
from services import report_service

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/supervisor/reports", methods=["GET"])
@require_role("SUPERVISOR")
def supervisor_reports():
    supervisor_id = session["staff_id"]
    return render_template(
        "supervisor/reports.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="reports",
        staff_perf=report_service.staff_performance(supervisor_id),
        attendance=report_service.attendance_summary(supervisor_id),
        task_by_location=report_service.task_report_by_location(supervisor_id),
        issues=report_service.issue_report(supervisor_id),
        materials=report_service.material_report(),
    )
