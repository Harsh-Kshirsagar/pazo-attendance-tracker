import calendar
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import Attendance, Person
from ..holiday_calendar import day_type_map, india_public_holidays, is_working_date
from . import bp

VALID_STATUSES = {"P", "A", "L", "H"}
MONTH_NAMES = list(calendar.month_name)[1:]


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


def parse_period():
    current = date.today()
    try:
        year = int(request.values.get("year", current.year))
        month = int(request.values.get("month", current.month))
        if year < 2000 or year > 9999 or month < 1 or month > 12:
            raise ValueError
    except (TypeError, ValueError):
        year, month = current.year, current.month
        flash("Invalid month/year supplied. Showing the current period.", "warning")
    return year, month


@bp.route("/monthly", methods=["GET", "POST"])
@login_required
def monthly():
    year, month = parse_period()
    last_day = calendar.monthrange(year, month)[1]
    days = [date(year, month, day) for day in range(1, last_day + 1)]
    # Employee code order mirrors the row order in the PAZO spreadsheet (PAZO001, PAZO002, ...).
    people = Person.query.filter_by(active=True).order_by(Person.employee_code.asc(), Person.id.asc()).all()
    day_types = day_type_map(days)
    holiday_names = india_public_holidays(year)

    if request.method == "POST":
        # Validate the complete submission before changing any saved records.
        submitted = {}
        submitted_metadata = {}
        errors = []
        for person in people:
            # Only administrators can edit employee metadata from this grid.
            # Regular users may update attendance only. Fields are optional here so
            # API/tests posting just attendance statuses do not clear existing values.
            if current_user.role == "admin":
                interview_field = f"interviews_tech_{person.id}"
                incentive_field = f"incentives_{person.id}"
                if interview_field in request.form:
                    interviews_tech = _parse_nonnegative_int(request.form.get(interview_field))
                    if interviews_tech == "invalid":
                        errors.append(f"INTERVIEWS(TECH) for {person.full_name} must be a non-negative whole number.")
                    else:
                        submitted_metadata[(person.id, "interviews_tech")] = interviews_tech
                if incentive_field in request.form:
                    incentives = _parse_incentives(request.form.get(incentive_field))
                    if incentives == "invalid":
                        errors.append(f"INCENTIVES for {person.full_name} must be a non-negative amount with up to two decimal places.")
                    else:
                        submitted_metadata[(person.id, "incentives")] = incentives
            for day in days:
                # Sundays and public holidays are fixed, read-only cells. Any forged
                # POST value for an off-day is ignored rather than saved.
                if not is_working_date(day):
                    continue
                field = f"status_{person.id}_{day.isoformat()}"
                status = request.form.get(field, "").strip().upper()
                if status and status not in VALID_STATUSES:
                    errors.append(f"Invalid status for {person.full_name} on {day.isoformat()}.")
                submitted[(person.id, day)] = status
        if errors:
            for message in errors[:3]:
                flash(message, "danger")
            if len(errors) > 3:
                flash(f"There are {len(errors) - 3} additional invalid values.", "danger")
            return redirect(url_for("attendance.monthly", year=year, month=month))

        try:
            people_by_id = {person.id: person for person in people}
            for (person_id, field_name), value in submitted_metadata.items():
                setattr(people_by_id[person_id], field_name, value)

            existing_rows = Attendance.query.filter(
                Attendance.attendance_date >= days[0],
                Attendance.attendance_date <= days[-1],
                Attendance.person_id.in_([person.id for person in people] or [-1]),
            ).all()
            existing = {(row.person_id, row.attendance_date): row for row in existing_rows}
            for key, status in submitted.items():
                row = existing.get(key)
                if not status:
                    if row:
                        db.session.delete(row)
                    continue
                if row:
                    row.status = status
                    row.marked_by = current_user.id
                else:
                    person_id, attendance_date = key
                    db.session.add(
                        Attendance(
                            person_id=person_id,
                            attendance_date=attendance_date,
                            status=status,
                            marked_by=current_user.id,
                        )
                    )
            db.session.commit()
            flash(f"Attendance saved for {MONTH_NAMES[month - 1]} {year}.", "success")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Attendance could not be saved because of a database error. No partial changes were kept.", "danger")
        return redirect(url_for("attendance.monthly", year=year, month=month))

    attendance_rows = Attendance.query.filter(
        Attendance.attendance_date >= days[0],
        Attendance.attendance_date <= days[-1],
        Attendance.person_id.in_([person.id for person in people] or [-1]),
    ).all()
    attendance_map = {(row.person_id, row.attendance_date): row.status for row in attendance_rows}
    weekoff_count = sum(1 for day in days if day_types[day] == "weekoff")
    public_holiday_count = sum(1 for day in days if day_types[day] == "public_holiday")
    year_options = sorted(set(range(max(2026, date.today().year - 5), max(2036, date.today().year + 10) + 1)) | {year})
    return render_template(
        "attendance/monthly.html",
        year=year,
        month=month,
        month_name=MONTH_NAMES[month - 1],
        days=days,
        people=people,
        attendance_map=attendance_map,
        day_types=day_types,
        holiday_names=holiday_names,
        weekoff_count=weekoff_count,
        public_holiday_count=public_holiday_count,
        year_options=year_options,
        month_names=MONTH_NAMES,
    )
