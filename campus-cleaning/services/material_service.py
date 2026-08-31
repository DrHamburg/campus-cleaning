from config.database import query, execute


def _compute_status(current_stock, reorder_level):
    if current_stock <= 0:
        return "Out of Stock"
    if current_stock <= reorder_level:
        return "Low Stock"
    return "Available"


def list_materials(search=None):
    conditions = []
    params = []
    if search:
        conditions.append("Material_Name LIKE %s")
        params.append(f"%{search}%")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return query(
        f"SELECT Material_ID, Material_Name, Current_Stock, Reorder_Level, Material_Status "
        f"FROM CLEANING_MATERIAL {where} ORDER BY Material_Name",
        tuple(params)
    )


def get_material_by_id(material_id):
    return query(
        "SELECT Material_ID, Material_Name, Current_Stock, Reorder_Level, Material_Status FROM CLEANING_MATERIAL WHERE Material_ID = %s",
        (material_id,), fetchone=True
    )


def create_material(name, initial_stock, reorder_level):
    if initial_stock < 0 or reorder_level < 0:
        return {"ok": False, "reason": "negative_value"}

    status = _compute_status(initial_stock, reorder_level)
    material_id, _ = execute(
        "INSERT INTO CLEANING_MATERIAL (Material_Name, Current_Stock, Reorder_Level, Material_Status) VALUES (%s, %s, %s, %s)",
        (name, initial_stock, reorder_level, status)
    )
    return {"ok": True, "material_id": material_id}


def update_material_details(material_id, name=None, reorder_level=None):
    material = get_material_by_id(material_id)
    if not material:
        return {"ok": False, "reason": "not_found"}

    new_reorder_level = material["Reorder_Level"] if reorder_level is None else reorder_level
    if new_reorder_level < 0:
        return {"ok": False, "reason": "negative_value"}

    new_name = material["Material_Name"] if name is None else name
    new_status = _compute_status(material["Current_Stock"], new_reorder_level)

    execute(
        "UPDATE CLEANING_MATERIAL SET Material_Name = %s, Reorder_Level = %s, Material_Status = %s WHERE Material_ID = %s",
        (new_name, new_reorder_level, new_status, material_id)
    )
    return {"ok": True}


def adjust_stock(material_id, delta):
    material = get_material_by_id(material_id)
    if not material:
        return {"ok": False, "reason": "not_found"}

    new_stock = material["Current_Stock"] + delta
    if new_stock < 0:
        return {"ok": False, "reason": "would_go_negative", "current_stock": material["Current_Stock"]}

    new_status = _compute_status(new_stock, material["Reorder_Level"])
    execute(
        "UPDATE CLEANING_MATERIAL SET Current_Stock = %s, Material_Status = %s WHERE Material_ID = %s",
        (new_stock, new_status, material_id)
    )
    return {"ok": True, "new_stock": new_stock, "new_status": new_status}
