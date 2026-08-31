import datetime
from flask import Blueprint, session, render_template
from middleware.decorators import require_role
from services import staff_service
from config.database import query

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/supervisor/dashboard", methods=["GET"])
@require_role("SUPERVISOR")
def supervisor_dashboard():
    supervisor_id = session["staff_id"]
    profile = staff_service.get_supervisor_profile(supervisor_id)
    today = datetime.date.today().isoformat()

    stats = query(
        """SELECT
             (SELECT COUNT(*) FROM CLEANING_STAFF cs JOIN STAFF s ON s.Staff_ID = cs.Staff_ID
              WHERE cs.Supervisor_ID = %s AND s.Status = 'Active') AS staff_count,
             (SELECT COUNT(*) FROM CLEANING_TASK ct JOIN CLEANING_STAFF cs ON cs.Staff_ID = ct.Staff_ID
              WHERE cs.Supervisor_ID = %s AND ct.Task_Date = %s) AS today_tasks,
             (SELECT COUNT(*) FROM CLEANING_TASK ct JOIN CLEANING_STAFF cs ON cs.Staff_ID = ct.Staff_ID
              WHERE cs.Supervisor_ID = %s AND ct.Task_Date = %s AND ct.Task_Status = 'Completed') AS completed_today,
             (SELECT COUNT(*) FROM CLEANING_TASK ct JOIN CLEANING_STAFF cs ON cs.Staff_ID = ct.Staff_ID
              WHERE cs.Supervisor_ID = %s AND ct.Task_Date = %s AND ct.Task_Status = 'Pending') AS pending_today,
             (SELECT COUNT(*) FROM CLEANING_ISSUE ci JOIN CAMPUS_LOCATION cl ON cl.Location_ID = ci.Location_ID
              WHERE cl.Floor_No = (SELECT Assigned_Floor FROM SUPERVISOR WHERE Staff_ID = %s) AND ci.Issue_Status != 'Resolved') AS open_issues,
             (SELECT COUNT(*) FROM CLEANING_MATERIAL WHERE Material_Status IN ('Low Stock', 'Out of Stock')) AS low_stock_materials
        """,
        (supervisor_id, supervisor_id, today, supervisor_id, today, supervisor_id, today, supervisor_id),
        fetchone=True
    )

    return render_template(
        "supervisor/dashboard.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="dashboard",
        profile=profile, stats=stats,
    )


@dashboard_bp.route("/staff/dashboard", methods=["GET"])
@require_role("CLEANING_STAFF")
def cleaning_dashboard():
    staff_id = session["staff_id"]
    profile = staff_service.get_staff_by_id(staff_id)
    today = datetime.date.today().isoformat()

    stats = query(
        """SELECT
             (SELECT COUNT(*) FROM CLEANING_TASK WHERE Staff_ID = %s AND Task_Date = %s) AS today_tasks,
             (SELECT COUNT(*) FROM CLEANING_TASK WHERE Staff_ID = %s AND Task_Date = %s AND Task_Status = 'Completed') AS completed_today,
             (SELECT COUNT(*) FROM CLEANING_TASK WHERE Staff_ID = %s AND Task_Date = %s AND Task_Status = 'Pending') AS pending_today,
             (SELECT COUNT(*) FROM CLEANING_ISSUE WHERE Reported_By = %s AND Issue_Status != 'Resolved') AS open_issues
        """,
        (staff_id, today, staff_id, today, staff_id, today, staff_id),
        fetchone=True
    )

    return render_template(
        "staff/dashboard.html",
        role="CLEANING_STAFF", user_name=session.get("user_name"), active_page="dashboard",
        profile=profile, stats=stats,
    )
