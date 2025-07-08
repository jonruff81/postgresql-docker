-- Migration: Add calculated_quantity to qty_takeoffs view using qty_formula

-- Example: Add a calculated_quantity field to the view
-- (You may need to adjust table/column names to match your schema)

DROP VIEW IF EXISTS takeoff.v_comprehensive_takeoff_analysis;
CREATE VIEW takeoff.v_comprehensive_takeoff_analysis AS
SELECT
  t.*,
  i.qty_formula,
  CASE
    WHEN i.qty_formula = 'total_sf_outside_studs'
      THEN (
        SELECT SUM(po.total_sf_outside_studs)
        FROM takeoff.plan_options po
        WHERE po.plan_option_id = t.plan_option_id
      )
    ELSE t.quantity
  END AS calculated_quantity
FROM takeoff.qty_takeoffs_staging t
JOIN takeoff.items i ON t.item_id = i.item_id;
