-- Verification Queries for Construction Takeoff Data

-- 1. Show record counts in core tables
SELECT 'divisions' as table_name, COUNT(*) FROM takeoff.divisions
UNION ALL
SELECT 'communities', COUNT(*) FROM takeoff.communities
UNION ALL
SELECT 'plans', COUNT(*) FROM takeoff.plans
UNION ALL
SELECT 'plan_elevations', COUNT(*) FROM takeoff.plan_elevations
UNION ALL
SELECT 'plan_options', COUNT(*) FROM takeoff.plan_options
UNION ALL
SELECT 'jobs', COUNT(*) FROM takeoff.jobs
UNION ALL
SELECT 'takeoffs', COUNT(*) FROM takeoff.takeoffs
UNION ALL
SELECT 'items', COUNT(*) FROM takeoff.items
UNION ALL
SELECT 'products', COUNT(*) FROM takeoff.products
UNION ALL
SELECT 'vendors', COUNT(*) FROM takeoff.vendors
ORDER BY table_name;

-- 2. Show the plan and job structure that has been loaded
SELECT 
    p.plan_id,
    p.plan_name,
    pe.plan_elevation_id,
    pe.elevation_name,
    pe.foundation,
    po.plan_option_id,
    po.option_name,
    j.job_id,
    j.job_name,
    j.is_template
FROM takeoff.plans p
JOIN takeoff.plan_elevations pe ON p.plan_id = pe.plan_id
JOIN takeoff.plan_options po ON pe.plan_elevation_id = po.plan_elevation_id
JOIN takeoff.jobs j ON po.plan_option_id = j.plan_option_id
ORDER BY p.plan_name, pe.elevation_name, po.option_name;

-- 3. Show a sample of takeoff line items for the first job
SELECT 
    t.takeoff_id,
    j.job_name,
    i.item_name,
    p.product_description,
    t.quantity,
    t.unit_price,
    t.extended_price
FROM takeoff.takeoffs t
JOIN takeoff.jobs j ON t.job_id = j.job_id
JOIN takeoff.products p ON t.product_id = p.product_id
JOIN takeoff.items i ON p.item_id = i.item_id
WHERE j.job_id = (SELECT MIN(job_id) FROM takeoff.jobs)
LIMIT 20;

-- 4. Check for takeoff IDs that might be causing conflicts
-- (This will show if multiple source files share the same TakeoffIDs)
-- NOTE: This query is for analysis and won't be run by the script.
-- It's here to guide debugging.
-- SELECT takeoff_id, COUNT(*)
-- FROM takeoff.takeoffs
-- GROUP BY takeoff_id
-- HAVING COUNT(*) > 1;