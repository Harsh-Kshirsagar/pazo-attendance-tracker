from datetime import date

from flask import render_template
from flask_login import login_required

from ..models import Attendance, Person
from ..holiday_calendar import is_working_date
from . import bp


@bp.route("/")
@login_required
def dashboard():
    today = date.today()
    month_start = today.replace(day=1)
    active_people = Person.query.filter_by(active=True).count()
    month_rows = Attendance.query.filter(
        Attendance.attendance_date >= month_start,
        Attendance.attendance_date <= today,
    ).all()
    month_rows = [row for row in month_rows if is_working_date(row.attendance_date)]
    month_counts = {"P": 0, "A": 0, "L": 0, "H": 0}
    for row in month_rows:
        month_counts[row.status] += 1
    today_rows = [row for row in Attendance.query.filter_by(attendance_date=today).all() if is_working_date(row.attendance_date)]
    today_counts = {"P": 0, "A": 0, "L": 0, "H": 0}
    for row in today_rows:
        today_counts[row.status] += 1
    return render_template(
        "dashboard.html",
        today=today,
        active_people=active_people,
        month_counts=month_counts,
        today_counts=today_counts,
        today_marked=len(today_rows),
    )
