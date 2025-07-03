-- Migration 006: Add cost_code column to v_current_vendor_pricing view
-- This migration updates the view to include the cost_code from the cost_codes table

-- Drop the existing view
DROP VIEW IF EXISTS takeoff.v_current_vendor_pricing;

-- Recreate the view with cost_code column
CREATE VIEW takeoff.v_current_vendor_pricing AS
SELECT 
    vp.pricing_id,
    v.vendor_name,
    v.vendor_id,
    p.product_description,
    p.product_id,
    i.item_name,
    cc.cost_code,  -- Added cost_code column
    vp.price,
    vp.unit_of_measure,
    vp.effective_date,
    vp.expiration_date,
    vp.price_type,
    vp.minimum_quantity,
    vp.notes,
    vp.created_date
FROM takeoff.vendor_pricing vp
    JOIN takeoff.vendors v ON vp.vendor_id = v.vendor_id
    JOIN takeoff.products p ON vp.product_id = p.product_id
    JOIN takeoff.items i ON p.item_id = i.item_id
    LEFT JOIN takeoff.cost_codes cc ON i.cost_code_id = cc.cost_code_id  -- Added JOIN to cost_codes
WHERE vp.is_current = true 
    AND vp.is_active = true 
    AND (vp.expiration_date IS NULL OR vp.expiration_date >= CURRENT_DATE);

-- Add a comment to the view
COMMENT ON VIEW takeoff.v_current_vendor_pricing IS 'Current active vendor pricing with cost codes. Includes cost_code from the related cost_codes table.';
