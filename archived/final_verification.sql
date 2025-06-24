-- Final Verification Script for Formula-Driven Takeoffs

-- 1. Show record counts to confirm data loading
SELECT 'plans' as table_name, COUNT(*) FROM takeoff.plans
UNION ALL
SELECT 'plan_elevations', COUNT(*) FROM takeoff.plan_elevations
UNION ALL
SELECT 'plan_options', COUNT(*) FROM takeoff.plan_options
UNION ALL
SELECT 'jobs', COUNT(*) FROM takeoff.jobs
UNION ALL
SELECT 'takeoffs', COUNT(*) FROM takeoff.takeoffs
ORDER BY table_name;

-- 2. Show the loaded plan and job structure
SELECT 
    p.plan_name,
    pe.elevation_name,
    pe.foundation,
    po.option_name,
    j.job_id,
    j.job_name
FROM takeoff.plans p
JOIN takeoff.plan_elevations pe ON p.plan_id = pe.plan_id
JOIN takeoff.plan_options po ON pe.plan_elevation_id = po.plan_elevation_id
JOIN takeoff.jobs j ON po.plan_option_id = j.plan_option_id
ORDER BY p.plan_name, pe.elevation_name, po.option_name;

-- 3. Show takeoff lines with calculated quantities and their source
SELECT 
    j.job_name,
    i.item_name,
    t.quantity,
    t.quantity_source,
    t.unit_price,
    t.extended_price
FROM takeoff.takeoffs t
JOIN takeoff.jobs j ON t.job_id = j.job_id
JOIN takeoff.products p ON t.product_id = p.product_id
JOIN takeoff.items i ON p.item_id = i.item_id
WHERE t.quantity_source LIKE 'Formula:%'
LIMIT 20;

-- 4. Cost per Square Foot Analysis
-- This view calculates the total cost for each job and normalizes it by square footage
-- to allow for powerful comparison analysis.
CREATE OR REPLACE VIEW v_job_cost_analysis AS
SELECT 
    j.job_id,
    j.job_name,
    vpo.plan_name,
    vpo.elevation_name,
    vpo.foundation,
    vpo.option_type,
    vpo.heated_sf_inside_studs,
    SUM(t.extended_price) as total_cost,
    CASE 
        WHEN vpo.heated_sf_inside_studs > 0 THEN SUM(t.extended_price) / vpo.heated_sf_inside_studs
        ELSE 0 
    END as cost_per_heated_sq_ft
FROM takeoff.jobs j
JOIN takeoff.takeoffs t ON j.job_id = t.job_id
JOIN takeoff.v_plan_options vpo ON j.plan_option_id = vpo.plan_option_id
WHERE j.is_template = TRUE
GROUP BY j.job_id, vpo.plan_name, vpo.elevation_name, vpo.foundation, vpo.option_type, vpo.heated_sf_inside_studs;

-- Show the results of the cost analysis
SELECT * FROM v_job_cost_analysis;