-- Add inventory-related fields to products table
ALTER TABLE takeoff.products
    ADD COLUMN IF NOT EXISTS image_url TEXT,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS min_stock_level INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS quantity INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS unit_of_measure VARCHAR(10) DEFAULT 'EA';

-- Create index for faster status filtering
CREATE INDEX IF NOT EXISTS idx_products_is_active ON takeoff.products(is_active);

-- Create index for inventory level queries
CREATE INDEX IF NOT EXISTS idx_products_quantity ON takeoff.products(quantity);

-- Add comments for documentation
COMMENT ON COLUMN takeoff.products.image_url IS 'URL or path to the product image';
COMMENT ON COLUMN takeoff.products.is_active IS 'Whether the product is active (true) or discontinued (false)';
COMMENT ON COLUMN takeoff.products.min_stock_level IS 'Minimum stock level before triggering low stock warning';
COMMENT ON COLUMN takeoff.products.quantity IS 'Current inventory quantity';
COMMENT ON COLUMN takeoff.products.unit_of_measure IS 'Unit of measure for inventory (EA, SF, LF, etc.)';

-- Create a function to check low stock status
CREATE OR REPLACE FUNCTION takeoff.is_low_stock(
    current_qty INTEGER,
    min_level INTEGER
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN CASE 
        WHEN current_qty IS NULL OR min_level IS NULL THEN FALSE
        WHEN current_qty <= min_level THEN TRUE
        ELSE FALSE
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE; 