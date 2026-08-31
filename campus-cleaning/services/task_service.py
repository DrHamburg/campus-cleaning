from config.database import query, execute

VALID_STATUSES = ["Pending", "In Progress", "Completed", "Cancelled"]
STAFF_ALLOWED_STATUSES = ["In Progress", "Completed"]



def can_supervisor_assign_task(supervisor_id, staff_id, location_id):
    staff = query("SELECT Supervisor_ID FROM CLEANING_STAFF WHERE Staff_ID = %s", (staff_id,), fetchone=True)
    location = query("SELECT Floor_No FROM CAMPUS_LOCATION WHERE Location_ID = %s", (location_id,), fetchone=True)
    supervisor = query("SELECT Assigned_Floor FROM SUPERVISOR WHERE Staff_ID = %s", (supervisor_id,), fetchone=True)

    if not staff or not location or not supervisor:
        return False

    return (
        int(staff["Supervisor_ID"]) == int(supervisor_id)
        and int(location["Floor_No"]) == int(supervisor["Assigned_Floor"])
    )


def is_task_in_supervisor_scope(task_id, supervisor_id):
    task = query("SELECT Staff_ID, Location_ID FROM CLEANING_TASK WHERE Task_ID = %s", (task_id,), fetchone=True)
    if not task:
        return False
    return can_supervisor_assign_task(supervisor_id, task["Staff_ID"], task["Location_ID"])


def create_task(supervisor_id, staff_id, location_id, shift_id, task_date, remarks):
    if not can_supervisor_assign_task(supervisor_id, staff_id, location_id):
        return {"ok": False, "reason": "out_of_scope"}

    task_id, _ = execute(
        """INSERT INTO CLEANING_TASK (Staff_ID, Location_ID, Shift_ID, Assigned_By, Task_Date, Task_Status, Remarks)
           VALUES (%s, %s, %s, %s, %s, 'Pending', %s)""",
        (staff_id, location_id, shift_id, supervisor_id, task_date, remarks or None)
    )
    return {"ok": True, "task_id": task_id}


def list_tasks_for_supervisor(supervisor_id, date=None, status=None, staff_id=None, location_id=None):
    conditions = ["cs.Supervisor_ID = %s"]
    params = [supervisor_id]

    if date:
        conditions.append("ct.Task_Date = %s")
        params.append(date)
    if status:
        conditions.append("ct.Task_Status = %s")
        params.append(status)
    if staff_id:
        conditions.append("ct.Staff_ID = %s")
        params.append(staff_id)
    if location_id:
        conditions.append("ct.Location_ID = %s")
        params.append(location_id)

    sql = f"""
        SELECT ct.Task_ID, ct.Staff_ID, s.Name AS Staff_Name, ct.Location_ID, ct.Shift_ID, sh.Shift_Name,
               ct.Assigned_By, DATE_FORMAT(ct.Task_Date, '%Y-%m-%d') AS Task_Date, ct.Task_Status,
               ct.Completion_Time, ct.Remarks
        FROM CLEANING_TASK ct
        JOIN CLEANING_STAFF cs ON cs.Staff_ID = ct.Staff_ID
        JOIN STAFF s ON s.Staff_ID = ct.Staff_ID
        JOIN SHIFT sh ON sh.Shift_ID = ct.Shift_ID
        WHERE {' AND '.join(conditions)}
        ORDER BY ct.Task_Date DESC, ct.Task_ID DESC
    """
    return query(sql, tuple(params))


def list_tasks_for_staff(staff_id, date=None, status=None):
    conditions = ["ct.Staff_ID = %s"]
    params = [staff_id]

    if date:
        conditions.append("ct.Task_Date = %s")
        params.append(date)
    if status:
        conditions.append("ct.Task_Status = %s")
        params.append(status)

    sql = f"""
        SELECT ct.Task_ID, ct.Location_ID, ct.Shift_ID, sh.Shift_Name, ct.Assigned_By,
               DATE_FORMAT(ct.Task_Date, '%Y-%m-%d') AS Task_Date, ct.Task_Status,
               ct.Completion_Time, ct.Remarks
        FROM CLEANING_TASK ct
        JOIN SHIFT sh ON sh.Shift_ID = ct.Shift_ID
        WHERE {' AND '.join(conditions)}
        ORDER BY ct.Task_Date DESC, ct.Task_ID DESC
    """
    return query(sql, tuple(params))


def get_task_by_id(task_id):
    return query(
        """SELECT ct.Task_ID, ct.Staff_ID, s.Name AS Staff_Name, ct.Location_ID,
                  cl.Block_Name, cl.Floor_No, cl.Room_No,
                  ct.Shift_ID, sh.Shift_Name, ct.Assigned_By,
                  DATE_FORMAT(ct.Task_Date, '%Y-%m-%d') AS Task_Date,
                  ct.Task_Status, ct.Completion_Time, ct.Remarks
           FROM CLEANING_TASK ct
           JOIN STAFF s ON s.Staff_ID = ct.Staff_ID
           JOIN CAMPUS_LOCATION cl ON cl.Location_ID = ct.Location_ID
           JOIN SHIFT sh ON sh.Shift_ID = ct.Shift_ID
           WHERE ct.Task_ID = %s""",
        (task_id,), fetchone=True
    )



