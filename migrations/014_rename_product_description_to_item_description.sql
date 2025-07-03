-- Migration 014: Rename product_description to item_description
-- This migration renames the product_description column to item_description for better clarity

-- Rename the column from product_description to item_description
ALTER TABLE takeoff.products 
RENAME COLUMN product_description TO item_description;

-- Add a comment to document this column rename
-- COMMENT: Renamed product_description to item_description for improved clarity
-- This better reflects that the field describes the item rather than the product specifically
