-- Fix quote associations: change plan_id to plan_option_id
-- Migration 006: Fix Quote Plan Associations

-- First, drop the foreign key constraint if it exists
ALTER TABLE takeoff.vendor_quotes DROP CONSTRAINT IF EXISTS vendor_quotes_plan_id_fkey;

-- Rename the column from plan_id to plan_option_id
ALTER TABLE takeoff.vendor_quotes RENAME COLUMN plan_id TO plan_option_id;

-- Add the correct foreign key constraint
ALTER TABLE takeoff.vendor_quotes 
ADD CONSTRAINT vendor_quotes_plan_option_id_fkey 
FOREIGN KEY (plan_option_id) REFERENCES takeoff.plan_options(plan_option_id);

-- Update any existing sample data to reference actual plan_option_ids
UPDATE takeoff.vendor_quotes 
SET plan_option_id = (
    SELECT plan_option_id 
    FROM takeoff.plan_options 
    LIMIT 1
)
WHERE plan_option_id IS NOT NULL;

COMMIT;
