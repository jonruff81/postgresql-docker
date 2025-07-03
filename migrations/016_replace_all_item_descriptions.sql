-- Migration 016: Replace all item_descriptions with conditional formulas or blank
-- This migration replaces ALL existing item_description data with new conditional logic
-- Fields will be blank if required data is not available

-- Update ALL item_description fields based on item_type
UPDATE takeoff.products 
SET item_description = CASE 
    -- For Product: use item_name if available, otherwise blank
    WHEN item_type = 'Product' AND EXISTS (
        SELECT 1 FROM takeoff.items i WHERE i.item_id = products.item_id AND i.item_name IS NOT NULL
    ) THEN (SELECT i.item_name FROM takeoff.items i WHERE i.item_id = products.item_id)
    
    -- For Quote: use "Quote_" + plan_full_name + option_name if plan data available, otherwise blank
    WHEN item_type = 'Quote' AND plan_option_id IS NOT NULL AND EXISTS (
        SELECT 1 FROM takeoff.plan_options po 
        JOIN takeoff.plan_elevations pe ON pe.plan_elevation_id = po.plan_elevation_id
        WHERE po.plan_option_id = products.plan_option_id 
        AND pe.plan_full_name IS NOT NULL AND po.option_name IS NOT NULL
    ) THEN (
        SELECT CONCAT('Quote_', pe.plan_full_name, po.option_name)
        FROM takeoff.plan_options po
        JOIN takeoff.plan_elevations pe ON pe.plan_elevation_id = po.plan_elevation_id
        WHERE po.plan_option_id = products.plan_option_id
    )
    
    -- For Attribute: use concatenated fields if available, otherwise blank
    WHEN item_type = 'Attribute' AND (
        brand IS NOT NULL OR style IS NOT NULL OR color IS NOT NULL OR 
        finish IS NOT NULL OR sku IS NOT NULL OR size IS NOT NULL
    ) THEN CONCAT(
        COALESCE(brand, ''), '_',
        COALESCE(style, ''), '_',
        COALESCE(color, ''), '_',
        COALESCE(finish, ''), '_',
        COALESCE(sku, ''), '_',
        COALESCE(size, '')
    )
    
    -- Default: blank for all other cases
    ELSE NULL
END;

-- Add a comment to document this comprehensive replacement
-- COMMENT: Replaced ALL item_description values with conditional formulas or blank
-- Product: item_name (or blank if not available)
-- Quote: "Quote_" + plan_full_name + option_name (or blank if plan data not available)
-- Attribute: brand + "_" + style + "_" + color + "_" + finish + "_" + sku + "_" + size (or blank if no attribute data)
-- All other cases: blank
