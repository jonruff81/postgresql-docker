-- Migration 031: Update v_comprehensive_takeoff_analysis view to include item_description from takeoffs table
-- This fixes the issue where editing item_description in qty takeoffs wasn't showing because 
-- the view was using products.item_description instead of takeoffs.item_description

BEGIN;

-- Drop and recreate the comprehensive takeoff analysis view with the enhanced takeoffs table
DROP VIEW IF EXISTS takeoff.v_comprehensive_takeoff_analysis;

CREATE VIEW takeoff.v_comprehensive_takeoff_analysis AS
SELECT 
    t.takeoff_id,
    -- Plan information
    pe.plan_full_name,
    po.option_name,
    -- Cost and Item information
    cc.cost_code,
    i.item_name,
    -- Use item_description from takeoffs table (editable) as primary, fallback to products
    COALESCE(t.item_description, p.item_description, i.item_name) as item_description,
    -- Quantity and pricing
    COALESCE(t.quantity_source, 'Manual') as quantity_source,
    COALESCE(t.quantity, 0) as quantity,
    COALESCE(t.unit_price, vp_current.price, 0) as unit_price,
    COALESCE(t.price_factor, 1.0) as price_factor,
    COALESCE(t.unit_of_measure, p.unit_of_measure, i.default_unit, 'EA') as unit_of_measure,
    -- Calculated quantity using formulas where applicable
    CASE 
        WHEN i.qty_formula IS NOT NULL AND i.qty_formula != '' THEN
            -- Try to evaluate the formula, fallback to manual quantity if formula fails
            COALESCE(
                CASE 
                    WHEN i.qty_formula = 'heated_sf_outside_studs' THEN po.heated_sf_outside_studs
                    WHEN i.qty_formula = 'total_sf_outside_studs' THEN po.total_sf_outside_studs
                    WHEN i.qty_formula = 'heated_sf_outside_veneer' THEN po.heated_sf_outside_veneer
                    WHEN i.qty_formula = 'total_sf_outside_veneer' THEN po.total_sf_outside_veneer
                    WHEN i.qty_formula = 'unheated_sf_outside_studs' THEN po.unheated_sf_outside_studs
                    WHEN i.qty_formula = 'unheated_sf_outside_veneer' THEN po.unheated_sf_outside_veneer
                    ELSE COALESCE(t.quantity, 0)
                END,
                COALESCE(t.quantity, 0)
            )
        ELSE COALESCE(t.quantity, 0)
    END as calculated_quantity,
    -- Extended price calculation
    (COALESCE(t.quantity, 0) * COALESCE(t.unit_price, vp_current.price, 0) * COALESCE(t.price_factor, 1.0)) as extended_price,
    -- Vendor information
    v.vendor_name,
    -- Job information  
    COALESCE(t.job_name, j.job_name) as job_name,
    COALESCE(t.job_number, j.job_number) as job_number,
    COALESCE(t.lot_number, j.lot_number) as lot_number,
    COALESCE(t.customer_name, j.customer_name) as customer_name,
    -- Additional details
    COALESCE(t.room, '') as room,
    COALESCE(t.spec_name, '') as spec_name,
    COALESCE(t.notes, '') as notes,
    -- Foreign key references for editing
    t.job_id,
    t.product_id,
    t.vendor_id,
    t.plan_option_id,
    t.item_id,
    t.cost_code_id,
    -- Timestamps
    t.created_date,
    t.updated_date
FROM takeoff.takeoffs t
    -- Required joins for plan and option information
    LEFT JOIN takeoff.plan_options po ON t.plan_option_id = po.plan_option_id
    LEFT JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
    -- Item and cost code joins
    LEFT JOIN takeoff.items i ON t.item_id = i.item_id
    LEFT JOIN takeoff.cost_codes cc ON COALESCE(t.cost_code_id, i.cost_code_id) = cc.cost_code_id
    -- Product join for fallback data
    LEFT JOIN takeoff.products p ON t.product_id = p.product_id
    -- Current vendor pricing for price fallback
    LEFT JOIN (
        SELECT DISTINCT ON (product_id) 
            product_id, vendor_id, price, unit_of_measure
        FROM takeoff.vendor_pricing 
        WHERE is_current = true AND is_active = true
        ORDER BY product_id, created_date DESC
    ) vp_current ON t.product_id = vp_current.product_id
    -- Vendor information
    LEFT JOIN takeoff.vendors v ON COALESCE(t.vendor_id, vp_current.vendor_id) = v.vendor_id
    -- Job information
    LEFT JOIN takeoff.jobs j ON t.job_id = j.job_id
ORDER BY 
    pe.plan_full_name, 
    po.option_name, 
    cc.cost_code, 
    i.item_name,
    t.takeoff_id;

COMMIT;
