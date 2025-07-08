-- Add item_type column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'takeoff' 
        AND table_name = 'items' 
        AND column_name = 'item_type'
    ) THEN
        ALTER TABLE takeoff.items
        ADD COLUMN item_type varchar(50) DEFAULT 'Product';

        -- Set default values for existing records
        UPDATE takeoff.items
        SET item_type = 'Product'
        WHERE item_type IS NULL;
    END IF;
END $$;