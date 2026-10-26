from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    active = db.Column(db.Boolean, nullable=False, default=True)
    must_change_password = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self) -> bool:
        return bool(self.active)

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Person(db.Model):
    __tablename__ = "people"
    __table_args__ = (
        db.CheckConstraint("interviews_tech IS NULL OR interviews_tech >= 0", name="ck_people_interviews_tech_nonnegative"),
        db.CheckConstraint("incentives IS NULL OR incentives >= 0", name="ck_people_incentives_nonnegative"),
    )

    id = db.Column(db.Integer, primary_key=True)
    employee_code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(160), nullable=False, index=True)
    interviews_tech = db.Column(db.Integer, nullable=True)
    incentives = db.Column(db.Numeric(10, 2), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    project_name = db.Column(db.String(100), nullable=True)
    joined_on = db.Column(db.Date, nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    attendance_records = db.relationship(
        "Attendance", back_populates="person", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Person {self.employee_code}: {self.full_name}>"


class Attendance(db.Model):
    __tablename__ = "attendance"
    __table_args__ = (
        db.UniqueConstraint("person_id", "attendance_date", name="uq_attendance_person_date"),
        db.CheckConstraint("status IN ('P', 'A', 'L', 'H')", name="ck_attendance_status"),
        db.Index("ix_attendance_date_status", "attendance_date", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(1), nullable=False)
    marked_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    person = db.relationship("Person", back_populates="attendance_records")
    marker = db.relationship("User", foreign_keys=[marked_by])

    def __repr__(self) -> str:
        return f"<Attendance person={self.person_id} date={self.attendance_date} status={self.status}>"
