-- Migration 030: Enhance takeoffs table for direct editing
-- This migration creates a comprehensive takeoffs table that supports all fields
-- needed for the qty takeoffs grid, replacing the need for complex view updates

-- First, let's see what the current takeoffs table looks like and back it up
CREATE TABLE IF NOT EXISTS takeoff.takeoffs_backup_030 AS 
SELECT * FROM takeoff.takeoffs;

-- Drop the existing simple takeoffs table
DROP TABLE IF EXISTS takeoff.takeoffs CASCADE;

-- Create the comprehensive takeoffs table
CREATE TABLE takeoff.takeoffs (
    takeoff_id SERIAL PRIMARY KEY,
    
    -- Core identification
    job_id INT REFERENCES takeoff.jobs(job_id),
    product_id INT REFERENCES takeoff.products(product_id),
    vendor_id INT REFERENCES takeoff.vendors(vendor_id),
    plan_option_id INT REFERENCES takeoff.plan_options(plan_option_id),
    item_id INT REFERENCES takeoff.items(item_id),
    cost_code_id INT REFERENCES takeoff.cost_codes(cost_code_id),
    
    -- Editable takeoff fields
    item_description TEXT,
    quantity_source VARCHAR(255),
    quantity DECIMAL(12,4),
    unit_price DECIMAL(12,4),
    price_factor DECIMAL(8,4) DEFAULT 1.0,
    unit_of_measure VARCHAR(50) DEFAULT 'EA',
    extended_price DECIMAL(15,2),
    notes TEXT,
    
    -- Job details (can be denormalized for easier editing)
    job_name VARCHAR(255),
    job_number VARCHAR(100),
    lot_number VARCHAR(100),
    customer_name VARCHAR(255),
    room VARCHAR(255),
    spec_name VARCHAR(255),
    
    -- Timestamps
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT takeoffs_quantity_check CHECK (quantity >= 0),
    CONSTRAINT takeoffs_unit_price_check CHECK (unit_price >= 0),
    CONSTRAINT takeoffs_extended_price_check CHECK (extended_price >= 0)
);

-- Create indexes for performance
CREATE INDEX idx_takeoffs_job_id ON takeoff.takeoffs(job_id);
CREATE INDEX idx_takeoffs_product_id ON takeoff.takeoffs(product_id);
CREATE INDEX idx_takeoffs_vendor_id ON takeoff.takeoffs(vendor_id);
CREATE INDEX idx_takeoffs_plan_option_id ON takeoff.takeoffs(plan_option_id);
CREATE INDEX idx_takeoffs_item_id ON takeoff.takeoffs(item_id);
CREATE INDEX idx_takeoffs_cost_code_id ON takeoff.takeoffs(cost_code_id);

-- Create trigger to auto-update updated_date
CREATE OR REPLACE FUNCTION takeoff.update_takeoffs_updated_date()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_date = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_takeoffs_updated_date
    BEFORE UPDATE ON takeoff.takeoffs
    FOR EACH ROW
    EXECUTE FUNCTION takeoff.update_takeoffs_updated_date();

-- Create trigger to auto-calculate extended_price when quantity or unit_price changes
CREATE OR REPLACE FUNCTION takeoff.calculate_takeoffs_extended_price()
RETURNS TRIGGER AS $$
BEGIN
    -- Auto-calculate extended_price if not explicitly set
    IF NEW.extended_price IS NULL OR OLD.quantity != NEW.quantity OR OLD.unit_price != NEW.unit_price OR OLD.price_factor != NEW.price_factor THEN
        NEW.extended_price = COALESCE(NEW.quantity, 0) * COALESCE(NEW.unit_price, 0) * COALESCE(NEW.price_factor, 1.0);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_takeoffs_calculate_extended_price
    BEFORE INSERT OR UPDATE ON takeoff.takeoffs
    FOR EACH ROW
    EXECUTE FUNCTION takeoff.calculate_takeoffs_extended_price();

