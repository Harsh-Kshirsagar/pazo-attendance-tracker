# PAZO Attendance Tracker

A responsive Flask web application for recording employee attendance and reviewing monthly/yearly summaries. The layout combines the wide, date-by-date attendance sheet from the provided PAZO spreadsheet with the clean summary cards and navigation style of the fee-tracker reference photo.

## Features

- Login/logout with Werkzeug PBKDF2-SHA256 password hashes, CSRF protection, and secure session-cookie defaults.
- Administrator and regular-user roles. Administrators manage accounts and employee/person records; regular users can update attendance and view reports but cannot open user/person management.
- Dynamic calendar grid for any month/year from 2000 through 9999; dates are generated from the selected year and month rather than hardcoded to 2026.
- Statuses: `P` Present, `A` Absent, `L` Leave, or blank (not marked). Per-person counts and daily/monthly totals update in the browser and are saved to MySQL.
- Monthly and annual reports with CSV and PDF exports.
- Employee code, name, INTERVIEWS(TECH), INCENTIVES (INR), project name, department, join date, search, deactivate/reactivate, and retained attendance history. Sr. No. is generated from the visible row order.
- Responsive Bootstrap layout, sticky employee columns, Sunday/weekoff and public-holiday shading, and mobile navigation.

## Project structure

```text
attendance_tracker/
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   ├── models.py
│   ├── decorators.py
│   ├── auth/routes.py
│   ├── main/routes.py
│   ├── attendance/routes.py
│   ├── people/routes.py
│   ├── users/routes.py
│   ├── reports/routes.py
│   ├── templates/             # Jinja pages
│   └── static/                # CSS and JavaScript
├── sql/
│   ├── schema.sql
│   ├── migrate_employee_metadata.sql
│   └── seed.sql
├── tests/test_smoke.py
├── config.py
├── run.py
├── requirements.txt
├── .env.example
└── README.md
```

## Requirements

- Python 3.10 or newer.
- MySQL 8.0+ (or a compatible MySQL server) and access to create the database/tables.
- A modern browser.

## Windows setup (PowerShell)

1. **Extract this project folder** to a convenient location and open it in VS Code (`File → Open Folder`). Open Terminal → New Terminal in that folder.

2. **Create and activate a virtual environment:**

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

   If PowerShell blocks activation, either allow the script for the current terminal with `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again, or use Command Prompt and run `.venv\Scripts\activate.bat`.

3. **Create the MySQL database and tables.** Start MySQL first. Option A: open MySQL Workbench, open `sql/schema.sql`, and execute the full script. Option B: from a terminal where the MySQL client is on `PATH`, run:

   ```powershell
   cmd /c "mysql -u root -p < sql\schema.sql"
   ```

   The script creates `pazo_attendance`, `users`, `people`, and `attendance`. The `people` table includes `interviews_tech` (integer) and `incentives` (DECIMAL(10,2)); `project_name` is retained from the existing schema.

   If upgrading an older installed database, open and execute `sql/migrate_employee_metadata.sql` in MySQL Workbench once after the `people` table exists. This migration is safe to re-run. Also execute `sql/migrate_add_halfday_status.sql` once to allow the additional `H` (half day) status in an older attendance table. Do not run migrations before creating the schema.

4. **Create an application database user** in MySQL Workbench or as a MySQL administrator. Example (replace the password with a strong unique value):

   ```sql
   CREATE USER IF NOT EXISTS 'attendance_app'@'localhost' IDENTIFIED BY 'REPLACE_WITH_A_STRONG_PASSWORD';
   GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
     ON pazo_attendance.* TO 'attendance_app'@'localhost';
   FLUSH PRIVILEGES;
   ```

   If your app connects over TCP as `127.0.0.1`, configure the MySQL account host to match your server policy (commonly `localhost` or `127.0.0.1`). Avoid using the MySQL root account for the web app.

5. **Configure the app.** Copy the sample environment file and edit the database values:

   ```powershell
   Copy-Item .env.example .env
   ```

   In `.env`, set `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`, and a strong `SECRET_KEY`. Generate a key with:

   ```powershell
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

   Set `FLASK_DEBUG=1` only for local development. For production, set `APP_ENV=production`, use a strong `SECRET_KEY`, configure HTTPS, and keep `SESSION_COOKIE_SECURE=1`.

6. **Load demo data and the default admin.** If you want the included sample employees and known starter account, run `sql/seed.sql` after `sql/schema.sql`:

   ```powershell
   cmd /c "mysql -u root -p < sql\seed.sql"
   ```

   Starter credentials: username `admin`, password `ChangeMe@2026!`. The app forces the starter admin to change this password before accessing protected pages. The included seed contains the 15 PAZO employees and project names visible in the supplied screenshot. Edit the interview counts and incentive amounts in People Management or directly in the two highlighted columns on the monthly attendance grid (click Save attendance to save changes). Review the imported details before production use. Accounts created by an administrator are also prompted to change the initial password at first sign-in.

   For a custom admin account instead, skip `sql/seed.sql` and after step 5 run:

   ```powershell
   $env:ADMIN_USERNAME = "admin"
   $env:ADMIN_EMAIL = "admin@your-company.example"
   $env:ADMIN_PASSWORD = "a-unique-password-with-12-chars-minimum"
   flask --app run.py init-db
   flask --app run.py seed-admin
   ```

   `seed-admin` does not overwrite an existing user. The app can also create missing tables through `flask --app run.py init-db`; using `schema.sql` is recommended because it includes explicit MySQL indexes and foreign-key definitions.

