
from config.database import query


def staff_performance(supervisor_id):
    return query(
        """SELECT s.Name,
                  COUNT(ct.Task_ID) AS Total_Tasks,
                  SUM(CASE WHEN ct.Task_Status = 'Completed' THEN 1 ELSE 0 END) AS Completed_Tasks,
                  SUM(CASE WHEN ct.Task_Status = 'Pending' THEN 1 ELSE 0 END) AS Pending_Tasks,
                  ROUND(100.0 * SUM(CASE WHEN ct.Task_Status = 'Completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(ct.Task_ID), 0), 1) AS Completion_Rate
           FROM CLEANING_STAFF cs
           JOIN STAFF s ON s.Staff_ID = cs.Staff_ID
           LEFT JOIN CLEANING_TASK ct ON ct.Staff_ID = cs.Staff_ID
           WHERE cs.Supervisor_ID = %s
           GROUP BY cs.Staff_ID, s.Name
           ORDER BY s.Name""",
        (supervisor_id,)
    )


def attendance_summary(supervisor_id):
    return query(
        """SELECT s.Name,
                  SUM(CASE WHEN a.Attendance_Status = 'Present' THEN 1 ELSE 0 END) AS Present_Count,
                  SUM(CASE WHEN a.Attendance_Status = 'Late' THEN 1 ELSE 0 END) AS Late_Count,
                  SUM(CASE WHEN a.Attendance_Status = 'Absent' THEN 1 ELSE 0 END) AS Absent_Count,
                  COUNT(a.Attendance_ID) AS Total_Records
           FROM CLEANING_STAFF cs
           JOIN STAFF s ON s.Staff_ID = cs.Staff_ID
           LEFT JOIN ATTENDANCE a ON a.Staff_ID = cs.Staff_ID
           WHERE cs.Supervisor_ID = %s
           GROUP BY cs.Staff_ID, s.Name
           ORDER BY s.Name""",
        (supervisor_id,)
    )


def task_report_by_location(supervisor_id):
    floor = query("SELECT Assigned_Floor FROM SUPERVISOR WHERE Staff_ID = %s", (supervisor_id,), fetchone=True)
    if not floor:
        return []
    return query(
        """SELECT cl.Location_ID,
                  COUNT(ct.Task_ID) AS Total_Tasks,
                  SUM(CASE WHEN ct.Task_Status = 'Completed' THEN 1 ELSE 0 END) AS Completed,
                  SUM(CASE WHEN ct.Task_Status = 'Pending' THEN 1 ELSE 0 END) AS Pending,
                  SUM(CASE WHEN ct.Task_Status = 'In Progress' THEN 1 ELSE 0 END) AS In_Progress
           FROM CAMPUS_LOCATION cl
           LEFT JOIN CLEANING_TASK ct ON ct.Location_ID = cl.Location_ID
           WHERE cl.Floor_No = %s
           GROUP BY cl.Location_ID
           HAVING COUNT(ct.Task_ID) > 0
           ORDER BY Total_Tasks DESC""",
        (floor["Assigned_Floor"],)
    )


def issue_report(supervisor_id):
    floor = query("SELECT Assigned_Floor FROM SUPERVISOR WHERE Staff_ID = %s", (supervisor_id,), fetchone=True)
    if not floor:
        return []
    return query(
        """SELECT ci.Issue_Type, ci.Priority, ci.Issue_Status, COUNT(*) AS Count
           FROM CLEANING_ISSUE ci
           JOIN CAMPUS_LOCATION cl ON cl.Location_ID = ci.Location_ID
           WHERE cl.Floor_No = %s
           GROUP BY ci.Issue_Type, ci.Priority, ci.Issue_Status
           ORDER BY Count DESC""",
        (floor["Assigned_Floor"],)
    )


def material_report():
    return query(
        "SELECT Material_Name, Current_Stock, Reorder_Level, Material_Status FROM CLEANING_MATERIAL ORDER BY Material_Status DESC, Material_Name"
    )
