-- Migration 012: Populate product item_type from items qty_type
-- This migration updates the products.item_type field with data from items.qty_type

-- Update products.item_type with corresponding items.qty_type data
UPDATE takeoff.products 
SET item_type = items.qty_type
FROM takeoff.items 
WHERE products.item_id = items.item_id 
AND products.item_type IS NULL;

-- Add a comment to document this data migration
-- COMMENT: Populated products.item_type field with data from items.qty_type
-- This ensures consistency between the product catalog and item definitions
