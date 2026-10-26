-- Run once against an existing PAZO database to allow half-day marks (H).
-- This preserves all existing attendance records.
USE pazo_attendance;
ALTER TABLE attendance MODIFY COLUMN status ENUM('P', 'A', 'L', 'H') NOT NULL;
