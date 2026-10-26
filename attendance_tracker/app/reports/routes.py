import calendar
import csv
from datetime import date
from io import BytesIO, StringIO

from flask import abort, flash, make_response, render_template, request
from flask_login import login_required
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from ..models import Attendance, Person
from ..holiday_calendar import is_working_date
from . import bp

MONTHS = list(calendar.month_name)[1:]


def _period():
    now = date.today()
    try:
        year = int(request.args.get("year", now.year))
        month = int(request.args.get("month", now.month))
        if not 2000 <= year <= 9999 or not 1 <= month <= 12:
            raise ValueError
    except (TypeError, ValueError):
        flash("Invalid reporting period. Showing the current month.", "warning")
        return now.year, now.month
    return year, month


def _people_with_month_totals(year, month):
    last_day = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last_day)
    rows = Attendance.query.filter(Attendance.attendance_date >= start, Attendance.attendance_date <= end).all()
    totals = {}
    for row in rows:
        if not is_working_date(row.attendance_date):
            continue
        item = totals.setdefault(row.person_id, {"P": 0, "A": 0, "L": 0, "H": 0})
        item[row.status] += 1
    people = Person.query.order_by(Person.active.desc(), Person.id.asc()).all()
    result = []
    for person in people:
        value = totals.get(person.id, {"P": 0, "A": 0, "L": 0, "H": 0})
        result.append({"person": person, "present": value["P"], "absent": value["A"], "leave": value["L"], "half_day": value["H"], "marked": sum(value.values())})
    totals_all = {
        "present": sum(item["present"] for item in result),
        "absent": sum(item["absent"] for item in result),
        "leave": sum(item["leave"] for item in result),
        "half_day": sum(item["half_day"] for item in result),
        "marked": sum(item["marked"] for item in result),
    }
    return result, totals_all


def _yearly_data(year):
    rows = Attendance.query.filter(
        Attendance.attendance_date >= date(year, 1, 1),
        Attendance.attendance_date <= date(year, 12, 31),
    ).all()
    by_person = {}
    for row in rows:
        if not is_working_date(row.attendance_date):
            continue
        item = by_person.setdefault(row.person_id, {m: {"P": 0, "A": 0, "L": 0, "H": 0} for m in range(1, 13)})
        item[row.attendance_date.month][row.status] += 1
    people = Person.query.order_by(Person.active.desc(), Person.id.asc()).all()
    result = []
    for person in people:
        months = by_person.get(person.id, {m: {"P": 0, "A": 0, "L": 0, "H": 0} for m in range(1, 13)})
        totals = {status: sum(months[m][status] for m in range(1, 13)) for status in ("P", "A", "L", "H")}
        result.append({"person": person, "months": months, "present": totals["P"], "absent": totals["A"], "leave": totals["L"], "half_day": totals["H"], "marked": sum(totals.values())})
    return result


