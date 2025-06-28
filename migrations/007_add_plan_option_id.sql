-- Migration to add plan_option_id column to vendor_quotes table
-- This is a simpler approach than the previous migration

BEGIN;

-- Add the plan_option_id column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'takeoff' 
        AND table_name = 'vendor_quotes' 
        AND column_name = 'plan_option_id'
    ) THEN
        ALTER TABLE takeoff.vendor_quotes 
        ADD COLUMN plan_option_id INTEGER;
        
        -- Add the foreign key constraint
        ALTER TABLE takeoff.vendor_quotes 
        ADD CONSTRAINT fk_vendor_quotes_plan_option 
        FOREIGN KEY (plan_option_id) 
        REFERENCES takeoff.plan_options(plan_option_id);
        
        -- Add an index for better performance
        CREATE INDEX idx_vendor_quotes_plan_option_id 
        ON takeoff.vendor_quotes(plan_option_id);
        
        RAISE NOTICE 'Added plan_option_id column to vendor_quotes table';
    ELSE
        RAISE NOTICE 'plan_option_id column already exists in vendor_quotes table';
    END IF;
END $$;

COMMIT;
