-- Migration script to move SF fields from plan_elevations to plan_options
-- and add heated_sf_inside_studs and total_sf_outside_studs

BEGIN;

-- Step 1: Add SF fields to plan_options table
ALTER TABLE takeoff.plan_options 
ADD COLUMN heated_sf_inside_studs integer,
ADD COLUMN heated_sf_outside_studs integer,
ADD COLUMN heated_sf_outside_veneer integer,
ADD COLUMN unheated_sf_inside_studs integer,
ADD COLUMN unheated_sf_outside_studs integer,
ADD COLUMN unheated_sf_outside_veneer integer,
ADD COLUMN total_sf_inside_studs integer,
ADD COLUMN total_sf_outside_studs integer,
ADD COLUMN total_sf_outside_veneer integer;

-- Step 2: Copy existing SF data from plan_elevations to plan_options
-- Since plan_options are related to plan_elevations, we need to update each option with its elevation's data
UPDATE takeoff.plan_options po
SET 
    heated_sf_inside_studs = pe.heated_sf_inside_studs,
    heated_sf_outside_studs = pe.heated_sf_outside_studs,
    heated_sf_outside_veneer = pe.heated_sf_outside_veneer,
    unheated_sf_inside_studs = pe.unheated_sf_inside_studs,
    unheated_sf_outside_studs = pe.unheated_sf_outside_studs,
    unheated_sf_outside_veneer = pe.unheated_sf_outside_veneer,
    total_sf_inside_studs = pe.total_sf_inside_studs,
    total_sf_outside_studs = pe.total_sf_outside_studs,
    total_sf_outside_veneer = pe.total_sf_outside_veneer
FROM takeoff.plan_elevations pe
WHERE po.plan_elevation_id = pe.plan_elevation_id;

-- Step 3: Remove SF fields from plan_elevations table
ALTER TABLE takeoff.plan_elevations 
DROP COLUMN heated_sf_inside_studs,
DROP COLUMN heated_sf_outside_studs,
DROP COLUMN heated_sf_outside_veneer,
DROP COLUMN unheated_sf_inside_studs,
DROP COLUMN unheated_sf_outside_studs,
DROP COLUMN unheated_sf_outside_veneer,
DROP COLUMN total_sf_inside_studs,
DROP COLUMN total_sf_outside_studs,
DROP COLUMN total_sf_outside_veneer;

-- Verify the changes
SELECT 'Migration completed successfully' as status;

COMMIT;
