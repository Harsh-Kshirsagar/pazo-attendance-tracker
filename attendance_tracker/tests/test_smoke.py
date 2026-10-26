from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.extensions import db
from app.models import Attendance, Person, User
from config import Config


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key-that-is-only-for-tests"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        admin = User(username="admin", email="admin@example.test", role="admin", active=True)
        admin.set_password("AdminPassword!123")
        regular = User(username="staff", email="staff@example.test", role="user", active=True)
        regular.set_password("StaffPassword!123")
        person = Person(employee_code="EMP001", full_name="Sample Employee", interviews_tech=3, incentives=Decimal("1250.00"), project_name="DEA", active=True)
        db.session.add_all([admin, regular, person])
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, username, password):
    return client.post("/auth/login", data={"identity": username, "password": password}, follow_redirects=False)


def test_regular_user_cannot_open_admin_pages(client):
    result = login(client, "staff", "StaffPassword!123")
    assert result.status_code == 302
    assert client.get("/users/").status_code == 403
    assert client.get("/people/").status_code == 403
    assert client.get("/attendance/monthly?year=2026&month=10").status_code == 200


def test_attendance_is_saved_and_monthly_report_counts_marks(app, client):
    login(client, "admin", "AdminPassword!123")
    person = None
    with app.app_context():
        person = Person.query.filter_by(employee_code="EMP001").first()
        person_id = person.id
    result = client.post(
        "/attendance/monthly?year=2026&month=10",
        data={
            "year": "2026",
            "month": "10",
            f"status_{person_id}_2026-10-01": "P",
            f"status_{person_id}_2026-10-05": "A",
            f"status_{person_id}_2026-10-06": "L",
            f"status_{person_id}_2026-10-07": "H",
        },
        follow_redirects=False,
    )
    assert result.status_code == 302
    with app.app_context():
        rows = Attendance.query.filter_by(person_id=person_id).all()
        assert {row.status for row in rows} == {"P", "A", "L", "H"}
    report = client.get("/reports/monthly?year=2026&month=10")
    assert report.status_code == 200
    assert b"Monthly attendance report" in report.data
    assert b"EMP001" in report.data


def test_future_year_period_renders(client):
    login(client, "admin", "AdminPassword!123")
    result = client.get("/attendance/monthly?year=2040&month=2")
    assert result.status_code == 200
    assert b"2040" in result.data


def test_employee_metadata_is_visible_and_persisted(app, client):
    login(client, "admin", "AdminPassword!123")
    page = client.get("/people/")
    assert page.status_code == 200
    assert b"INTERVIEWS(TECH)" in page.data
    assert b"INCENTIVES" in page.data
    with app.app_context():
        person = Person.query.filter_by(employee_code="EMP001").first()
        assert person.interviews_tech == 3
        assert person.incentives == Decimal("1250.00")


def test_sundays_and_public_holidays_are_read_only(app, client):
    login(client, "admin", "AdminPassword!123")
    with app.app_context():
        person_id = Person.query.filter_by(employee_code="EMP001").first().id
    page = client.get("/attendance/monthly?year=2026&month=10")
    assert page.status_code == 200
    assert b"WEEKOFF" in page.data
    assert b"PAZO custom holiday" in page.data
    assert f"status_{person_id}_2026-10-04".encode() not in page.data
    assert f"status_{person_id}_2026-10-31".encode() not in page.data

    # Even a forged POST cannot save a mark on a Sunday or public holiday.
    client.post(
        "/attendance/monthly?year=2026&month=10",
        data={
            "year": "2026",
            "month": "10",
            f"status_{person_id}_2026-10-04": "P",
            f"status_{person_id}_2026-10-31": "A",
            f"status_{person_id}_2026-10-05": "P",
        },
        follow_redirects=False,
    )
    with app.app_context():
        rows = Attendance.query.filter(Attendance.person_id == person_id).all()
        saved_dates = {row.attendance_date for row in rows}
        assert date(2026, 10, 4) not in saved_dates
        assert date(2026, 10, 31) not in saved_dates
        assert date(2026, 10, 5) in saved_dates


def test_admin_can_edit_interviews_and_incentives_from_attendance_grid(app, client):
    login(client, "admin", "AdminPassword!123")
    with app.app_context():
        person = Person.query.filter_by(employee_code="EMP001").first()
        person_id = person.id

    page = client.get("/attendance/monthly?year=2026&month=10")
    assert page.status_code == 200
    assert f'name="interviews_tech_{person_id}"'.encode() in page.data
    assert f'name="incentives_{person_id}"'.encode() in page.data

    result = client.post(
        "/attendance/monthly?year=2026&month=10",
        data={
            "year": "2026",
            "month": "10",
            f"interviews_tech_{person_id}": "12",
            f"incentives_{person_id}": "2750.50",
        },
        follow_redirects=False,
    )
    assert result.status_code == 302
    with app.app_context():
        person = Person.query.filter_by(employee_code="EMP001").first()
        assert person.interviews_tech == 12
        assert person.incentives == Decimal("2750.50")


def test_regular_user_cannot_change_employee_metadata_from_attendance_grid(app, client):
    login(client, "staff", "StaffPassword!123")
    with app.app_context():
        person = Person.query.filter_by(employee_code="EMP001").first()
        person_id = person.id

    page = client.get("/attendance/monthly?year=2026&month=10")
    assert page.status_code == 200
    assert f'name="interviews_tech_{person_id}"'.encode() not in page.data

    client.post(
        "/attendance/monthly?year=2026&month=10",
        data={
            "year": "2026",
            "month": "10",
            f"interviews_tech_{person_id}": "999",
            f"incentives_{person_id}": "9999.99",
        },
        follow_redirects=False,
    )
    with app.app_context():
        person = Person.query.filter_by(employee_code="EMP001").first()
        assert person.interviews_tech == 3
        assert person.incentives == Decimal("1250.00")
