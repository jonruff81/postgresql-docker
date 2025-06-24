-- Update schema to include all Excel fields
-- This adds missing columns to existing tables

SET search_path TO takeoff, public;

-- Add missing columns to plans table
ALTER TABLE plans ADD COLUMN IF NOT EXISTS architect VARCHAR(255);
ALTER TABLE plans ADD COLUMN IF NOT EXISTS engineer VARCHAR(255);

-- Add missing columns to plan_elevations table
ALTER TABLE plan_elevations ADD COLUMN IF NOT EXISTS plan_full_name VARCHAR(255);
ALTER TABLE plan_elevations ADD COLUMN IF NOT EXISTS version_number VARCHAR(50);
ALTER TABLE plan_elevations ADD COLUMN IF NOT EXISTS version_date VARCHAR(50);
ALTER TABLE plan_elevations ADD COLUMN IF NOT EXISTS is_current_version BOOLEAN DEFAULT TRUE;
ALTER TABLE plan_elevations ADD COLUMN IF NOT EXISTS stair_count INTEGER;

-- Add square footage columns to plan_elevations
ALTER TABLE plan_elevations ADD COLUMN IF NOT EXISTS heated_sf_inside_studs INTEGER;
ALTER TABLE plan_elevations ADD COLUMN IF NOT EXISTS heated_sf_outside_studs INTEGER;
ALTER TABLE plan_elevations ADD COLUMN IF NOT EXISTS heated_sf_outside_veneer INTEGER;
ALTER TABLE plan_elevations ADD COLUMN IF NOT EXISTS unheated_sf_inside_studs INTEGER;
ALTER TABLE plan_elevations ADD COLUMN IF NOT EXISTS unheated_sf_outside_studs INTEGER;
ALTER TABLE plan_elevations ADD COLUMN IF NOT EXISTS unheated_sf_outside_veneer INTEGER;
ALTER TABLE plan_elevations ADD COLUMN IF NOT EXISTS total_sf_inside_studs INTEGER;
ALTER TABLE plan_elevations ADD COLUMN IF NOT EXISTS total_sf_outside_studs INTEGER;
ALTER TABLE plan_elevations ADD COLUMN IF NOT EXISTS total_sf_outside_veneer INTEGER;

-- Add missing columns to plan_options table
ALTER TABLE plan_options ADD COLUMN IF NOT EXISTS option_description TEXT;
ALTER TABLE plan_options ADD COLUMN IF NOT EXISTS option_type VARCHAR(100);
ALTER TABLE plan_options ADD COLUMN IF NOT EXISTS bedroom_count INTEGER;
ALTER TABLE plan_options ADD COLUMN IF NOT EXISTS bathroom_count INTEGER;

-- Add missing columns to items table
ALTER TABLE items ADD COLUMN IF NOT EXISTS attribute_level VARCHAR(100);
ALTER TABLE items ADD COLUMN IF NOT EXISTS model VARCHAR(100);
ALTER TABLE items ADD COLUMN IF NOT EXISTS qty_formula TEXT;
ALTER TABLE items ADD COLUMN IF NOT EXISTS takeoff_type VARCHAR(100);

-- Add missing columns to takeoffs table
ALTER TABLE takeoffs ADD COLUMN IF NOT EXISTS takeoff_id_source INTEGER; -- Store original TakeoffID from Excel
ALTER TABLE takeoffs ADD COLUMN IF NOT EXISTS job_number VARCHAR(100);
ALTER TABLE takeoffs ADD COLUMN IF NOT EXISTS lot_number VARCHAR(100);
ALTER TABLE takeoffs ADD COLUMN IF NOT EXISTS customer_name VARCHAR(255);
ALTER TABLE takeoffs ADD COLUMN IF NOT EXISTS unit_of_measure VARCHAR(50);
ALTER TABLE takeoffs ADD COLUMN IF NOT EXISTS price_factor DECIMAL(10,4);
ALTER TABLE takeoffs ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE takeoffs ADD COLUMN IF NOT EXISTS room VARCHAR(255);
ALTER TABLE takeoffs ADD COLUMN IF NOT EXISTS spec_name VARCHAR(255);
ALTER TABLE takeoffs ADD COLUMN IF NOT EXISTS spec_description TEXT;
ALTER TABLE takeoffs ADD COLUMN IF NOT EXISTS spec_level VARCHAR(100);
ALTER TABLE takeoffs ADD COLUMN IF NOT EXISTS is_heated BOOLEAN;
ALTER TABLE takeoffs ADD COLUMN IF NOT EXISTS floor_level VARCHAR(100);
ALTER TABLE takeoffs ADD COLUMN IF NOT EXISTS room_type VARCHAR(100);
ALTER TABLE takeoffs ADD COLUMN IF NOT EXISTS room_sqft DECIMAL(10,2);
ALTER TABLE takeoffs ADD COLUMN IF NOT EXISTS selected_total DECIMAL(12,2);

-- Create communities table if it doesn't exist properly
CREATE TABLE IF NOT EXISTS communities (
    community_id SERIAL PRIMARY KEY,
    division_id INT REFERENCES divisions(division_id),
    community_name VARCHAR(255) NOT NULL
);

-- Add missing columns to jobs table
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_number VARCHAR(100);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS lot_number VARCHAR(100);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS customer_name VARCHAR(255);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS division_id INTEGER REFERENCES divisions(division_id);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS community_id INTEGER REFERENCES communities(community_id);

-- Update takeoffs table to use INTEGER primary key if not already
-- (Keep the existing auto-increment takeoff_id but also store the source TakeoffID)

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_takeoffs_takeoff_id_source ON takeoffs(takeoff_id_source);
CREATE INDEX IF NOT EXISTS idx_takeoffs_job_id ON takeoffs(job_id);
CREATE INDEX IF NOT EXISTS idx_plan_elevations_plan_id ON plan_elevations(plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_options_plan_elevation_id ON plan_options(plan_elevation_id);
CREATE INDEX IF NOT EXISTS idx_jobs_plan_option_id ON jobs(plan_option_id);

-- Create a view for easier data analysis
CREATE OR REPLACE VIEW v_takeoff_analysis AS
SELECT 
    t.takeoff_id,
    t.takeoff_id_source,
    t.job_number,
    p.plan_name,
    pe.elevation_name,
    pe.foundation,
    po.option_name,
    po.option_type,
    cg.cost_group_name,
    cc.cost_code,
    cc.cost_code_description,
    i.item_name,
    pr.product_description,
    t.quantity,
    t.unit_price,
    t.extended_price,
    v.vendor_name,
    pe.heated_sf_outside_studs,
    pe.total_sf_outside_studs
FROM takeoffs t
LEFT JOIN jobs j ON t.job_id = j.job_id
LEFT JOIN plan_options po ON j.plan_option_id = po.plan_option_id
LEFT JOIN plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
LEFT JOIN plans p ON pe.plan_id = p.plan_id
LEFT JOIN products pr ON t.product_id = pr.product_id
LEFT JOIN items i ON pr.item_id = i.item_id
LEFT JOIN cost_codes cc ON i.cost_code_id = cc.cost_code_id
LEFT JOIN cost_groups cg ON cc.cost_group_id = cg.cost_group_id
LEFT JOIN vendors v ON t.vendor_id = v.vendor_id;

SELECT 'Schema updated successfully with all Excel fields!' as status;
