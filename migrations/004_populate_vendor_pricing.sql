-- Populate Vendor Pricing from Existing Takeoff Data
-- This script extracts unique vendor/product/price combinations from takeoffs table
-- and creates vendor pricing records

-- Insert vendor pricing from existing takeoff data
INSERT INTO takeoff.vendor_pricing (
    vendor_id, 
    product_id, 
    price, 
    unit_of_measure,
    effective_date,
    price_type,
    notes,
    created_by
)
SELECT DISTINCT
    t.vendor_id,
    t.product_id,
    t.unit_price,
    COALESCE(t.unit_of_measure, 'EA') as unit_of_measure,
    CURRENT_DATE - INTERVAL '30 days' as effective_date, -- Assume existing prices have been effective for 30 days
    CASE 
        WHEN i.qty_type = 'Quote' THEN 'quote'
        ELSE 'standard'
    END as price_type,
    'Migrated from takeoff data on ' || CURRENT_DATE::text as notes,
    'system_migration' as created_by
FROM takeoff.takeoffs t
JOIN takeoff.products p ON t.product_id = p.product_id
JOIN takeoff.items i ON p.item_id = i.item_id
WHERE t.vendor_id IS NOT NULL 
AND t.product_id IS NOT NULL 
AND t.unit_price > 0
AND NOT EXISTS (
    -- Avoid duplicates
    SELECT 1 FROM takeoff.vendor_pricing vp 
    WHERE vp.vendor_id = t.vendor_id 
    AND vp.product_id = t.product_id 
    AND vp.price = t.unit_price
);

-- Update statistics
ANALYZE takeoff.vendor_pricing;

-- Show summary of populated data
SELECT 
    'Vendor Pricing Records Created' as summary_type,
    COUNT(*) as record_count
FROM takeoff.vendor_pricing

UNION ALL

SELECT 
    'Unique Vendor/Product Combinations',
    COUNT(DISTINCT vendor_id || '-' || product_id)
FROM takeoff.vendor_pricing

UNION ALL

SELECT 
    'Price Types',
    COUNT(DISTINCT price_type)
FROM takeoff.vendor_pricing;

-- Show sample of vendor pricing data
SELECT 
    v.vendor_name,
    p.product_description,
    vp.price,
    vp.unit_of_measure,
    vp.price_type,
    vp.effective_date
FROM takeoff.vendor_pricing vp
JOIN takeoff.vendors v ON vp.vendor_id = v.vendor_id
JOIN takeoff.products p ON vp.product_id = p.product_id
ORDER BY v.vendor_name, p.product_description
LIMIT 10;
