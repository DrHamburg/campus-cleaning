

from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from middleware.decorators import require_role
from services import handout_service, material_service

handouts_bp = Blueprint("handouts", __name__)


@handouts_bp.route("/supervisor/handouts", methods=["GET"])
@require_role("SUPERVISOR")
def supervisor_handout_list():
    handouts = handout_service.list_handouts_for_supervisor(session["staff_id"])
    return render_template(
        "supervisor/handouts_list.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="handouts",
        handouts=handouts,
    )


@handouts_bp.route("/supervisor/handouts/new", methods=["GET"])
@require_role("SUPERVISOR")
def supervisor_handout_new():
    staff = handout_service.list_assignable_staff_for_supervisor(session["staff_id"])
    materials = material_service.list_materials()
    return render_template(
        "supervisor/handout_form.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="handouts",
        staff=staff, materials=materials, slots=range(1, handout_service.MAX_ITEMS_PER_FORM + 1),
    )


@handouts_bp.route("/supervisor/handouts/new", methods=["POST"])
@require_role("SUPERVISOR")
def supervisor_handout_create():
    supervisor_id = session["staff_id"]
    staff_id = request.form.get("staff_id")
    purpose = request.form.get("purpose")
    handout_date = request.form.get("handout_date")

    if not all([staff_id, handout_date]):
        flash("Staff and date are required.", "error")
        return redirect(url_for("handouts.supervisor_handout_new"))

    items = []
    for i in range(1, handout_service.MAX_ITEMS_PER_FORM + 1):
        material_id = request.form.get(f"material_id_{i}")
        quantity = request.form.get(f"quantity_{i}")
        if material_id and quantity:
            try:
                qty = int(quantity)
            except ValueError:
                continue
            if qty > 0:
                items.append((int(material_id), qty))

    if not items:
        flash("Add at least one material with a quantity greater than zero.", "error")
        return redirect(url_for("handouts.supervisor_handout_new"))

    result = handout_service.create_handout(supervisor_id, int(staff_id), purpose, handout_date, items)

    if not result["ok"]:
        if result["reason"] == "out_of_scope":
            flash("Forbidden: staff member is not under your supervision.", "error")
        elif result["reason"] == "insufficient_stock":
            flash(f"Not enough stock — only {result['available']} available for one of the selected materials.", "error")
        else:
            flash("Could not create handout.", "error")
        return redirect(url_for("handouts.supervisor_handout_new"))

    flash("Material handout created and inventory updated.", "success")
    return redirect(url_for("handouts.supervisor_handout_detail", handout_id=result["handout_id"]))


@handouts_bp.route("/supervisor/handouts/<int:handout_id>", methods=["GET"])
@require_role("SUPERVISOR")
def supervisor_handout_detail(handout_id):
    supervisor_id = session["staff_id"]
    if not handout_service.is_handout_in_supervisor_scope(handout_id, supervisor_id):
        flash("Forbidden: this handout is not under your supervision.", "error")
        return redirect(url_for("handouts.supervisor_handout_list"))

    handout, items = handout_service.get_handout_with_items(handout_id)
    if not handout:
        flash("Handout not found.", "error")
        return redirect(url_for("handouts.supervisor_handout_list"))

    return render_template(
        "supervisor/handout_detail.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="handouts",
        handout=handout, items=items,
    )


@handouts_bp.route("/supervisor/handouts/<int:handout_id>/items/<int:item_no>/return", methods=["POST"])
@require_role("SUPERVISOR")
def supervisor_handout_mark_returned(handout_id, item_no):
    supervisor_id = session["staff_id"]
    status = request.form.get("return_status")
    result = handout_service.mark_item_returned(handout_id, item_no, supervisor_id, status)

    if not result["ok"]:
        flash("Could not update return status.", "error")
    else:
        flash("Return status updated.", "success")

    return redirect(url_for("handouts.supervisor_handout_detail", handout_id=handout_id))


@handouts_bp.route("/staff/handouts", methods=["GET"])
@require_role("CLEANING_STAFF")
def staff_handout_list():
    handouts = handout_service.list_handouts_for_staff(session["staff_id"])
    return render_template(
        "staff/handouts_list.html",
        role="CLEANING_STAFF", user_name=session.get("user_name"), active_page="handouts",
        handouts=handouts,
    )


@handouts_bp.route("/staff/handouts/<int:handout_id>", methods=["GET"])
@require_role("CLEANING_STAFF")
def staff_handout_detail(handout_id):
    staff_id = session["staff_id"]
    handout, items = handout_service.get_handout_with_items(handout_id)

    if not handout or int(handout["Staff_ID"]) != int(staff_id):
        flash("Forbidden.", "error")
        return redirect(url_for("handouts.staff_handout_list"))

    return render_template(
        "staff/handout_detail.html",
        role="CLEANING_STAFF", user_name=session.get("user_name"), active_page="handouts",
        handout=handout, items=items,
    )
