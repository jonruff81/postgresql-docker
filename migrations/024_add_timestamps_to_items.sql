-- Add timestamp columns to items table
DO $$ 
BEGIN
    -- Add created_date if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'takeoff' 
        AND table_name = 'items' 
        AND column_name = 'created_date'
    ) THEN
        ALTER TABLE takeoff.items
        ADD COLUMN created_date timestamp DEFAULT CURRENT_TIMESTAMP;

        -- Set default values for existing records
        UPDATE takeoff.items
        SET created_date = CURRENT_TIMESTAMP
        WHERE created_date IS NULL;
    END IF;

    -- Add modified_date if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'takeoff' 
        AND table_name = 'items' 
        AND column_name = 'modified_date'
    ) THEN
        ALTER TABLE takeoff.items
        ADD COLUMN modified_date timestamp DEFAULT CURRENT_TIMESTAMP;

        -- Set default values for existing records
        UPDATE takeoff.items
        SET modified_date = CURRENT_TIMESTAMP
        WHERE modified_date IS NULL;
    END IF;
END $$;