-- Create vendor quotes and related tables for quote management system
-- Migration 005: Quote Management Tables

-- Create vendor_quotes table
CREATE TABLE IF NOT EXISTS takeoff.vendor_quotes (
    quote_id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL REFERENCES takeoff.vendors(vendor_id),
    quote_number VARCHAR(50),
    quote_date DATE,
    expiration_date DATE,
    contact_person VARCHAR(100),
    contact_email VARCHAR(100),
    contact_phone VARCHAR(20),
    total_amount DECIMAL(12,2),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'expired', 'accepted', 'rejected', 'superseded')),
    notes TEXT,
    plan_id INTEGER REFERENCES takeoff.plans(plan_id),
    job_id INTEGER REFERENCES takeoff.jobs(job_id),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create vendor_quote_lines table
CREATE TABLE IF NOT EXISTS takeoff.vendor_quote_lines (
    quote_line_id SERIAL PRIMARY KEY,
    quote_id INTEGER NOT NULL REFERENCES takeoff.vendor_quotes(quote_id) ON DELETE CASCADE,
    cost_code INTEGER,
    product_description TEXT,
    quantity DECIMAL(10,3),
    unit_price DECIMAL(10,2),
    unit_of_measure VARCHAR(20),
    line_total DECIMAL(12,2),
    notes TEXT,
    product_id INTEGER REFERENCES takeoff.items(item_id),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create file_attachments table
CREATE TABLE IF NOT EXISTS takeoff.file_attachments (
    file_id SERIAL PRIMARY KEY,
    quote_id INTEGER REFERENCES takeoff.vendor_quotes(quote_id) ON DELETE CASCADE,
    job_id INTEGER REFERENCES takeoff.jobs(job_id) ON DELETE CASCADE,
    plan_id INTEGER REFERENCES takeoff.plans(plan_id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES takeoff.items(item_id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(10),
    file_size INTEGER,
    uploaded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_vendor_quotes_vendor_id ON takeoff.vendor_quotes(vendor_id);
CREATE INDEX IF NOT EXISTS idx_vendor_quotes_status ON takeoff.vendor_quotes(status);
CREATE INDEX IF NOT EXISTS idx_vendor_quotes_date ON takeoff.vendor_quotes(quote_date);
CREATE INDEX IF NOT EXISTS idx_vendor_quote_lines_quote_id ON takeoff.vendor_quote_lines(quote_id);
CREATE INDEX IF NOT EXISTS idx_vendor_quote_lines_cost_code ON takeoff.vendor_quote_lines(cost_code);
CREATE INDEX IF NOT EXISTS idx_file_attachments_quote_id ON takeoff.file_attachments(quote_id);

-- Add comments for documentation
COMMENT ON TABLE takeoff.vendor_quotes IS 'Vendor quotes for materials and services';
COMMENT ON TABLE takeoff.vendor_quote_lines IS 'Individual line items within vendor quotes';
COMMENT ON TABLE takeoff.file_attachments IS 'File attachments linked to quotes, jobs, plans, or items';

-- Add unique constraint on quote number per vendor
ALTER TABLE takeoff.vendor_quotes ADD CONSTRAINT uq_vendor_quote_number 
    UNIQUE (vendor_id, quote_number);

-- Add check constraint for positive amounts
ALTER TABLE takeoff.vendor_quotes ADD CONSTRAINT chk_positive_amount 
    CHECK (total_amount IS NULL OR total_amount >= 0);

ALTER TABLE takeoff.vendor_quote_lines ADD CONSTRAINT chk_positive_line_total 
    CHECK (line_total IS NULL OR line_total >= 0);

-- Update trigger for vendor_quotes
CREATE OR REPLACE FUNCTION update_vendor_quotes_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_date = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_vendor_quotes_timestamp ON takeoff.vendor_quotes;
CREATE TRIGGER trigger_update_vendor_quotes_timestamp
    BEFORE UPDATE ON takeoff.vendor_quotes
    FOR EACH ROW
    EXECUTE FUNCTION update_vendor_quotes_timestamp();

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON takeoff.vendor_quotes TO Jon;
GRANT SELECT, INSERT, UPDATE, DELETE ON takeoff.vendor_quote_lines TO Jon;
GRANT SELECT, INSERT, UPDATE, DELETE ON takeoff.file_attachments TO Jon;
GRANT USAGE, SELECT ON SEQUENCE takeoff.vendor_quotes_quote_id_seq TO Jon;
GRANT USAGE, SELECT ON SEQUENCE takeoff.vendor_quote_lines_quote_line_id_seq TO Jon;
GRANT USAGE, SELECT ON SEQUENCE takeoff.file_attachments_file_id_seq TO Jon;

-- Insert some sample data for testing
INSERT INTO takeoff.vendor_quotes (vendor_id, quote_number, quote_date, status, total_amount, notes)
SELECT 
    v.vendor_id,
    'Q-2024-' || LPAD(v.vendor_id::text, 3, '0'),
    CURRENT_DATE - INTERVAL '30 days',
    'active',
    15000.00,
    'Sample quote for testing purposes'
FROM takeoff.vendors v
LIMIT 3
ON CONFLICT (vendor_id, quote_number) DO NOTHING;

COMMIT;
