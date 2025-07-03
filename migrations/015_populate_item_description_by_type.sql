-- Migration 015: Populate item_description based on item_type
-- This migration sets item_description according to different formulas based on item_type

-- Update item_description for Product type: use item_name from items table
UPDATE takeoff.products 
SET item_description = items.item_name
FROM takeoff.items items
WHERE products.item_id = items.item_id 
AND products.item_type = 'Product';

-- Update item_description for Quote type: use "Quote_" + plan_full_name + option_name
UPDATE takeoff.products 
SET item_description = CONCAT('Quote_', COALESCE(pe.plan_full_name, ''), COALESCE(po.option_name, ''))
FROM takeoff.plan_options po
JOIN takeoff.plan_elevations pe ON pe.plan_elevation_id = po.plan_elevation_id
WHERE products.plan_option_id = po.plan_option_id 
AND products.item_type = 'Quote';

-- Update item_description for Attribute type: use brand_style_color_finish_sku_size
UPDATE takeoff.products 
SET item_description = CONCAT(
    COALESCE(brand, ''), '_',
    COALESCE(style, ''), '_',
    COALESCE(color, ''), '_',
    COALESCE(finish, ''), '_',
    COALESCE(sku, ''), '_',
    COALESCE(size, '')
)
WHERE item_type = 'Attribute';

-- Add a comment to document this data population
-- COMMENT: Populated item_description with conditional formulas based on item_type
-- Product: item_name
-- Quote: "Quote_" + plan_full_name + option_name  
-- Attribute: brand + "_" + style + "_" + color + "_" + finish + "_" + sku + "_" + size
