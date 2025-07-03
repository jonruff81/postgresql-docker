-- Migration 017: Fix Quote item_description to show "Quote" when no plan data available
-- This migration updates Quote records to show "Quote" when plan_option_id is not available

-- Update Quote records to show "Quote" when no plan data is available
UPDATE takeoff.products 
SET item_description = CASE 
    -- For Quote with plan data: use "Quote_" + plan_full_name + option_name
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
    
    -- For Quote without plan data: just show "Quote"
    WHEN item_type = 'Quote' THEN 'Quote'
    
    -- Keep existing values for other item types
    ELSE item_description
END
WHERE item_type = 'Quote';

-- Add a comment to document this fix
-- COMMENT: Updated Quote item_description logic
-- Quote with plan data: "Quote_" + plan_full_name + option_name
-- Quote without plan data: "Quote"
