-- Migration 020: Update vendor pricing view to include quotes
-- This allows quotes to appear in the vendor pricing grid

-- Drop the existing view
DROP VIEW IF EXISTS takeoff.v_current_vendor_pricing;

-- Recreate the view to include both vendor_pricing and quotes data
CREATE VIEW takeoff.v_current_vendor_pricing AS
-- Existing vendor pricing data
SELECT 
    vp.pricing_id,
    v.vendor_name,
    v.vendor_id,
    p.item_description AS product_description,
    p.product_id,
    i.item_name,
    cc.cost_code,
    vp.price,
    vp.unit_of_measure,
    vp.effective_date,
    vp.expiration_date,
    vp.price_type,
    vp.minimum_quantity,
    vp.notes,
    vp.created_date
FROM takeoff.vendor_pricing vp
JOIN takeoff.vendors v ON vp.vendor_id = v.vendor_id
JOIN takeoff.products p ON vp.product_id = p.product_id
JOIN takeoff.items i ON p.item_id = i.item_id
LEFT JOIN takeoff.cost_codes cc ON i.cost_code_id = cc.cost_code_id
WHERE vp.is_current = true 
    AND vp.is_active = true 
    AND (vp.expiration_date IS NULL OR vp.expiration_date >= CURRENT_DATE)

UNION ALL

-- Quotes data formatted to match vendor pricing structure
SELECT 
    -q.quote_id as pricing_id,  -- Negative ID to distinguish from vendor_pricing
    v.vendor_name,
    v.vendor_id,
    CASE 
        WHEN p.item_type = 'Quote' THEN 'Quote for ' || i.item_name
        ELSE i.item_name
    END AS product_description,
    p.product_id,
    i.item_name,
    cc.cost_code,
    q.price,
    'SF' as unit_of_measure,  -- Default unit for quotes
    q.effective_date,
    q.expiration_date,
    'quote' as price_type,
    NULL as minimum_quantity,
    q.notes,
    q.created_date
FROM takeoff.quotes q
JOIN takeoff.vendors v ON q.vendor_id = v.vendor_id
JOIN takeoff.items i ON q.item_id = i.item_id
LEFT JOIN takeoff.products p ON i.item_id = p.item_id
LEFT JOIN takeoff.cost_codes cc ON q.cost_code_id = cc.cost_code_id
WHERE (q.expiration_date IS NULL OR q.expiration_date >= CURRENT_DATE);

-- Add comment
COMMENT ON VIEW takeoff.v_current_vendor_pricing IS 
'Combined view of current vendor pricing and quotes for vendor pricing grid';
