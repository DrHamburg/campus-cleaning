from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from middleware.decorators import require_auth, require_role
from services import task_service

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("/supervisor/tasks", methods=["GET"])
@require_role("SUPERVISOR")
def supervisor_task_list():
    supervisor_id = session["staff_id"]
    date = request.args.get("date") or None
    status = request.args.get("status") or None

    tasks = task_service.list_tasks_for_supervisor(supervisor_id, date=date, status=status)

    return render_template(
        "supervisor/tasks_list.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="tasks",
        tasks=tasks, filter_date=date or "", filter_status=status or "",
    )


@tasks_bp.route("/supervisor/tasks/new", methods=["GET"])
@require_role("SUPERVISOR")
def supervisor_task_new():
    supervisor_id = session["staff_id"]
    block = request.args.get("block")

    if not block:
        blocks = task_service.list_blocks_for_supervisor(supervisor_id)
        return render_template(
            "supervisor/task_block_select.html",
            role="SUPERVISOR", user_name=session.get("user_name"), active_page="tasks",
            blocks=blocks,
        )

    staff = task_service.list_assignable_staff_for_block(supervisor_id, block)
    locations = task_service.list_assignable_locations_for_block(supervisor_id, block)
    shifts = task_service.list_shifts()

    return render_template(
        "supervisor/task_form.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="tasks",
        block=block, staff=staff, locations=locations, shifts=shifts,
        mode="create", task=None,
    )


@tasks_bp.route("/supervisor/tasks/new", methods=["POST"])
@require_role("SUPERVISOR")
def supervisor_task_create():
    supervisor_id = session["staff_id"]
    staff_id = request.form.get("staff_id")
    location_id = request.form.get("location_id")
    shift_id = request.form.get("shift_id")
    task_date = request.form.get("task_date")
    remarks = request.form.get("remarks")
    block = request.form.get("block")

    if not all([staff_id, location_id, shift_id, task_date]):
        flash("Please fill in staff, location, shift, and date.", "error")
        return redirect(url_for("tasks.supervisor_task_new", block=block))

    result = task_service.create_task(supervisor_id, int(staff_id), location_id, int(shift_id), task_date, remarks)

    if not result["ok"]:
        if result["reason"] == "out_of_scope":
            flash("Forbidden: staff member or location is outside your assigned floor.", "error")
        else:
            flash("Could not create task.", "error")
        return redirect(url_for("tasks.supervisor_task_new", block=block))

    flash("Task created successfully.", "success")
    return redirect(url_for("tasks.supervisor_task_list"))


@tasks_bp.route("/supervisor/tasks/<int:task_id>/view", methods=["GET"])
@require_role("SUPERVISOR")
def supervisor_task_view(task_id):
    supervisor_id = session["staff_id"]
    if not task_service.is_task_in_supervisor_scope(task_id, supervisor_id):
        flash("Forbidden: task is outside your assigned floor.", "error")
        return redirect(url_for("tasks.supervisor_task_list"))

    task = task_service.get_task_by_id(task_id)
    if not task:
        flash("Task not found.", "error")
        return redirect(url_for("tasks.supervisor_task_list"))

    return render_template(
        "supervisor/task_view.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="tasks",
        task=task,
    )


@tasks_bp.route("/supervisor/tasks/<int:task_id>/edit", methods=["GET"])
@require_role("SUPERVISOR")
def supervisor_task_edit(task_id):
    supervisor_id = session["staff_id"]
    if not task_service.is_task_in_supervisor_scope(task_id, supervisor_id):
        flash("Forbidden: task is outside your assigned floor.", "error")
        return redirect(url_for("tasks.supervisor_task_list"))

    task = task_service.get_task_by_id(task_id)
    if not task:
        flash("Task not found.", "error")
        return redirect(url_for("tasks.supervisor_task_list"))

    
    block = request.args.get("block") or task["Block_Name"]

    staff = task_service.list_assignable_staff_for_block(supervisor_id, block)
    locations = task_service.list_assignable_locations_for_block(supervisor_id, block)
    shifts = task_service.list_shifts()
    all_blocks = task_service.list_blocks_for_supervisor(supervisor_id)

    return render_template(
        "supervisor/task_form.html",
        role="SUPERVISOR", user_name=session.get("user_name"), active_page="tasks",
        block=block, staff=staff, locations=locations, shifts=shifts,
        mode="edit", task=task, all_blocks=all_blocks,
    )


