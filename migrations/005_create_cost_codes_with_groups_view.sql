-- Migration 005: Create cost codes with groups view
-- Purpose: Join cost_codes and cost_groups tables for comprehensive cost code information
-- Created: 2025-07-02

-- Create view that joins cost codes with their associated cost groups
CREATE OR REPLACE VIEW takeoff.v_cost_codes_with_groups AS
SELECT 
    cc.cost_code_id,
    cc.cost_group_id,
    cc.cost_code,
    cc.cost_code_description,
    cg.cost_group_code,
    cg.cost_group_name
FROM takeoff.cost_codes cc
LEFT JOIN takeoff.cost_groups cg ON cc.cost_group_id = cg.cost_group_id
ORDER BY cc.cost_code;

-- Add comment to the view
COMMENT ON VIEW takeoff.v_cost_codes_with_groups IS 
'Comprehensive view of cost codes with their associated cost group information. 
Provides easy access to both cost code details and parent cost group classification.';

-- Verify the view works
SELECT 'View created successfully. Record count:' as status, COUNT(*) as total_records 
FROM takeoff.v_cost_codes_with_groups;
