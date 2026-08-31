import re
from config.database import get_connection, query, execute
from utils.password import hash_password

TEMP_PASSWORD = "Temp@1234"

STAFF_SELECT = """
    SELECT s.Staff_ID, s.Name, s.Phone_Number, s.Email, s.Gender, s.Address,
           s.NID, DATE_FORMAT(s.Date_of_Joining, '%Y-%m-%d') AS Date_of_Joining, s.Status,
           cs.Assigned_Area, cs.Assigned_Block, cs.Supervisor_ID
    FROM CLEANING_STAFF cs
    JOIN STAFF s ON s.Staff_ID = cs.Staff_ID
"""


def is_staff_in_supervisor_scope(staff_id, supervisor_id):
    row = query(
        "SELECT Staff_ID FROM CLEANING_STAFF WHERE Staff_ID = %s AND Supervisor_ID = %s",
        (staff_id, supervisor_id), fetchone=True
    )
    return row is not None


def get_supervisor_profile(staff_id):
    return query(
        """SELECT s.Staff_ID, s.Name, s.Phone_Number, s.Email, s.Gender, s.Address,
                  s.NID, DATE_FORMAT(s.Date_of_Joining, '%Y-%m-%d') AS Date_of_Joining, s.Status,
                  sup.Assigned_Floor
           FROM SUPERVISOR sup
           JOIN STAFF s ON s.Staff_ID = sup.Staff_ID
           WHERE s.Staff_ID = %s""",
        (staff_id,), fetchone=True
    )


def list_coworkers(staff_id):
    own = get_staff_by_id(staff_id)
    if not own:
        return []
    supervisor_id = own["Supervisor_ID"]
    return query(
        """SELECT s.Staff_ID, s.Name, cs.Assigned_Block
           FROM CLEANING_STAFF cs
           JOIN STAFF s ON s.Staff_ID = cs.Staff_ID
           WHERE cs.Supervisor_ID = %s AND s.Status = 'Active'
           ORDER BY cs.Assigned_Block, s.Name""",
        (supervisor_id,)
    )


def list_staff_for_supervisor(supervisor_id, status=None):
    conditions = ["cs.Supervisor_ID = %s"]
    params = [supervisor_id]
    if status:
        conditions.append("s.Status = %s")
        params.append(status)
    sql = f"{STAFF_SELECT} WHERE {' AND '.join(conditions)} ORDER BY s.Name"
    return query(sql, tuple(params))


def get_staff_by_id(staff_id):
    sql = f"{STAFF_SELECT} WHERE s.Staff_ID = %s"
    return query(sql, (staff_id,), fetchone=True)


def create_staff(supervisor_id, name, phone, email, gender, address, nid, date_of_joining, assigned_area, assigned_block):
    conn = get_connection()
    try:
        conn.start_transaction()
        cur = conn.cursor()

        cur.execute(
            """INSERT INTO STAFF (Name, Phone_Number, Email, Gender, Address, NID, Date_of_Joining, Status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'Active')""",
            (name, phone or None, email, gender or None, address or None, nid or None, date_of_joining)
        )
        new_staff_id = cur.lastrowid

        cur.execute(
            """INSERT INTO CLEANING_STAFF (Staff_ID, Assigned_Area, Assigned_Block, Supervisor_ID)
               VALUES (%s, %s, %s, %s)""",
            (new_staff_id, assigned_area, assigned_block, supervisor_id)
        )

        password_hash = hash_password(TEMP_PASSWORD)
        cur.execute(
            """INSERT INTO USER_ACCOUNT (Staff_ID, University_Email, Password_Hash, Role, Account_Status, Must_Change_Password)
               VALUES (%s, %s, %s, 'CLEANING_STAFF', 'ACTIVE', TRUE)""",
            (new_staff_id, email, password_hash)
        )

        conn.commit()
        return {"ok": True, "staff_id": new_staff_id, "temporary_password": TEMP_PASSWORD}
    except Exception as e:
        conn.rollback()
        # MySQL duplicate-entry error code is 1062
        if getattr(e, "errno", None) == 1062:
            return {"ok": False, "reason": "duplicate_email"}
        raise
    finally:
        conn.close()


def update_staff(staff_id, supervisor_id, phone=None, address=None, assigned_area=None, assigned_block=None, status=None):
    if not is_staff_in_supervisor_scope(staff_id, supervisor_id):
        return {"ok": False, "reason": "out_of_scope"}

    staff_fields, staff_params = [], []
    if phone is not None:
        staff_fields.append("Phone_Number = %s"); staff_params.append(phone)
    if address is not None:
        staff_fields.append("Address = %s"); staff_params.append(address)

    account_status_to_sync = None
    if status is not None:
        if status not in ("Active", "Inactive"):
            return {"ok": False, "reason": "invalid_status"}
        staff_fields.append("Status = %s"); staff_params.append(status)
        account_status_to_sync = "ACTIVE" if status == "Active" else "INACTIVE"

    cs_fields, cs_params = [], []
    if assigned_area is not None:
        cs_fields.append("Assigned_Area = %s"); cs_params.append(assigned_area)
    if assigned_block is not None:
        if not re.match(r"^[A-H]$", assigned_block):
            return {"ok": False, "reason": "invalid_block"}
        cs_fields.append("Assigned_Block = %s"); cs_params.append(assigned_block)

    if not staff_fields and not cs_fields:
        return {"ok": False, "reason": "no_changes"}

    if staff_fields:
        staff_params.append(staff_id)
        execute(f"UPDATE STAFF SET {', '.join(staff_fields)} WHERE Staff_ID = %s", tuple(staff_params))
    if cs_fields:
        cs_params.append(staff_id)
        execute(f"UPDATE CLEANING_STAFF SET {', '.join(cs_fields)} WHERE Staff_ID = %s", tuple(cs_params))
    if account_status_to_sync is not None:
        execute("UPDATE USER_ACCOUNT SET Account_Status = %s WHERE Staff_ID = %s", (account_status_to_sync, staff_id))

    return {"ok": True}


def deactivate_staff(staff_id, supervisor_id):
    if not is_staff_in_supervisor_scope(staff_id, supervisor_id):
        return {"ok": False, "reason": "out_of_scope"}

    execute("UPDATE STAFF SET Status = 'Inactive' WHERE Staff_ID = %s", (staff_id,))
    execute("UPDATE USER_ACCOUNT SET Account_Status = 'INACTIVE' WHERE Staff_ID = %s", (staff_id,))
    return {"ok": True}
