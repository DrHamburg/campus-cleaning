import datetime
from config.database import query, execute

LATE_GRACE_MINUTES = 15


def _combine(date_obj, time_obj):
    if isinstance(time_obj, datetime.timedelta):
        total_seconds = int(time_obj.total_seconds())
        time_obj = (datetime.datetime.min + datetime.timedelta(seconds=total_seconds)).time()
    return datetime.datetime.combine(date_obj, time_obj)


def get_active_shifts():
    return query("SELECT Shift_ID, Shift_Name, Start_Time, End_Time FROM SHIFT WHERE Shift_Status = 'Active' ORDER BY Start_Time")


def get_today_records_for_staff(staff_id):
    today = datetime.date.today().isoformat()
    return query(
        """SELECT a.Attendance_ID, a.Shift_ID, sh.Shift_Name, a.Check_In_Time, a.Check_Out_Time, a.Attendance_Status
           FROM ATTENDANCE a
           JOIN SHIFT sh ON sh.Shift_ID = a.Shift_ID
           WHERE a.Staff_ID = %s AND a.Attendance_Date = %s
           ORDER BY a.Check_In_Time""",
        (staff_id, today)
    )


def check_in(staff_id, shift_id):
    today = datetime.date.today()
    now_time = datetime.datetime.now().time()

    existing = query(
        "SELECT Attendance_ID FROM ATTENDANCE WHERE Staff_ID = %s AND Shift_ID = %s AND Attendance_Date = %s",
        (staff_id, shift_id, today.isoformat()), fetchone=True
    )
    if existing:
        return {"ok": False, "reason": "already_checked_in"}

    shift = query("SELECT Start_Time FROM SHIFT WHERE Shift_ID = %s AND Shift_Status = 'Active'", (shift_id,), fetchone=True)
    if not shift:
        return {"ok": False, "reason": "invalid_shift"}

    shift_start = _combine(today, shift["Start_Time"])
    check_in_dt = _combine(today, now_time)
    minutes_late = (check_in_dt - shift_start).total_seconds() / 60
    status = "Late" if minutes_late > LATE_GRACE_MINUTES else "Present"

    attendance_id, _ = execute(
        """INSERT INTO ATTENDANCE (Staff_ID, Shift_ID, Attendance_Date, Check_In_Time, Attendance_Status)
           VALUES (%s, %s, %s, %s, %s)""",
        (staff_id, shift_id, today.isoformat(), now_time.strftime("%H:%M:%S"), status)
    )
    return {"ok": True, "attendance_id": attendance_id, "status": status}


def check_out(attendance_id, staff_id):
    record = query(
        "SELECT Staff_ID, Check_In_Time, Check_Out_Time FROM ATTENDANCE WHERE Attendance_ID = %s",
        (attendance_id,), fetchone=True
    )
    if not record:
        return {"ok": False, "reason": "not_found"}
    if int(record["Staff_ID"]) != int(staff_id):
        return {"ok": False, "reason": "not_your_record"}
    if not record["Check_In_Time"]:
        return {"ok": False, "reason": "not_checked_in"}
    if record["Check_Out_Time"]:
        return {"ok": False, "reason": "already_checked_out"}

    now_time = datetime.datetime.now().time().strftime("%H:%M:%S")
    execute("UPDATE ATTENDANCE SET Check_Out_Time = %s WHERE Attendance_ID = %s", (now_time, attendance_id))
    return {"ok": True}


def list_attendance_for_staff(staff_id, date=None, status=None):
    conditions = ["a.Staff_ID = %s"]
    params = [staff_id]
    if date:
        conditions.append("a.Attendance_Date = %s")
        params.append(date)
    if status:
        conditions.append("a.Attendance_Status = %s")
        params.append(status)

    sql = f"""
        SELECT a.Attendance_ID, sh.Shift_Name,
               DATE_FORMAT(a.Attendance_Date, '%Y-%m-%d') AS Attendance_Date,
               a.Check_In_Time, a.Check_Out_Time, a.Attendance_Status, a.Remarks
        FROM ATTENDANCE a
        JOIN SHIFT sh ON sh.Shift_ID = a.Shift_ID
        WHERE {' AND '.join(conditions)}
        ORDER BY a.Attendance_Date DESC, a.Check_In_Time DESC
    """
    return query(sql, tuple(params))


def list_attendance_for_supervisor(supervisor_id, date=None, status=None, staff_id=None):
    conditions = ["cs.Supervisor_ID = %s"]
    params = [supervisor_id]
    if date:
        conditions.append("a.Attendance_Date = %s")
        params.append(date)
    if status:
        conditions.append("a.Attendance_Status = %s")
        params.append(status)
    if staff_id:
        conditions.append("a.Staff_ID = %s")
        params.append(staff_id)

    sql = f"""
        SELECT a.Attendance_ID, a.Staff_ID, s.Name AS Staff_Name, sh.Shift_Name,
               DATE_FORMAT(a.Attendance_Date, '%Y-%m-%d') AS Attendance_Date,
               a.Check_In_Time, a.Check_Out_Time, a.Attendance_Status, a.Remarks
        FROM ATTENDANCE a
        JOIN CLEANING_STAFF cs ON cs.Staff_ID = a.Staff_ID
        JOIN STAFF s ON s.Staff_ID = a.Staff_ID
        JOIN SHIFT sh ON sh.Shift_ID = a.Shift_ID
        WHERE {' AND '.join(conditions)}
        ORDER BY a.Attendance_Date DESC, a.Check_In_Time DESC
    """
    return query(sql, tuple(params))
