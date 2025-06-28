-- Migration 009: Add item_id to vendor_quotes for quote-to-product integration
-- This allows quotes to be linked to items and automatically create products

BEGIN;

-- Add item_id column to vendor_quotes table
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'takeoff' 
        AND table_name = 'vendor_quotes' 
        AND column_name = 'item_id'
    ) THEN
        ALTER TABLE takeoff.vendor_quotes 
        ADD COLUMN item_id INTEGER;
        
        -- Add the foreign key constraint
        ALTER TABLE takeoff.vendor_quotes 
        ADD CONSTRAINT fk_vendor_quotes_item 
        FOREIGN KEY (item_id) 
        REFERENCES takeoff.items(item_id);
        
        -- Add an index for better performance
        CREATE INDEX idx_vendor_quotes_item_id 
        ON takeoff.vendor_quotes(item_id);
        
        RAISE NOTICE 'Added item_id column to vendor_quotes table';
    ELSE
        RAISE NOTICE 'item_id column already exists in vendor_quotes table';
    END IF;
END $$;

-- Create function to generate product description from quote
CREATE OR REPLACE FUNCTION generate_quote_product_description(
    p_item_id INTEGER,
    p_plan_option_id INTEGER
) RETURNS TEXT AS $$
DECLARE
    v_item_name TEXT;
    v_plan_elevation_name TEXT;
    v_option_name TEXT;
    v_product_description TEXT;
BEGIN
    -- Get item name
    SELECT item_name INTO v_item_name
    FROM takeoff.items
    WHERE item_id = p_item_id;
    
    -- Get plan elevation and option details
    SELECT 
        CONCAT(p.plan_name, ' - ', pe.elevation_name, ' ', pe.foundation) as plan_elevation_name,
        po.option_name
    INTO v_plan_elevation_name, v_option_name
    FROM takeoff.plan_options po
    JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
    JOIN takeoff.plans p ON pe.plan_id = p.plan_id
    WHERE po.plan_option_id = p_plan_option_id;
    
    -- Generate product description using the formula: item_name_plan_elevation_name_option_name
    v_product_description := CONCAT(
        COALESCE(v_item_name, 'Unknown Item'),
        '_',
        COALESCE(v_plan_elevation_name, 'Unknown Plan'),
        '_',
        COALESCE(v_option_name, 'Unknown Option')
    );
    
    RETURN v_product_description;
END;
$$ LANGUAGE plpgsql;

-- Create function to automatically create product from quote
CREATE OR REPLACE FUNCTION create_product_from_quote(
    p_quote_id INTEGER
) RETURNS INTEGER AS $$
DECLARE
    v_item_id INTEGER;
    v_plan_option_id INTEGER;
    v_vendor_id INTEGER;
    v_total_amount DECIMAL(12,2);
    v_product_description TEXT;
    v_product_id INTEGER;
    v_existing_product_id INTEGER;
BEGIN
    -- Get quote details
    SELECT item_id, plan_option_id, vendor_id, total_amount
    INTO v_item_id, v_plan_option_id, v_vendor_id, v_total_amount
    FROM takeoff.vendor_quotes
    WHERE quote_id = p_quote_id;
    
    -- Check if required fields are present
    IF v_item_id IS NULL OR v_plan_option_id IS NULL THEN
        RAISE NOTICE 'Quote % is missing item_id or plan_option_id - cannot create product', p_quote_id;
        RETURN NULL;
    END IF;
    
    -- Generate product description
    v_product_description := generate_quote_product_description(v_item_id, v_plan_option_id);
    
    -- Check if product already exists for this item with this description
    SELECT product_id INTO v_existing_product_id
    FROM takeoff.products
    WHERE item_id = v_item_id 
    AND product_description = v_product_description;
    
    IF v_existing_product_id IS NOT NULL THEN
        RAISE NOTICE 'Product already exists with ID % for quote %', v_existing_product_id, p_quote_id;
        RETURN v_existing_product_id;
    END IF;
    
    -- Create new product
    INSERT INTO takeoff.products (item_id, product_description, model)
    VALUES (v_item_id, v_product_description, 'Quote-' || p_quote_id)
    RETURNING product_id INTO v_product_id;
    
    -- Create vendor pricing record if quote has total amount and vendor
    IF v_total_amount IS NOT NULL AND v_vendor_id IS NOT NULL THEN
        INSERT INTO takeoff.vendor_pricing (vendor_id, product_id, price, unit_of_measure, is_current, is_active)
        VALUES (v_vendor_id, v_product_id, v_total_amount, 'EA', TRUE, TRUE)
        ON CONFLICT (vendor_id, product_id) DO UPDATE SET
            price = EXCLUDED.price,
            is_current = TRUE,
            is_active = TRUE;
        
        RAISE NOTICE 'Created vendor pricing for vendor % product % at price %', v_vendor_id, v_product_id, v_total_amount;
    END IF;
    
    RAISE NOTICE 'Created product % from quote % with description: %', v_product_id, p_quote_id, v_product_description;
    RETURN v_product_id;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically create products when quotes are accepted