-- Restore any existing data from backup (if there was any)
-- Use INSERT without specifying takeoff_id to let SERIAL auto-generate
INSERT INTO takeoff.takeoffs (
    job_id, product_id, vendor_id, quantity, unit_price, extended_price, quantity_source
)
SELECT 
    job_id, product_id, vendor_id, quantity, unit_price, extended_price, quantity_source
FROM takeoff.takeoffs_backup_030
WHERE EXISTS (SELECT 1 FROM takeoff.takeoffs_backup_030);

-- Insert some sample data for testing (only if no data exists)
INSERT INTO takeoff.takeoffs (
    job_name, job_number, item_description, quantity_source, quantity, unit_price, unit_of_measure, notes
) 
SELECT * FROM (VALUES
    ('Sample Development Project', 'DEV-001', 'ENGINEERING SITE VISIT', 'Manual', 1.0, 500.00, 'EA', 'Initial site assessment'),
    ('Sample Development Project', 'DEV-001', 'Supervision Neighborhood', 'Manual', 1.0, 800.00, 'EA', 'Project supervision'),
    ('Sample Development Project', 'DEV-001', 'UTILITIES', 'Manual', 1.0, 1200.00, 'LS', 'Utility connections')
) AS sample_data(job_name, job_number, item_description, quantity_source, quantity, unit_price, unit_of_measure, notes)
WHERE NOT EXISTS (SELECT 1 FROM takeoff.takeoffs);

-- Create updated comprehensive view that works with new table structure
CREATE OR REPLACE VIEW takeoff.v_comprehensive_takeoff_analysis AS
SELECT 
    t.takeoff_id,
    
    -- Plan information
    COALESCE(pe.plan_full_name, p.plan_name) as plan_full_name,
    po.option_name,
    
    -- Cost and item information  
    cc.cost_code,
    i.item_name,
    t.item_description,
    
    -- Takeoff details
    t.quantity_source,
    t.quantity,
    -- Dynamic quantity calculation based on formula
    CASE 
        WHEN f.formula_text = 'heated_sf_inside_studs' THEN po.heated_sf_inside_studs
        WHEN f.formula_text = 'total_sf_outside_studs' THEN po.total_sf_outside_studs  
        WHEN f.formula_text = 'total_sf_outside_veneer' THEN po.total_sf_outside_veneer
        ELSE t.quantity
    END as calculated_quantity,
    
    t.unit_price,
    t.price_factor,
    t.unit_of_measure,
    t.extended_price,
    
    -- Vendor information
    v.vendor_name,
    
    -- Additional details
    t.notes,
    t.job_name,
    t.job_number,
    t.lot_number,
    t.customer_name,
    t.room,
    t.spec_name,
    
    -- Foreign keys for editing
    t.job_id,
    t.product_id,
    t.vendor_id,
    t.plan_option_id,
    t.item_id,
    t.cost_code_id,
    
    -- Timestamps
    t.created_date,
    t.updated_date

FROM takeoff.takeoffs t
LEFT JOIN takeoff.jobs j ON t.job_id = j.job_id
LEFT JOIN takeoff.products prod ON t.product_id = prod.product_id
LEFT JOIN takeoff.vendors v ON t.vendor_id = v.vendor_id
LEFT JOIN takeoff.plan_options po ON t.plan_option_id = po.plan_option_id
LEFT JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
LEFT JOIN takeoff.plans p ON pe.plan_id = p.plan_id
LEFT JOIN takeoff.items i ON t.item_id = i.item_id
LEFT JOIN takeoff.cost_codes cc ON t.cost_code_id = cc.cost_code_id
LEFT JOIN takeoff.formulas f ON i.formula_id = f.formula_id
ORDER BY t.takeoff_id;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON takeoff.takeoffs TO PUBLIC;
GRANT USAGE, SELECT ON takeoff.takeoffs_takeoff_id_seq TO PUBLIC;
GRANT SELECT ON takeoff.v_comprehensive_takeoff_analysis TO PUBLIC;

-- Clean up backup table
DROP TABLE IF EXISTS takeoff.takeoffs_backup_030;

SELECT 'Migration 030 completed: Enhanced takeoffs table for direct editing' as status;
