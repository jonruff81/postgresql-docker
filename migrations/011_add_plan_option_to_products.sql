-- Migration 011: Add plan_option_id to products table
-- This migration adds a plan_option_id field to link products to specific plan options

-- Add plan_option_id column to products table
ALTER TABLE takeoff.products 
ADD COLUMN IF NOT EXISTS plan_option_id integer;

-- Add foreign key constraint to link to plan_options table
ALTER TABLE takeoff.products 
ADD CONSTRAINT products_plan_option_id_fkey 
FOREIGN KEY (plan_option_id) REFERENCES takeoff.plan_options(plan_option_id);

-- Add comment to document the new field
COMMENT ON COLUMN takeoff.products.plan_option_id IS 'Foreign key linking product to specific plan option';

-- Update the table comment to reflect the new relationship
COMMENT ON TABLE takeoff.products IS 'Enhanced product catalog with comprehensive product information including brand, style, materials, documentation links, and plan option associations';
