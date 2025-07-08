-- Migration: Support dynamic qty_formula in takeoff view using a plpgsql function

-- 1. Create or replace function to get a plan_option column value by name
CREATE OR REPLACE FUNCTION takeoff.get_plan_option_value(plan_option_id INT, column_name TEXT)
RETURNS NUMERIC AS $$
DECLARE
    result NUMERIC;
    sql TEXT;
BEGIN
    sql := format('SELECT %I FROM takeoff.plan_options WHERE plan_option_id = $1', column_name);
    EXECUTE sql INTO result USING plan_option_id;
    RETURN result;
END;
$$ LANGUAGE plpgsql STABLE;

-- 2. Drop and recreate the view to use the function for qty_formula
DROP VIEW IF EXISTS takeoff.v_comprehensive_takeoff_analysis;
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
  (CASE
    WHEN i.qty_formula IS NOT NULL AND i.qty_formula <> '' AND i.qty_formula ~ '^[a-zA-Z_][a-zA-Z0-9_]*$'
      THEN takeoff.get_plan_option_value(po.plan_option_id, i.qty_formula)
    ELSE t.quantity
  END * t.price_factor * t.unit_price) AS extended_price,
  v.vendor_name,
  t.notes,
  j.job_name,
  t.job_number,
  t.lot_number,
  j.customer_name,
  -- t.room, -- omitted for now
  -- t.spec_name, -- omitted for now
  t.job_id,
  t.product_id,
  t.vendor_id,
  po.plan_option_id,
  i.item_id AS item_id,
  i.cost_code_id AS cost_code_id,
  i.qty_formula,
  CASE
    WHEN i.qty_formula IS NOT NULL AND i.qty_formula <> '' AND i.qty_formula ~ '^[a-zA-Z_][a-zA-Z0-9_]*$'
      THEN takeoff.get_plan_option_value(po.plan_option_id, i.qty_formula)
    ELSE t.quantity
  END AS calculated_quantity
FROM takeoff.takeoffs t
LEFT JOIN takeoff.jobs j ON t.job_id = j.job_id
LEFT JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
LEFT JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
LEFT JOIN takeoff.items i ON t.product_id = i.item_id
LEFT JOIN takeoff.cost_codes cc ON i.cost_code_id = cc.cost_code_id
LEFT JOIN takeoff.products p ON t.product_id = p.product_id
LEFT JOIN takeoff.vendors v ON t.vendor_id = v.vendor_id;
