

from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from middleware.decorators import require_role
from services import staff_service

staff_bp = Blueprint("staff", __name__)


@staff_bp.route("/supervisor/staff", methods=["GET"])
@require_role("SUPERVISOR")
def list_staff():
    supervisor_id = session["staff_id"]
    status = request.args.get("status") or None
    staff = staff_service.list_staff_for_supervisor(supervisor_id, status=status)
    return render_template(
        "supervisor/staff_list.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="staff",
        staff=staff, filter_status=status or "",
    )


@staff_bp.route("/supervisor/staff/new", methods=["GET"])
@require_role("SUPERVISOR")
def staff_new():
    return render_template(
        "supervisor/staff_form.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="staff",
        mode="create", staff=None,
    )


@staff_bp.route("/supervisor/staff/new", methods=["POST"])
@require_role("SUPERVISOR")
def staff_create():
    supervisor_id = session["staff_id"]
    form = request.form

    name = form.get("name")
    email = form.get("email")
    date_of_joining = form.get("date_of_joining")
    assigned_area = form.get("assigned_area")
    assigned_block = form.get("assigned_block")

    if not all([name, email, date_of_joining, assigned_area, assigned_block]):
        flash("Name, email, date of joining, block, and assigned area are required.", "error")
        return redirect(url_for("staff.staff_new"))

    result = staff_service.create_staff(
        supervisor_id, name, form.get("phone"), email, form.get("gender"),
        form.get("address"), form.get("nid"), date_of_joining, assigned_area, assigned_block
    )

    if not result["ok"]:
        if result["reason"] == "duplicate_email":
            flash("A staff member with this email already exists.", "error")
        else:
            flash("Could not create staff member.", "error")
        return redirect(url_for("staff.staff_new"))

    flash(f"{name} was created successfully. Temporary password: {result['temporary_password']} — share this with them, they'll be asked to change it on first login.", "success")
    return redirect(url_for("staff.list_staff"))


@staff_bp.route("/supervisor/staff/<int:staff_id>/edit", methods=["GET"])
@require_role("SUPERVISOR")
def staff_edit(staff_id):
    supervisor_id = session["staff_id"]
    if not staff_service.is_staff_in_supervisor_scope(staff_id, supervisor_id):
        flash("Forbidden: this staff member is not under your supervision.", "error")
        return redirect(url_for("staff.list_staff"))

    staff = staff_service.get_staff_by_id(staff_id)
    if not staff:
        flash("Staff member not found.", "error")
        return redirect(url_for("staff.list_staff"))

    return render_template(
        "supervisor/staff_form.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="staff",
        mode="edit", staff=staff,
    )


@staff_bp.route("/supervisor/staff/<int:staff_id>/edit", methods=["POST"])
@require_role("SUPERVISOR")
def staff_update(staff_id):
    supervisor_id = session["staff_id"]
    form = request.form

    result = staff_service.update_staff(
        staff_id, supervisor_id,
        phone=form.get("phone"), address=form.get("address"),
        assigned_area=form.get("assigned_area"), assigned_block=form.get("assigned_block"),
        status=form.get("status"),
    )

    if not result["ok"]:
        messages = {
            "out_of_scope": "Forbidden: this staff member is not under your supervision.",
            "invalid_status": "Status must be 'Active' or 'Inactive'.",
            "invalid_block": "Assigned block must be a single letter A-H.",
            "no_changes": "No fields to update.",
        }
        flash(messages.get(result["reason"], "Could not update staff member."), "error")
        return redirect(url_for("staff.staff_edit", staff_id=staff_id))

    flash("Staff member updated.", "success")
    return redirect(url_for("staff.list_staff"))


@staff_bp.route("/supervisor/staff/<int:staff_id>/deactivate", methods=["POST"])
@require_role("SUPERVISOR")
def staff_deactivate(staff_id):
    supervisor_id = session["staff_id"]
    result = staff_service.deactivate_staff(staff_id, supervisor_id)

    if not result["ok"]:
        flash("Could not deactivate staff member.", "error")
    else:
        flash("Staff member deactivated.", "success")

    return redirect(url_for("staff.list_staff"))



@staff_bp.route("/supervisor/staff/<int:staff_id>/view", methods=["GET"])
@require_role("SUPERVISOR")
def staff_view(staff_id):
    supervisor_id = session["staff_id"]
    if not staff_service.is_staff_in_supervisor_scope(staff_id, supervisor_id):
        flash("Forbidden: this staff member is not under your supervision.", "error")
        return redirect(url_for("staff.list_staff"))

    staff = staff_service.get_staff_by_id(staff_id)
    if not staff:
        flash("Staff member not found.", "error")
        return redirect(url_for("staff.list_staff"))

    return render_template(
        "supervisor/staff_view.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="staff",
        staff=staff,
    )


@staff_bp.route("/supervisor/my-staff", methods=["GET"])
@require_role("SUPERVISOR")
def my_staff_list():
    """Dashboard-linked, read-only staff listing — profile viewing only,
    no Edit/Deactivate actions here (those live on the separate Staff
    Management page, reachable from the sidebar)."""
    supervisor_id = session["staff_id"]
    staff = staff_service.list_staff_for_supervisor(supervisor_id)
    return render_template(
        "supervisor/my_staff_list.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="dashboard",
        staff=staff,
    )


@staff_bp.route("/staff/my-floor", methods=["GET"])
@require_role("CLEANING_STAFF")
def my_floor():
    coworkers = staff_service.list_coworkers(session["staff_id"])
    return render_template(
        "staff/my_floor.html",
        role="CLEANING_STAFF", user_name=session.get("user_name"), active_page="dashboard",
        coworkers=coworkers, session_staff_id=session["staff_id"],
    )