CREATE OR REPLACE FUNCTION trigger_create_product_from_accepted_quote()
RETURNS TRIGGER AS $$
BEGIN
    -- Only create product when quote status becomes 'accepted' and has item_id
    IF NEW.status = 'accepted' AND NEW.item_id IS NOT NULL AND 
       (OLD.status IS NULL OR OLD.status != 'accepted') THEN
        
        PERFORM create_product_from_quote(NEW.quote_id);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if it exists
DROP TRIGGER IF EXISTS trigger_auto_create_product_from_quote ON takeoff.vendor_quotes;

-- Create trigger for automatic product creation
CREATE TRIGGER trigger_auto_create_product_from_quote
    AFTER INSERT OR UPDATE ON takeoff.vendor_quotes
    FOR EACH ROW
    EXECUTE FUNCTION trigger_create_product_from_accepted_quote();

-- Create view for quote-product integration analysis
CREATE OR REPLACE VIEW takeoff.v_quote_products AS
SELECT 
    vq.quote_id,
    vq.quote_number,
    v.vendor_name,
    i.item_name,
    vq.total_amount as quote_amount,
    vq.status as quote_status,
    p.product_id,
    p.product_description,
    vp.price as vendor_price,
    vp.is_current as is_current_pricing,
    pe.plan_name || ' - ' || pev.elevation_name || ' ' || pev.foundation as plan_elevation_name,
    po.option_name
FROM takeoff.vendor_quotes vq
LEFT JOIN takeoff.vendors v ON vq.vendor_id = v.vendor_id
LEFT JOIN takeoff.items i ON vq.item_id = i.item_id
LEFT JOIN takeoff.products p ON (i.item_id = p.item_id AND p.model LIKE 'Quote-%')
LEFT JOIN takeoff.vendor_pricing vp ON (v.vendor_id = vp.vendor_id AND p.product_id = vp.product_id)
LEFT JOIN takeoff.plan_options po ON vq.plan_option_id = po.plan_option_id
LEFT JOIN takeoff.plan_elevations pev ON po.plan_elevation_id = pev.plan_elevation_id
LEFT JOIN takeoff.plans pe ON pev.plan_id = pe.plan_id
ORDER BY vq.quote_id;

-- Add comments for documentation
COMMENT ON COLUMN takeoff.vendor_quotes.item_id IS 'Links quote to specific item for product creation';
COMMENT ON FUNCTION generate_quote_product_description(INTEGER, INTEGER) IS 'Generates product description using item_name_plan_elevation_name_option_name format';
COMMENT ON FUNCTION create_product_from_quote(INTEGER) IS 'Creates product and vendor pricing records from accepted quotes';
COMMENT ON VIEW takeoff.v_quote_products IS 'Shows relationship between quotes, products, and vendor pricing';

-- Grant permissions
GRANT EXECUTE ON FUNCTION generate_quote_product_description(INTEGER, INTEGER) TO "Jon";
GRANT EXECUTE ON FUNCTION create_product_from_quote(INTEGER) TO "Jon";
GRANT SELECT ON takeoff.v_quote_products TO "Jon";

COMMIT;