def _csv_response(filename, headers, rows):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        # Avoid spreadsheet-formula execution when user-supplied text is opened in Excel.
        safe_row = []
        for value in row:
            if isinstance(value, str) and value[:1] in {"=", "+", "-", "@", "\t", "\r"}:
                value = "'" + value
            safe_row.append(value)
        writer.writerow(safe_row)
    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _pdf_response(filename, title, subtitle, headers, rows):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=title,
        author="PAZO Solutions",
    )
    styles = getSampleStyleSheet()
    heading = ParagraphStyle("ReportTitle", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#243f87"), spaceAfter=5)
    story = [Paragraph(title, heading), Paragraph(subtitle, styles["Normal"]), Spacer(1, 7 * mm)]
    safe_rows = [[str(value) for value in headers]] + [[str(value) for value in row] for row in rows]
    table = LongTable(safe_rows, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3edf9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#172b55")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)
    doc.build(story)
    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@bp.route("/monthly")
@login_required
def monthly():
    year, month = _period()
    records, totals = _people_with_month_totals(year, month)
    year_options = sorted(set(range(max(2026, date.today().year - 5), max(2036, date.today().year + 10) + 1)) | {year})
    return render_template("reports/monthly.html", year=year, month=month, month_name=MONTHS[month - 1], month_names=MONTHS, year_options=year_options, records=records, totals=totals)


@bp.route("/yearly")
@login_required
def yearly():
    now = date.today()
    try:
        year = int(request.args.get("year", now.year))
        if not 2000 <= year <= 9999:
            raise ValueError
    except (TypeError, ValueError):
        year = now.year
        flash("Invalid reporting year. Showing the current year.", "warning")
    records = _yearly_data(year)
    year_options = sorted(set(range(max(2026, date.today().year - 5), max(2036, date.today().year + 10) + 1)) | {year})
    totals = {
        "present": sum(row["present"] for row in records),
        "absent": sum(row["absent"] for row in records),
        "leave": sum(row["leave"] for row in records),
        "half_day": sum(row["half_day"] for row in records),
        "marked": sum(row["marked"] for row in records),
    }
    return render_template("reports/yearly.html", year=year, year_options=year_options, records=records, totals=totals)


@bp.route("/monthly.csv")
@login_required
def monthly_csv():
    year, month = _period()
    records, _totals = _people_with_month_totals(year, month)
    rows = []
    for serial, record in enumerate(records, start=1):
        person = record["person"]
        rows.append([serial, person.full_name, person.interviews_tech if person.interviews_tech is not None else "", str(person.incentives) if person.incentives is not None else "", person.project_name or "", person.employee_code, person.department or "", record["present"], record["absent"], record["half_day"], record["leave"], record["marked"], "Active" if person.active else "Inactive"])
    return _csv_response(f"attendance-{year}-{month:02d}.csv", ["Sr. No.", "Name of Employee", "INTERVIEWS(TECH)", "INCENTIVES", "Project Name", "Employee Code", "Department", "Present", "Absent", "Half Days", "Leave", "Days Marked", "Status"], rows)


@bp.route("/yearly.csv")
@login_required
def yearly_csv():
    now = date.today()
    try:
        year = int(request.args.get("year", now.year))
        if not 2000 <= year <= 9999:
            raise ValueError
    except (TypeError, ValueError):
        abort(400, description="Year must be between 2000 and 9999.")
    records = _yearly_data(year)
    headers = ["Sr. No.", "Name of Employee", "INTERVIEWS(TECH)", "INCENTIVES", "Project Name", "Employee Code"] + [f"{MONTHS[m - 1]} {s}" for m in range(1, 13) for s in ("Present", "Absent", "Half Day", "Leave")] + ["Year Present", "Year Absent", "Year Half Days", "Year Leave", "Days Marked", "Status"]
    rows = []
    for serial, record in enumerate(records, start=1):
        person = record["person"]
        row = [serial, person.full_name, person.interviews_tech if person.interviews_tech is not None else "", str(person.incentives) if person.incentives is not None else "", person.project_name or "", person.employee_code]
        for m in range(1, 13):
            row.extend([record["months"][m]["P"], record["months"][m]["A"], record["months"][m]["H"], record["months"][m]["L"]])
        row.extend([record["present"], record["absent"], record["half_day"], record["leave"], record["marked"], "Active" if person.active else "Inactive"])
        rows.append(row)
    return _csv_response(f"attendance-{year}-yearly.csv", headers, rows)


@bp.route("/monthly.pdf")
@login_required
def monthly_pdf():
    year, month = _period()
    records, _totals = _people_with_month_totals(year, month)
    rows = []
    for serial, record in enumerate(records, start=1):
        person = record["person"]
        rows.append([serial, person.full_name, person.interviews_tech if person.interviews_tech is not None else "—", f"INR {person.incentives:,.2f}" if person.incentives is not None else "—", person.project_name or "—", person.employee_code, record["present"], record["absent"], record["half_day"], record["leave"], record["marked"], "Active" if person.active else "Inactive"])
    return _pdf_response(f"attendance-{year}-{month:02d}.pdf", f"Monthly Attendance Report — {MONTHS[month - 1]} {year}", "PAZO Solutions · Attendance summary (blank dates are not included in totals)", ["Sr. No.", "Employee", "Tech interviews", "Incentives", "Project", "Code", "Present", "Absent", "Half days", "Leave", "Marked", "Status"], rows)


@bp.route("/yearly.pdf")
@login_required
def yearly_pdf():
    now = date.today()
    try:
        year = int(request.args.get("year", now.year))
        if not 2000 <= year <= 9999:
            raise ValueError
    except (TypeError, ValueError):
        abort(400, description="Year must be between 2000 and 9999.")
    records = _yearly_data(year)
    rows = []
    for serial, record in enumerate(records, start=1):
        person = record["person"]
        rows.append([serial, person.full_name, person.interviews_tech if person.interviews_tech is not None else "—", f"INR {person.incentives:,.2f}" if person.incentives is not None else "—", person.project_name or "—", person.employee_code, record["present"], record["absent"], record["half_day"], record["leave"], record["marked"], "Active" if person.active else "Inactive"])
    return _pdf_response(f"attendance-{year}-yearly.pdf", f"Yearly Attendance Report — {year}", "PAZO Solutions · Annual totals across all 12 months", ["Sr. No.", "Employee", "Tech interviews", "Incentives", "Project", "Code", "Present", "Absent", "Half days", "Leave", "Marked", "Status"], rows)
