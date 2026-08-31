from config.database import query


def list_blocks_on_floor(floor_no):
    rows = query(
        "SELECT DISTINCT Block_Name FROM CAMPUS_LOCATION WHERE Floor_No = %s AND Location_Status = 'Active' ORDER BY Block_Name",
        (floor_no,)
    )
    return [r["Block_Name"] for r in rows]


def get_supervisor_floor(supervisor_id):
    row = query("SELECT Assigned_Floor FROM SUPERVISOR WHERE Staff_ID = %s", (supervisor_id,), fetchone=True)
    return row["Assigned_Floor"] if row else None


def get_floor_schedule(supervisor_id, date, block=None, shift_id=None):
    floor_no = get_supervisor_floor(supervisor_id)
    if floor_no is None:
        return [], []

    conditions = ["cl.Floor_No = %s", "cl.Location_Status = 'Active'"]
    params = [floor_no]

    if block:
        conditions.append("cl.Block_Name = %s")
        params.append(block)

    task_join_conditions = ["ct.Location_ID = cl.Location_ID", "ct.Task_Date = %s"]
    task_join_params = [date]
    if shift_id:
        task_join_conditions.append("ct.Shift_ID = %s")
        task_join_params.append(shift_id)

    sql = f"""
        SELECT cl.Location_ID, cl.Block_Name, cl.Room_No, cl.Location_Type,
               ct.Task_ID, s.Name AS Staff_Name, sh.Shift_Name, ct.Task_Status
        FROM CAMPUS_LOCATION cl
        LEFT JOIN CLEANING_TASK ct ON {' AND '.join(task_join_conditions)}
        LEFT JOIN STAFF s ON s.Staff_ID = ct.Staff_ID
        LEFT JOIN SHIFT sh ON sh.Shift_ID = ct.Shift_ID
        WHERE {' AND '.join(conditions)}
        ORDER BY cl.Block_Name, cl.Room_No, sh.Start_Time
    """
    rows = query(sql, tuple(task_join_params + params))
    blocks = list_blocks_on_floor(floor_no)
    return rows, blocks
