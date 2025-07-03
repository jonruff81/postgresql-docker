-- Migration 022: Create comprehensive takeoff analysis view
-- Combines takeoff data with plan info, cost codes, items, vendors for complete analysis

CREATE VIEW takeoff.v_comprehensive_takeoff_analysis AS
SELECT 
    t.takeoff_id,
    pe.plan_full_name,
    po.option_name,
    cc.cost_code,
    i.item_name,
    p.item_description,
    t.quantity_source,
    t.quantity,
    t.unit_price,
    t.price_factor,
    t.unit_of_measure,
    CASE 
        WHEN t.extended_price_manual IS NOT NULL THEN t.extended_price_manual
        ELSE (t.quantity * t.unit_price * COALESCE(t.price_factor, 1))
    END AS extended_price,
    v.vendor_name,
    t.notes,
    -- Additional useful fields
    j.job_name,
    j.job_number,
    j.lot_number,
    j.customer_name,
    t.room,
    t.spec_name,
    -- IDs for filtering/joining
    t.job_id,
    t.product_id,
    t.vendor_id,
    po.plan_option_id,
    i.item_id,
    cc.cost_code_id
FROM takeoff.takeoffs t
-- Join with jobs to get plan option info
LEFT JOIN takeoff.jobs j ON t.job_id = j.job_id
LEFT JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
LEFT JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
-- Join with products and items for item details
LEFT JOIN takeoff.products p ON t.product_id = p.product_id
LEFT JOIN takeoff.items i ON p.item_id = i.item_id
LEFT JOIN takeoff.cost_codes cc ON i.cost_code_id = cc.cost_code_id
-- Join with vendors for vendor name
LEFT JOIN takeoff.vendors v ON t.vendor_id = v.vendor_id
ORDER BY pe.plan_full_name, po.option_name, cc.cost_code, i.item_name;

-- Add comment
COMMENT ON VIEW takeoff.v_comprehensive_takeoff_analysis IS 
'Comprehensive takeoff analysis view combining plan options, cost codes, items, quantities, pricing, and vendor information';
