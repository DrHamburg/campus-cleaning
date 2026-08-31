from config.database import query, execute
from services.task_service import is_task_in_supervisor_scope

VALID_STATUSES = ["Open", "In Progress", "Resolved"]


def list_locations_on_floor(floor_no):
    return query(
        "SELECT Location_ID, Block_Name, Room_No, Location_Type FROM CAMPUS_LOCATION WHERE Floor_No = %s AND Location_Status = 'Active' ORDER BY Block_Name, Room_No",
        (floor_no,)
    )


def get_supervisor_floor_for_staff(staff_id):
    row = query(
        """SELECT sup.Assigned_Floor FROM CLEANING_STAFF cs
           JOIN SUPERVISOR sup ON sup.Staff_ID = cs.Supervisor_ID
           WHERE cs.Staff_ID = %s""",
        (staff_id,), fetchone=True
    )
    return row["Assigned_Floor"] if row else None


def list_own_recent_tasks(staff_id):
    return query(
        "SELECT Task_ID, Location_ID, Task_Date FROM CLEANING_TASK WHERE Staff_ID = %s ORDER BY Task_Date DESC LIMIT 10",
        (staff_id,)
    )


def create_issue(staff_id, location_id, task_id, issue_type, description, priority, issue_date):
    task_id = task_id or None
    issue_id, _ = execute(
        """INSERT INTO CLEANING_ISSUE (Location_ID, Task_ID, Reported_By, Issue_Date, Issue_Type, Description, Priority, Issue_Status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, 'Open')""",
        (location_id, task_id, staff_id, issue_date, issue_type, description, priority)
    )
    return {"ok": True, "issue_id": issue_id}


def list_issues_for_staff(staff_id, status=None):
    conditions = ["ci.Reported_By = %s"]
    params = [staff_id]
    if status:
        conditions.append("ci.Issue_Status = %s")
        params.append(status)
    return query(
        f"""SELECT ci.Issue_ID, ci.Location_ID, DATE_FORMAT(ci.Issue_Date, '%Y-%m-%d') AS Issue_Date,
                   ci.Issue_Type, ci.Priority, ci.Issue_Status
            FROM CLEANING_ISSUE ci
            WHERE {' AND '.join(conditions)}
            ORDER BY ci.Issue_Date DESC, ci.Issue_ID DESC""",
        tuple(params)
    )


def list_issues_for_supervisor(supervisor_id, status=None, priority=None):
    row = query("SELECT Assigned_Floor FROM SUPERVISOR WHERE Staff_ID = %s", (supervisor_id,), fetchone=True)
    if not row:
        return []
    floor_no = row["Assigned_Floor"]

    conditions = ["cl.Floor_No = %s"]
    params = [floor_no]
    if status:
        conditions.append("ci.Issue_Status = %s")
        params.append(status)
    if priority:
        conditions.append("ci.Priority = %s")
        params.append(priority)

    return query(
        f"""SELECT ci.Issue_ID, ci.Location_ID, s.Name AS Reported_By_Name,
                   DATE_FORMAT(ci.Issue_Date, '%Y-%m-%d') AS Issue_Date,
                   ci.Issue_Type, ci.Priority, ci.Issue_Status, ci.Task_ID
            FROM CLEANING_ISSUE ci
            JOIN CAMPUS_LOCATION cl ON cl.Location_ID = ci.Location_ID
            JOIN STAFF s ON s.Staff_ID = ci.Reported_By
            WHERE {' AND '.join(conditions)}
            ORDER BY ci.Issue_Date DESC, ci.Issue_ID DESC""",
        tuple(params)
    )


def get_issue_by_id(issue_id):
    return query(
        """SELECT ci.Issue_ID, ci.Location_ID, cl.Block_Name, cl.Floor_No, ci.Task_ID, ci.Reported_By,
                  s.Name AS Reported_By_Name, DATE_FORMAT(ci.Issue_Date, '%Y-%m-%d') AS Issue_Date,
                  ci.Issue_Type, ci.Description, ci.Priority, ci.Issue_Status,
                  DATE_FORMAT(ci.Resolved_Date, '%Y-%m-%d') AS Resolved_Date, ci.Resolution_Remarks
           FROM CLEANING_ISSUE ci
           JOIN CAMPUS_LOCATION cl ON cl.Location_ID = ci.Location_ID
           JOIN STAFF s ON s.Staff_ID = ci.Reported_By
           WHERE ci.Issue_ID = %s""",
        (issue_id,), fetchone=True
    )


def is_issue_in_supervisor_scope(issue_id, supervisor_id):
    issue = get_issue_by_id(issue_id)
    if not issue:
        return False

    supervisor = query("SELECT Assigned_Floor FROM SUPERVISOR WHERE Staff_ID = %s", (supervisor_id,), fetchone=True)
    if not supervisor or issue["Floor_No"] != supervisor["Assigned_Floor"]:
        return False

    if issue["Task_ID"] is not None:
        if not is_task_in_supervisor_scope(issue["Task_ID"], supervisor_id):
            return False

    return True


def update_issue_status(issue_id, status):
    if status not in VALID_STATUSES:
        return {"ok": False, "reason": "invalid_status"}
    execute("UPDATE CLEANING_ISSUE SET Issue_Status = %s WHERE Issue_ID = %s", (status, issue_id))
    return {"ok": True}


def resolve_issue(issue_id, resolution_remarks, resolved_date):
    execute(
        "UPDATE CLEANING_ISSUE SET Issue_Status = 'Resolved', Resolved_Date = %s, Resolution_Remarks = %s WHERE Issue_ID = %s",
        (resolved_date, resolution_remarks, issue_id)
    )
    return {"ok": True}