def update_task_by_supervisor(task_id, supervisor_id, updates):
    if not is_task_in_supervisor_scope(task_id, supervisor_id):
        return {"ok": False, "reason": "out_of_scope"}

    existing = get_task_by_id(task_id)
    if not existing:
        return {"ok": False, "reason": "not_found"}

    next_staff_id = updates.get("staffId", existing["Staff_ID"])
    next_location_id = updates.get("locationId", existing["Location_ID"])

    if "staffId" in updates or "locationId" in updates:
        if not can_supervisor_assign_task(supervisor_id, next_staff_id, next_location_id):
            return {"ok": False, "reason": "out_of_scope"}

    if "status" in updates and updates["status"] not in VALID_STATUSES:
        return {"ok": False, "reason": "invalid_status"}

    fields = []
    params = []
    if "staffId" in updates:
        fields.append("Staff_ID = %s"); params.append(updates["staffId"])
    if "locationId" in updates:
        fields.append("Location_ID = %s"); params.append(updates["locationId"])
    if "shiftId" in updates:
        fields.append("Shift_ID = %s"); params.append(updates["shiftId"])
    if "taskDate" in updates:
        fields.append("Task_Date = %s"); params.append(updates["taskDate"])
    if "status" in updates:
        fields.append("Task_Status = %s"); params.append(updates["status"])
    if "remarks" in updates:
        fields.append("Remarks = %s"); params.append(updates["remarks"])
    if updates.get("status") == "Completed":
        fields.append("Completion_Time = CURTIME()")

    if not fields:
        return {"ok": False, "reason": "no_changes"}

    params.append(task_id)
    execute(f"UPDATE CLEANING_TASK SET {', '.join(fields)} WHERE Task_ID = %s", tuple(params))
    return {"ok": True}


def cancel_task_by_supervisor(task_id, supervisor_id):
    if not is_task_in_supervisor_scope(task_id, supervisor_id):
        return {"ok": False, "reason": "out_of_scope"}

    existing = get_task_by_id(task_id)
    if not existing:
        return {"ok": False, "reason": "not_found"}
    if existing["Task_Status"] == "Completed":
        return {"ok": False, "reason": "already_completed"}

    execute("UPDATE CLEANING_TASK SET Task_Status = 'Cancelled' WHERE Task_ID = %s", (task_id,))
    return {"ok": True}


def update_task_progress_by_staff(task_id, staff_id, status=None, remarks=None):
    task = query("SELECT Staff_ID, Task_Status FROM CLEANING_TASK WHERE Task_ID = %s", (task_id,), fetchone=True)

    if not task:
        return {"ok": False, "reason": "not_found"}
    if int(task["Staff_ID"]) != int(staff_id):
        return {"ok": False, "reason": "not_your_task"}
    if status is not None and status not in STAFF_ALLOWED_STATUSES:
        return {"ok": False, "reason": "invalid_status_for_staff"}

    fields = []
    params = []
    if status is not None:
        fields.append("Task_Status = %s"); params.append(status)
        if status == "Completed":
            fields.append("Completion_Time = CURTIME()")
    if remarks is not None:
        fields.append("Remarks = %s"); params.append(remarks)

    if not fields:
        return {"ok": False, "reason": "no_changes"}

    params.append(task_id)
    execute(f"UPDATE CLEANING_TASK SET {', '.join(fields)} WHERE Task_ID = %s", tuple(params))
    return {"ok": True}


def list_blocks_for_supervisor(supervisor_id):
    rows = query(
        """SELECT DISTINCT cs.Assigned_Block AS block
           FROM CLEANING_STAFF cs
           JOIN STAFF s ON s.Staff_ID = cs.Staff_ID
           WHERE cs.Supervisor_ID = %s AND s.Status = 'Active'
           ORDER BY cs.Assigned_Block""",
        (supervisor_id,)
    )
    return [r["block"] for r in rows]


def list_assignable_staff_for_block(supervisor_id, block):
    return query(
        """SELECT s.Staff_ID, s.Name
           FROM CLEANING_STAFF cs
           JOIN STAFF s ON s.Staff_ID = cs.Staff_ID
           WHERE cs.Supervisor_ID = %s AND cs.Assigned_Block = %s AND s.Status = 'Active'
           ORDER BY s.Name""",
        (supervisor_id, block)
    )


def list_assignable_locations_for_block(supervisor_id, block):
    supervisor = query("SELECT Assigned_Floor FROM SUPERVISOR WHERE Staff_ID = %s", (supervisor_id,), fetchone=True)
    if not supervisor:
        return []
    return query(
        """SELECT Location_ID, Block_Name, Floor_No, Room_No, Location_Type
           FROM CAMPUS_LOCATION
           WHERE Floor_No = %s AND Block_Name = %s AND Location_Status = 'Active'
           ORDER BY Location_Type, Room_No""",
        (supervisor["Assigned_Floor"], block)
    )


def list_shifts():
    return query("SELECT Shift_ID, Shift_Name, Start_Time, End_Time FROM SHIFT WHERE Shift_Status = 'Active' ORDER BY Start_Time")
