

from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from middleware.decorators import require_role
from services import material_service

materials_bp = Blueprint("materials", __name__)


@materials_bp.route("/supervisor/materials", methods=["GET"])
@require_role("SUPERVISOR")
def list_materials():
    search = request.args.get("search") or None
    materials = material_service.list_materials(search=search)
    return render_template(
        "supervisor/materials_list.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="materials",
        materials=materials, filter_search=search or "",
    )


@materials_bp.route("/supervisor/materials/new", methods=["GET"])
@require_role("SUPERVISOR")
def material_new():
    return render_template(
        "supervisor/material_form.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="materials",
        mode="create", material=None,
    )


@materials_bp.route("/supervisor/materials/new", methods=["POST"])
@require_role("SUPERVISOR")
def material_create():
    name = request.form.get("name")
    initial_stock = request.form.get("initial_stock")
    reorder_level = request.form.get("reorder_level")

    if not name or initial_stock is None or reorder_level is None:
        flash("Name, initial stock, and reorder level are required.", "error")
        return redirect(url_for("materials.material_new"))

    try:
        initial_stock = int(initial_stock)
        reorder_level = int(reorder_level)
    except ValueError:
        flash("Stock and reorder level must be whole numbers.", "error")
        return redirect(url_for("materials.material_new"))

    result = material_service.create_material(name, initial_stock, reorder_level)
    if not result["ok"]:
        flash("Stock and reorder level cannot be negative.", "error")
        return redirect(url_for("materials.material_new"))

    flash(f"{name} added to inventory.", "success")
    return redirect(url_for("materials.list_materials"))


@materials_bp.route("/supervisor/materials/<int:material_id>/edit", methods=["GET"])
@require_role("SUPERVISOR")
def material_edit(material_id):
    material = material_service.get_material_by_id(material_id)
    if not material:
        flash("Material not found.", "error")
        return redirect(url_for("materials.list_materials"))
    return render_template(
        "supervisor/material_form.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="materials",
        mode="edit", material=material,
    )


@materials_bp.route("/supervisor/materials/<int:material_id>/edit", methods=["POST"])
@require_role("SUPERVISOR")
def material_update(material_id):
    name = request.form.get("name")
    reorder_level = request.form.get("reorder_level")

    try:
        reorder_level = int(reorder_level) if reorder_level is not None else None
    except ValueError:
        flash("Reorder level must be a whole number.", "error")
        return redirect(url_for("materials.material_edit", material_id=material_id))

    result = material_service.update_material_details(material_id, name=name, reorder_level=reorder_level)
    if not result["ok"]:
        messages = {"not_found": "Material not found.", "negative_value": "Reorder level cannot be negative."}
        flash(messages.get(result["reason"], "Could not update material."), "error")
        return redirect(url_for("materials.material_edit", material_id=material_id))

    flash("Material updated.", "success")
    return redirect(url_for("materials.list_materials"))


@materials_bp.route("/supervisor/materials/<int:material_id>/adjust", methods=["GET"])
@require_role("SUPERVISOR")
def material_adjust_page(material_id):
    material = material_service.get_material_by_id(material_id)
    if not material:
        flash("Material not found.", "error")
        return redirect(url_for("materials.list_materials"))
    return render_template(
        "supervisor/material_adjust.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="materials",
        material=material,
    )


@materials_bp.route("/supervisor/materials/<int:material_id>/adjust", methods=["POST"])
@require_role("SUPERVISOR")
def material_adjust(material_id):
    action = request.form.get("action")
    amount = request.form.get("amount")

    try:
        amount = int(amount)
    except (ValueError, TypeError):
        flash("Please enter a whole number.", "error")
        return redirect(url_for("materials.material_adjust_page", material_id=material_id))

    if amount <= 0:
        flash("Amount must be greater than zero.", "error")
        return redirect(url_for("materials.material_adjust_page", material_id=material_id))

    delta = amount if action == "add" else -amount
    result = material_service.adjust_stock(material_id, delta)

    if not result["ok"]:
        if result["reason"] == "would_go_negative":
            flash(f"Cannot remove {amount} — only {result['current_stock']} in stock.", "error")
        else:
            flash("Could not adjust stock.", "error")
        return redirect(url_for("materials.material_adjust_page", material_id=material_id))

    flash(f"Stock updated to {result['new_stock']} ({result['new_status']}).", "success")
    return redirect(url_for("materials.list_materials"))
