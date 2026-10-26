from datetime import date
from decimal import Decimal, InvalidOperation

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from ..decorators import admin_required
from ..extensions import db
from ..models import Person
from . import bp


def _parse_nonnegative_int(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        number = int(value)
        return number if 0 <= number <= 2147483647 else "invalid"
    except (TypeError, ValueError):
        return "invalid"


def _parse_incentives(value):
    value = (value or "").strip().replace(",", "")
    if not value:
        return None
    try:
        amount = Decimal(value)
        if not amount.is_finite() or amount < 0 or amount > Decimal("99999999.99"):
            return "invalid"
        return amount.quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return "invalid"


def _parse_date(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return "invalid"


@bp.route("/")
@admin_required
def index():
    query = request.args.get("q", "").strip()
    people_query = Person.query
    if query:
        like = f"%{query}%"
        people_query = people_query.filter(
            or_(Person.employee_code.ilike(like), Person.full_name.ilike(like),
                Person.department.ilike(like), Person.project_name.ilike(like))
        )
    people = people_query.order_by(Person.active.desc(), Person.id.asc()).all()
    return render_template("people/list.html", people=people, query=query)


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def create():
    if request.method == "POST":
        employee_code = request.form.get("employee_code", "").strip()
        full_name = request.form.get("full_name", "").strip()
        interviews_tech = _parse_nonnegative_int(request.form.get("interviews_tech"))
        incentives = _parse_incentives(request.form.get("incentives"))
        department = request.form.get("department", "").strip() or None
        project_name = request.form.get("project_name", "").strip() or None
        joined_on = _parse_date(request.form.get("joined_on"))
        if not employee_code or not full_name:
            flash("Employee code and full name are required.", "danger")
        elif joined_on == "invalid":
            flash("Join date must be a valid date.", "danger")
        elif interviews_tech == "invalid":
            flash("INTERVIEWS(TECH) must be a non-negative whole number.", "danger")
        elif incentives == "invalid":
            flash("INCENTIVES must be a non-negative amount with up to two decimal places.", "danger")
        else:
            person = Person(
                employee_code=employee_code,
                full_name=full_name,
                interviews_tech=interviews_tech,
                incentives=incentives,
                department=department,
                project_name=project_name,
                joined_on=joined_on,
                active=True,
            )
            try:
                db.session.add(person)
                db.session.commit()
                flash(f"{full_name} was added.", "success")
                return redirect(url_for("people.index"))
            except IntegrityError:
                db.session.rollback()
                flash("That employee code is already in use.", "danger")
    return render_template("people/form.html", person=None, page_title="Add person")


@bp.route("/<int:person_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(person_id):
    person = Person.query.get_or_404(person_id)
    if request.method == "POST":
        employee_code = request.form.get("employee_code", "").strip()
        full_name = request.form.get("full_name", "").strip()
        interviews_tech = _parse_nonnegative_int(request.form.get("interviews_tech"))
        incentives = _parse_incentives(request.form.get("incentives"))
        joined_on = _parse_date(request.form.get("joined_on"))
        if not employee_code or not full_name:
            flash("Employee code and full name are required.", "danger")
        elif joined_on == "invalid":
            flash("Join date must be a valid date.", "danger")
        elif interviews_tech == "invalid":
            flash("INTERVIEWS(TECH) must be a non-negative whole number.", "danger")
        elif incentives == "invalid":
            flash("INCENTIVES must be a non-negative amount with up to two decimal places.", "danger")
        else:
            person.employee_code = employee_code
            person.full_name = full_name
            person.interviews_tech = interviews_tech
            person.incentives = incentives
            person.department = request.form.get("department", "").strip() or None
            person.project_name = request.form.get("project_name", "").strip() or None
            person.joined_on = joined_on
            try:
                db.session.commit()
                flash("Person details updated.", "success")
                return redirect(url_for("people.index"))
            except IntegrityError:
                db.session.rollback()
                flash("That employee code is already assigned to another person.", "danger")
    return render_template("people/form.html", person=person, page_title="Edit person")


@bp.route("/<int:person_id>/toggle-active", methods=["POST"])
@admin_required
def toggle_active(person_id):
    person = Person.query.get_or_404(person_id)
    person.active = not person.active
    db.session.commit()
    state = "activated" if person.active else "deactivated"
    flash(f"{person.full_name} was {state}. Existing attendance history has been retained.", "success")
    return redirect(url_for("people.index"))
