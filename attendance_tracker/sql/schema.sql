-- PAZO Solutions Attendance Tracker
-- Run as a MySQL user that is allowed to create databases and tables.
CREATE DATABASE IF NOT EXISTS pazo_attendance
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE pazo_attendance;

CREATE TABLE IF NOT EXISTS users (
  id INT NOT NULL AUTO_INCREMENT,
  username VARCHAR(80) NOT NULL,
  email VARCHAR(254) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('admin', 'user') NOT NULL DEFAULT 'user',
  active BOOLEAN NOT NULL DEFAULT TRUE,
  must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_username (username),
  UNIQUE KEY uq_users_email (email),
  KEY ix_users_role_active (role, active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS people (
  id INT NOT NULL AUTO_INCREMENT,
  employee_code VARCHAR(40) NOT NULL,
  full_name VARCHAR(160) NOT NULL,
  interviews_tech INT NULL,
  incentives DECIMAL(10,2) NULL,
  department VARCHAR(100) NULL,
  project_name VARCHAR(100) NULL,
  joined_on DATE NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_people_employee_code (employee_code),
  KEY ix_people_full_name (full_name),
  KEY ix_people_active (active),
  CONSTRAINT ck_people_interviews_tech_nonnegative CHECK (interviews_tech IS NULL OR interviews_tech >= 0),
  CONSTRAINT ck_people_incentives_nonnegative CHECK (incentives IS NULL OR incentives >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance (
  id INT NOT NULL AUTO_INCREMENT,
  person_id INT NOT NULL,
  attendance_date DATE NOT NULL,
  status ENUM('P', 'A', 'L', 'H') NOT NULL,
  marked_by INT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_attendance_person_date (person_id, attendance_date),
  KEY ix_attendance_date (attendance_date),
  KEY ix_attendance_date_status (attendance_date, status),
  CONSTRAINT fk_attendance_person FOREIGN KEY (person_id) REFERENCES people(id) ON DELETE CASCADE,
  CONSTRAINT fk_attendance_marker FOREIGN KEY (marked_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
