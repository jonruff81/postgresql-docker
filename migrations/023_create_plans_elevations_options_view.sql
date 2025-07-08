CREATE OR REPLACE VIEW v_plans_elevations_options AS
SELECT 
    p.plan_id,
    p.plan_name,
    p.architect,
    p.engineer,
    pe.plan_elevation_id,
    pe.elevation_name,
    pe.foundation,
    pe.heated_sf_inside_studs,
    pe.total_sf_outside_studs,
    po.plan_option_id,
    po.option_name,
    po.option_type
FROM plans p
JOIN plan_elevations pe ON p.plan_id = pe.plan_id
JOIN plan_options po ON pe.plan_elevation_id = po.plan_elevation_id;
