-- Comprehensive Verification Script (Phase 3)

-- 1. Show record counts in all key tables
SELECT 'plans' as table_name, COUNT(*) FROM takeoff.plans
UNION ALL
SELECT 'plan_elevations', COUNT(*) FROM takeoff.plan_elevations
UNION ALL
SELECT 'plan_options', COUNT(*) FROM takeoff.plan_options
UNION ALL
SELECT 'jobs', COUNT(*) FROM takeoff.jobs
UNION ALL
SELECT 'takeoffs', COUNT(*) FROM takeoff.takeoffs
UNION ALL
SELECT 'vendors', COUNT(*) FROM takeoff.vendors
UNION ALL
SELECT 'vendor_pricing', COUNT(*) FROM takeoff.vendor_pricing
UNION ALL
SELECT 'items', COUNT(*) FROM takeoff.items
UNION ALL
SELECT 'formulas', COUNT(*) FROM takeoff.formulas
ORDER BY table_name;

-- 2. Verify correct plan, elevation, foundation, and option names
SELECT 
    p.plan_name,
    pe.elevation_name,
    pe.foundation,
    po.option_name,
    j.job_name
FROM takeoff.jobs j
JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
JOIN takeoff.plans p ON pe.plan_id = p.plan_id
WHERE j.is_template = TRUE
ORDER BY j.job_id;

-- 3. Show a sample of vendor pricing data
SELECT 
    v.vendor_name,
    p.product_description,
    vp.price,
    vp.unit_of_measure
FROM takeoff.vendor_pricing vp
JOIN takeoff.vendors v ON vp.vendor_id = v.vendor_id
JOIN takeoff.products p ON vp.product_id = p.product_id
LIMIT 20;

-- 4. Verify that the new schema tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'takeoff' AND table_name IN ('item_attributes', 'files', 'file_links');

-- 5. Cost per Square Foot Analysis
SELECT * FROM takeoff.v_job_cost_analysis;