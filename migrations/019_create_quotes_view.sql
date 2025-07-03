-- Migration 019: Create Quotes view for AG-Grid
-- This migration creates a view that joins quotes with related tables for the UI

-- Create the quotes view with all necessary data for AG-Grid
CREATE OR REPLACE VIEW takeoff.v_quotes AS
SELECT 
    q.quote_id,
    q.cost_code_id,
    cc.cost_code,
    cc.cost_code_description,
    q.item_id,
    i.item_name,
    CASE 
        WHEN p.item_type = 'Product' THEN i.item_name
        WHEN p.item_type = 'Quote' AND q.plan_option_id IS NOT NULL THEN 
            CONCAT('Quote_', pe.plan_full_name, po.option_name)
        WHEN p.item_type = 'Quote' THEN 'Quote'
        ELSE i.item_name
    END as item_description,
    q.plan_option_id,
    CASE 
        WHEN q.plan_option_id IS NOT NULL THEN 
            CONCAT(pe.plan_full_name, '-', po.option_name)
        ELSE NULL 
    END as plan_option_display,
    q.vendor_id,
    v.vendor_name,
    q.price,
    q.notes,
    q.effective_date,
    q.expiration_date,
    q.quote_file,
    q.created_date,
    q.updated_date
FROM takeoff.quotes q
LEFT JOIN takeoff.cost_codes cc ON q.cost_code_id = cc.cost_code_id
LEFT JOIN takeoff.items i ON q.item_id = i.item_id
LEFT JOIN takeoff.products p ON i.item_id = p.item_id
LEFT JOIN takeoff.plan_options po ON q.plan_option_id = po.plan_option_id
LEFT JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
LEFT JOIN takeoff.vendors v ON q.vendor_id = v.vendor_id;

-- Add comment to document the view
COMMENT ON VIEW takeoff.v_quotes IS 'Comprehensive view of quotes with related lookup data for AG-Grid interface';
