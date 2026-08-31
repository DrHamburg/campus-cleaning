from config.database import get_connection, query, execute
from services.material_service import _compute_status

MAX_ITEMS_PER_FORM = 5 


def list_assignable_staff_for_supervisor(supervisor_id):
    return query(
        """SELECT s.Staff_ID, s.Name
           FROM CLEANING_STAFF cs JOIN STAFF s ON s.Staff_ID = cs.Staff_ID
           WHERE cs.Supervisor_ID = %s AND s.Status = 'Active'
           ORDER BY s.Name""",
        (supervisor_id,)
    )


def is_staff_in_supervisor_scope(staff_id, supervisor_id):
    row = query(
        "SELECT Staff_ID FROM CLEANING_STAFF WHERE Staff_ID = %s AND Supervisor_ID = %s",
        (staff_id, supervisor_id), fetchone=True
    )
    return row is not None


def create_handout(supervisor_id, staff_id, purpose, handout_date, items):
    if not is_staff_in_supervisor_scope(staff_id, supervisor_id):
        return {"ok": False, "reason": "out_of_scope"}
    if not items:
        return {"ok": False, "reason": "no_items"}

    conn = get_connection()
    try:
        conn.start_transaction()
        cur = conn.cursor(dictionary=True)

        cur.execute(
            "INSERT INTO MATERIAL_HANDOUT (Staff_ID, Issued_By, Handout_Date, Usage_Purpose) VALUES (%s, %s, %s, %s)",
            (staff_id, supervisor_id, handout_date, purpose)
        )
        handout_id = cur.lastrowid

        item_no = 1
        for material_id, quantity in items:
            cur.execute("SELECT Current_Stock, Reorder_Level FROM CLEANING_MATERIAL WHERE Material_ID = %s FOR UPDATE", (material_id,))
            material = cur.fetchone()
            if not material:
                conn.rollback()
                return {"ok": False, "reason": "material_not_found"}
            if material["Current_Stock"] < quantity:
                conn.rollback()
                return {"ok": False, "reason": "insufficient_stock", "material_id": material_id, "available": material["Current_Stock"]}

            cur.execute(
                "INSERT INTO HANDOUT_ITEM (Handout_ID, Item_No, Material_ID, Quantity) VALUES (%s, %s, %s, %s)",
                (handout_id, item_no, material_id, quantity)
            )

            new_stock = material["Current_Stock"] - quantity
            new_status = _compute_status(new_stock, material["Reorder_Level"])
            cur.execute(
                "UPDATE CLEANING_MATERIAL SET Current_Stock = %s, Material_Status = %s WHERE Material_ID = %s",
                (new_stock, new_status, material_id)
            )
            item_no += 1

        conn.commit()
        return {"ok": True, "handout_id": handout_id}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_handouts_for_supervisor(supervisor_id):
    return query(
        """SELECT mh.Handout_ID, mh.Staff_ID, s.Name AS Staff_Name,
                  DATE_FORMAT(mh.Handout_Date, '%Y-%m-%d') AS Handout_Date, mh.Usage_Purpose
           FROM MATERIAL_HANDOUT mh
           JOIN CLEANING_STAFF cs ON cs.Staff_ID = mh.Staff_ID
           JOIN STAFF s ON s.Staff_ID = mh.Staff_ID
           WHERE cs.Supervisor_ID = %s
           ORDER BY mh.Handout_Date DESC, mh.Handout_ID DESC""",
        (supervisor_id,)
    )


def list_handouts_for_staff(staff_id):
    return query(
        """SELECT Handout_ID, DATE_FORMAT(Handout_Date, '%Y-%m-%d') AS Handout_Date, Usage_Purpose
           FROM MATERIAL_HANDOUT WHERE Staff_ID = %s ORDER BY Handout_Date DESC, Handout_ID DESC""",
        (staff_id,)
    )


def get_handout_with_items(handout_id):
    handout = query(
        """SELECT mh.Handout_ID, mh.Staff_ID, s.Name AS Staff_Name, mh.Issued_By, sup.Name AS Issued_By_Name,
                  DATE_FORMAT(mh.Handout_Date, '%Y-%m-%d') AS Handout_Date, mh.Usage_Purpose
           FROM MATERIAL_HANDOUT mh
           JOIN STAFF s ON s.Staff_ID = mh.Staff_ID
           JOIN STAFF sup ON sup.Staff_ID = mh.Issued_By
           WHERE mh.Handout_ID = %s""",
        (handout_id,), fetchone=True
    )
    if not handout:
        return None, []
    items = query(
        """SELECT hi.Item_No, hi.Material_ID, cm.Material_Name, hi.Quantity, hi.Return_Status
           FROM HANDOUT_ITEM hi JOIN CLEANING_MATERIAL cm ON cm.Material_ID = hi.Material_ID
           WHERE hi.Handout_ID = %s ORDER BY hi.Item_No""",
        (handout_id,)
    )
    return handout, items


def is_handout_in_supervisor_scope(handout_id, supervisor_id):
    row = query(
        """SELECT mh.Handout_ID FROM MATERIAL_HANDOUT mh
           JOIN CLEANING_STAFF cs ON cs.Staff_ID = mh.Staff_ID
           WHERE mh.Handout_ID = %s AND cs.Supervisor_ID = %s""",
        (handout_id, supervisor_id), fetchone=True
    )
    return row is not None


def mark_item_returned(handout_id, item_no, supervisor_id, return_status):
    if not is_handout_in_supervisor_scope(handout_id, supervisor_id):
        return {"ok": False, "reason": "out_of_scope"}
    if return_status not in ("Returned", "Not Returned", "Partially Returned"):
        return {"ok": False, "reason": "invalid_status"}
    execute(
        "UPDATE HANDOUT_ITEM SET Return_Status = %s WHERE Handout_ID = %s AND Item_No = %s",
        (return_status, handout_id, item_no)
    )
    return {"ok": True}