@tasks_bp.route("/supervisor/tasks/<int:task_id>/edit", methods=["POST"])
@require_role("SUPERVISOR")
def supervisor_task_update(task_id):
    supervisor_id = session["staff_id"]
    block = request.form.get("block")

    updates = {}
    if request.form.get("staff_id"):
        updates["staffId"] = int(request.form["staff_id"])
    if request.form.get("location_id"):
        updates["locationId"] = request.form["location_id"]
    if request.form.get("shift_id"):
        updates["shiftId"] = int(request.form["shift_id"])
    if request.form.get("task_date"):
        updates["taskDate"] = request.form["task_date"]
    if request.form.get("status"):
        updates["status"] = request.form["status"]
    updates["remarks"] = request.form.get("remarks", "")

    result = task_service.update_task_by_supervisor(task_id, supervisor_id, updates)

    if not result["ok"]:
        reason = result["reason"]
        messages = {
            "out_of_scope": "Forbidden: task or new assignment is outside your assigned floor.",
            "not_found": "Task not found.",
            "invalid_status": "Invalid task status.",
            "no_changes": "No fields to update.",
        }
        flash(messages.get(reason, "Could not update task."), "error")
        return redirect(url_for("tasks.supervisor_task_edit", task_id=task_id, block=block))

    flash("Task updated successfully.", "success")
    return redirect(url_for("tasks.supervisor_task_list"))


@tasks_bp.route("/supervisor/tasks/<int:task_id>/cancel", methods=["POST"])
@require_role("SUPERVISOR")
def supervisor_task_cancel(task_id):
    supervisor_id = session["staff_id"]
    result = task_service.cancel_task_by_supervisor(task_id, supervisor_id)

    if not result["ok"]:
        messages = {
            "out_of_scope": "Forbidden: task is outside your assigned floor.",
            "not_found": "Task not found.",
            "already_completed": "Cannot cancel a completed task.",
        }
        flash(messages.get(result["reason"], "Could not cancel task."), "error")
    else:
        flash("Task cancelled.", "success")

    return redirect(url_for("tasks.supervisor_task_list"))


@tasks_bp.route("/staff/tasks", methods=["GET"])
@require_role("CLEANING_STAFF")
def staff_task_list():
    staff_id = session["staff_id"]
    date = request.args.get("date") or None
    status = request.args.get("status") or None

    tasks = task_service.list_tasks_for_staff(staff_id, date=date, status=status)

    return render_template(
        "staff/tasks_list.html",
        role="CLEANING_STAFF", user_name=session.get("user_name"), active_page="tasks",
        tasks=tasks, filter_date=date or "", filter_status=status or "",
    )


@tasks_bp.route("/staff/tasks/<int:task_id>", methods=["GET"])
@require_role("CLEANING_STAFF")
def staff_task_detail(task_id):
    staff_id = session["staff_id"]
    task = task_service.get_task_by_id(task_id)

    if not task or int(task["Staff_ID"]) != int(staff_id):
        flash("Forbidden.", "error")
        return redirect(url_for("tasks.staff_task_list"))

    return render_template(
        "staff/task_detail.html",
        role="CLEANING_STAFF", user_name=session.get("user_name"), active_page="tasks",
        task=task,
    )


@tasks_bp.route("/staff/tasks/<int:task_id>/update", methods=["GET"])
@require_role("CLEANING_STAFF")
def staff_task_update_page(task_id):
    staff_id = session["staff_id"]
    task = task_service.get_task_by_id(task_id)

    if not task or int(task["Staff_ID"]) != int(staff_id):
        flash("Forbidden.", "error")
        return redirect(url_for("tasks.staff_task_list"))

    if task["Task_Status"] in ("Completed", "Cancelled"):
        flash("This task can no longer be updated.", "error")
        return redirect(url_for("tasks.staff_task_detail", task_id=task_id))

    return render_template(
        "staff/task_update.html",
        role="CLEANING_STAFF", user_name=session.get("user_name"), active_page="tasks",
        task=task,
    )


@tasks_bp.route("/staff/tasks/<int:task_id>/progress", methods=["POST"])
@require_role("CLEANING_STAFF")
def staff_task_progress(task_id):
    staff_id = session["staff_id"]
    status = request.form.get("status")
    remarks = request.form.get("remarks")

    result = task_service.update_task_progress_by_staff(task_id, staff_id, status=status, remarks=remarks)

    if not result["ok"]:
        messages = {
            "not_found": "Task not found.",
            "not_your_task": "Forbidden: this task is not assigned to you.",
            "invalid_status_for_staff": "You may only set status to 'In Progress' or 'Completed'.",
            "no_changes": "No fields to update.",
        }
        flash(messages.get(result["reason"], "Could not update task."), "error")
        return redirect(url_for("tasks.staff_task_update_page", task_id=task_id))

    flash("Task updated.", "success")
    return redirect(url_for("tasks.staff_task_detail", task_id=task_id))
