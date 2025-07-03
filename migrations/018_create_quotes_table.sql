-- Migration 018: Create Quotes table
-- This migration creates a dedicated Quotes table for managing vendor quotes

-- Create the quotes table
CREATE TABLE takeoff.quotes (
    quote_id SERIAL PRIMARY KEY,
    cost_code_id INTEGER REFERENCES takeoff.cost_codes(cost_code_id),
    item_id INTEGER REFERENCES takeoff.items(item_id),
    plan_option_id INTEGER REFERENCES takeoff.plan_options(plan_option_id),
    vendor_id INTEGER REFERENCES takeoff.vendors(vendor_id),
    price DECIMAL(15,2),
    notes TEXT,
    effective_date DATE,
    expiration_date DATE,
    quote_file TEXT, -- Will store file path/name for uploaded quotes
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for better performance
CREATE INDEX idx_quotes_cost_code_id ON takeoff.quotes(cost_code_id);
CREATE INDEX idx_quotes_item_id ON takeoff.quotes(item_id);
CREATE INDEX idx_quotes_plan_option_id ON takeoff.quotes(plan_option_id);
CREATE INDEX idx_quotes_vendor_id ON takeoff.quotes(vendor_id);
CREATE INDEX idx_quotes_effective_date ON takeoff.quotes(effective_date);
CREATE INDEX idx_quotes_expiration_date ON takeoff.quotes(expiration_date);

-- Add comments to document the table structure
COMMENT ON TABLE takeoff.quotes IS 'Vendor quotes for construction items with pricing and plan options';
COMMENT ON COLUMN takeoff.quotes.quote_id IS 'Primary key for quotes';
COMMENT ON COLUMN takeoff.quotes.cost_code_id IS 'Foreign key to cost_codes table';
COMMENT ON COLUMN takeoff.quotes.item_id IS 'Foreign key to items table';
COMMENT ON COLUMN takeoff.quotes.plan_option_id IS 'Foreign key to plan_options table';
COMMENT ON COLUMN takeoff.quotes.vendor_id IS 'Foreign key to vendors table';
COMMENT ON COLUMN takeoff.quotes.price IS 'Quote price amount';
COMMENT ON COLUMN takeoff.quotes.notes IS 'Additional notes about the quote';
COMMENT ON COLUMN takeoff.quotes.effective_date IS 'Date when quote becomes effective';
COMMENT ON COLUMN takeoff.quotes.expiration_date IS 'Date when quote expires';
COMMENT ON COLUMN takeoff.quotes.quote_file IS 'File path/name for uploaded quote documents';
