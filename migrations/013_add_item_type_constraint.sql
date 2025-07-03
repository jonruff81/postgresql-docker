-- Migration 013: Add CHECK constraint to products.item_type field
-- This migration adds a constraint to only allow 'Quote', 'Product', or 'Attribute' values

-- Add CHECK constraint to control item_type values
ALTER TABLE takeoff.products 
ADD CONSTRAINT products_item_type_check 
CHECK (item_type IN ('Quote', 'Product', 'Attribute'));

-- Update the column comment to reflect the constraint
COMMENT ON COLUMN takeoff.products.item_type IS 'Type categorization for the product. Must be one of: Quote, Product, Attribute';

-- Add a comment to document this constraint addition
-- COMMENT: Added CHECK constraint to products.item_type to ensure data integrity
-- Only allows values: Quote, Product, Attribute
