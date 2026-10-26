-- Run this ONLY on an existing pazo_attendance database created with the older schema.
-- It safely adds the two new fields if they are not already present.
USE pazo_attendance;

SET @has_interviews_tech = (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'people' AND COLUMN_NAME = 'interviews_tech'
);
SET @sql_interviews_tech = IF(
  @has_interviews_tech = 0,
  'ALTER TABLE people ADD COLUMN interviews_tech INT NULL AFTER full_name',
  'SELECT 1'
);
PREPARE stmt_interviews_tech FROM @sql_interviews_tech;
EXECUTE stmt_interviews_tech;
DEALLOCATE PREPARE stmt_interviews_tech;

SET @has_incentives = (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'people' AND COLUMN_NAME = 'incentives'
);
SET @sql_incentives = IF(
  @has_incentives = 0,
  'ALTER TABLE people ADD COLUMN incentives DECIMAL(10,2) NULL AFTER interviews_tech',
  'SELECT 1'
);
PREPARE stmt_incentives FROM @sql_incentives;
EXECUTE stmt_incentives;
DEALLOCATE PREPARE stmt_incentives;

-- Existing records are kept. Project Name already existed in the earlier schema.