7. **Run the server:**

   ```powershell
   flask --app run.py run --debug
   ```

   Open `http://127.0.0.1:5000` in your browser and sign in. Stop the development server with **Ctrl+C** in its terminal.

## macOS/Linux setup

The same steps apply, replacing virtual-environment activation with `source .venv/bin/activate` and running the SQL file with `mysql -u root -p < sql/schema.sql`. Copy `.env.example` to `.env`, edit the values, load seed data, and launch with `flask --app run.py run --debug`.

## Optional CLI commands

```bash
flask --app run.py init-db       # Create tables from ORM models
flask --app run.py seed-admin    # Create admin using ADMIN_* environment variables if no matching username/email exists
flask --app run.py create-admin  # Prompt for a new administrator
```

## Reports and exports

- Attendance grid: `/attendance/monthly`
- Monthly report: `/reports/monthly`
- Yearly report: `/reports/yearly`
- CSV/PDF downloads are provided on each report page.

Exports contain summary counts. The yearly CSV also contains each month's P/A/H/L counts. Blank dates are intentionally not treated as absences, because there is no mark to support that assumption.

## Roles

- **Admin:** manage people, create/edit/deactivate accounts, assign roles, update attendance, view and export reports.
- **Regular user:** view the dashboard, update attendance, view and export reports, and change their own password. They cannot access the people or user-management pages.

The app prevents an administrator from demoting/deactivating the last active administrator through the UI. Deactivation is used instead of deleting people/users so records can be retained.

## Database notes

- `users`: account identity, password hash, role, activation state, forced password-change flag, timestamps.
- `people`: employee identity, technical interview count, incentive amount in INR, department/project, join date, activation state. `interviews_tech` is nullable integer; `incentives` is nullable DECIMAL(10,2).
- `attendance`: one row per person/date with `P` (present), `A` (absent), `L` (leave), or `H` (half day); a unique key prevents duplicate marks for the same person on the same date.
- `attendance.marked_by` identifies the account that last saved a mark; it becomes `NULL` if that account is deleted.

All SQL operations use SQLAlchemy ORM queries or parameters. Passwords are never stored in plaintext. CSRF tokens protect form submissions.

## Production deployment checklist

This is a complete application foundation, but a production rollout still needs environment-specific deployment configuration: a production WSGI server (such as Waitress on Windows or Gunicorn on Linux), HTTPS/reverse proxy, backup/restore testing, database least-privilege review, monitoring/log retention, and an agreed policy for attendance corrections and data retention. Do not expose Flask's development server to the public internet.

## Visual interpretation and assumptions

- The monthly sheet includes generated Sr. No., Name of Employee, INTERVIEWS(TECH), INCENTIVES, and Project Name before one column per calendar day. Employee code is retained in employee management and exports. Technical interviews are whole-number counts; incentives are rupee amounts to two decimal places. Administrators can edit both values directly in the monthly attendance grid and save them with the Save attendance button; regular users see the values but cannot edit them. Sticky serial/name columns keep the wide table easier to navigate.
- The fee-tracker reference maps to the dashboard: four high-level metric cards, quick actions, clean whitespace, blue/green PAZO accents, and a simple top navigation.
- Working-day statuses are `P` (present), `A` (absent), `L` (leave), and `H` (half day). Sundays and public holidays are locked off-days rather than editable attendance cells.
- Monthly/yearly counts include explicit attendance marks on working days only. Sundays, national/public holidays, and configured PAZO holidays are excluded from attendance-mark totals.
- The app uses Flask + SQLAlchemy rather than Django to keep the codebase lightweight while retaining route separation, ORM safety, CSRF protection, password hashing, and login management.


## Weekly offs, India public holidays, and half-day marks

- Every Sunday is displayed as `WEEKOFF` and cannot be marked P/A/L/H.
- India-wide public holidays are generated by the `holidays` Python package for the selected year and shown as locked `PH` cells. Their names appear in the date-cell tooltip. The holiday list can differ by state and employer; optional `HOLIDAY_SUBDIV=MH` in `.env` includes Maharashtra-specific holidays as well.
- Working days support `P` (present), `A` (absent), `L` (leave), and `H` (half day).
- When upgrading an existing database, execute `sql/migrate_add_halfday_status.sql` in MySQL Workbench once to add `H` to the attendance status enum. No employee or attendance rows are deleted.
- The built-in country calendar follows the installed holiday-library data. Company-specific dates can be added to `app/custom_holidays.json` in `YYYY-MM-DD` format. The provided reference marks 31-Oct-2026 as PH, so that PAZO-specific override is included. Company-specific dates should be confirmed against PAZO’s approved annual holiday list.
