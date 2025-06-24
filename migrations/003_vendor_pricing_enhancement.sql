-- Vendor Pricing Enhancement Script
-- Adds proper vendor pricing management with history and file attachments

-- First, enhance the vendor_pricing table with proper history tracking
DROP TABLE IF EXISTS takeoff.vendor_pricing CASCADE;

CREATE TABLE takeoff.vendor_pricing (
    pricing_id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES takeoff.vendors(vendor_id),
    product_id INTEGER REFERENCES takeoff.products(product_id),
    price NUMERIC(12,4) NOT NULL,
    unit_of_measure VARCHAR(50),
    effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
    expiration_date DATE,
    is_current BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    price_type VARCHAR(50) DEFAULT 'standard', -- standard, quote, contract, promotional
    minimum_quantity NUMERIC(12,4) DEFAULT 1,
    notes TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100),
    UNIQUE(vendor_id, product_id, effective_date)
);

-- Create indexes for performance
CREATE INDEX idx_vendor_pricing_vendor_product ON takeoff.vendor_pricing(vendor_id, product_id);
CREATE INDEX idx_vendor_pricing_current ON takeoff.vendor_pricing(is_current, is_active);
CREATE INDEX idx_vendor_pricing_effective_date ON takeoff.vendor_pricing(effective_date);

-- Create vendor quotes table for file attachments and quote management
CREATE TABLE takeoff.vendor_quotes (
    quote_id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES takeoff.vendors(vendor_id),
    quote_number VARCHAR(100),
    quote_date DATE NOT NULL,
    expiration_date DATE,
    contact_person VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    total_amount NUMERIC(12,2),
    status VARCHAR(50) DEFAULT 'active', -- active, expired, superseded, accepted, rejected
    notes TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100)
);

-- Create quote line items table to link quotes to specific products and pricing
CREATE TABLE takeoff.quote_line_items (
    quote_line_id SERIAL PRIMARY KEY,
    quote_id INTEGER REFERENCES takeoff.vendor_quotes(quote_id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES takeoff.products(product_id),
    quantity NUMERIC(12,4),
    unit_price NUMERIC(12,4),
    unit_of_measure VARCHAR(50),
    line_total NUMERIC(12,2),
    notes TEXT,
    pricing_id INTEGER REFERENCES takeoff.vendor_pricing(pricing_id)
);

-- Create file attachments table for quotes and pricing documentation
CREATE TABLE takeoff.pricing_attachments (
    attachment_id SERIAL PRIMARY KEY,
    quote_id INTEGER REFERENCES takeoff.vendor_quotes(quote_id) ON DELETE CASCADE,
    pricing_id INTEGER REFERENCES takeoff.vendor_pricing(pricing_id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    file_type VARCHAR(100),
    mime_type VARCHAR(255),
    description TEXT,
    uploaded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uploaded_by VARCHAR(100),
    CONSTRAINT chk_attachment_reference CHECK (
        (quote_id IS NOT NULL AND pricing_id IS NULL) OR 
        (quote_id IS NULL AND pricing_id IS NOT NULL)
    )
);

-- Create price history tracking function
CREATE OR REPLACE FUNCTION track_price_history()
RETURNS TRIGGER AS $$
BEGIN
    -- When a new pricing record is inserted, mark previous ones as not current
    IF TG_OP = 'INSERT' THEN
        UPDATE takeoff.vendor_pricing 
        SET is_current = false,
            updated_date = CURRENT_TIMESTAMP
        WHERE vendor_id = NEW.vendor_id 
        AND product_id = NEW.product_id 
        AND pricing_id != NEW.pricing_id
        AND is_current = true;
        
        RETURN NEW;
    END IF;
    
    -- When updating, track the change
    IF TG_OP = 'UPDATE' THEN
        NEW.updated_date = CURRENT_TIMESTAMP;
        RETURN NEW;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for price history tracking
CREATE TRIGGER trigger_track_price_history
    AFTER INSERT OR UPDATE ON takeoff.vendor_pricing
    FOR EACH ROW
    EXECUTE FUNCTION track_price_history();

-- Create view for current vendor pricing
CREATE VIEW takeoff.v_current_vendor_pricing AS
SELECT 
    vp.pricing_id,
    v.vendor_name,
    v.vendor_id,
    p.product_description,
    p.product_id,
    i.item_name,
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
WHERE vp.is_current = true 
AND vp.is_active = true
AND (vp.expiration_date IS NULL OR vp.expiration_date >= CURRENT_DATE);

-- Create view for price history analysis
CREATE VIEW takeoff.v_price_history AS
SELECT 
    v.vendor_name,
    p.product_description,
    i.item_name,
    vp.price,
    vp.unit_of_measure,
    vp.effective_date,
    vp.expiration_date,
    vp.price_type,
    vp.is_current,
    LAG(vp.price) OVER (PARTITION BY vp.vendor_id, vp.product_id ORDER BY vp.effective_date) as previous_price,
    CASE 
        WHEN LAG(vp.price) OVER (PARTITION BY vp.vendor_id, vp.product_id ORDER BY vp.effective_date) IS NOT NULL
        THEN ROUND(((vp.price - LAG(vp.price) OVER (PARTITION BY vp.vendor_id, vp.product_id ORDER BY vp.effective_date)) / 
                   LAG(vp.price) OVER (PARTITION BY vp.vendor_id, vp.product_id ORDER BY vp.effective_date) * 100), 2)
        ELSE NULL
    END as price_change_percent
FROM takeoff.vendor_pricing vp
JOIN takeoff.vendors v ON vp.vendor_id = v.vendor_id
JOIN takeoff.products p ON vp.product_id = p.product_id
JOIN takeoff.items i ON p.item_id = i.item_id
WHERE vp.is_active = true
ORDER BY v.vendor_name, p.product_description, vp.effective_date DESC;

-- Create view for vendor quotes with totals
CREATE VIEW takeoff.v_vendor_quotes_summary AS
SELECT 
    vq.quote_id,
    vq.quote_number,
    v.vendor_name,
    vq.quote_date,
    vq.expiration_date,
    vq.status,
    vq.contact_person,
    vq.total_amount,
    COUNT(qli.quote_line_id) as line_item_count,
    COUNT(pa.attachment_id) as attachment_count,
    vq.created_date
FROM takeoff.vendor_quotes vq
JOIN takeoff.vendors v ON vq.vendor_id = v.vendor_id
LEFT JOIN takeoff.quote_line_items qli ON vq.quote_id = qli.quote_id
LEFT JOIN takeoff.pricing_attachments pa ON vq.quote_id = pa.quote_id
GROUP BY vq.quote_id, vq.quote_number, v.vendor_name, vq.quote_date, 
         vq.expiration_date, vq.status, vq.contact_person, vq.total_amount, vq.created_date;

-- Add comments for documentation
COMMENT ON TABLE takeoff.vendor_pricing IS 'Vendor pricing catalog with historical tracking';
COMMENT ON TABLE takeoff.vendor_quotes IS 'Vendor quotes and bid management';
COMMENT ON TABLE takeoff.quote_line_items IS 'Individual line items within vendor quotes';
COMMENT ON TABLE takeoff.pricing_attachments IS 'File attachments for quotes and pricing documentation';

COMMENT ON COLUMN takeoff.vendor_pricing.price_type IS 'Type of pricing: standard, quote, contract, promotional';
COMMENT ON COLUMN takeoff.vendor_pricing.effective_date IS 'Date when this price becomes effective';
COMMENT ON COLUMN takeoff.vendor_pricing.expiration_date IS 'Date when this price expires (NULL = no expiration)';
COMMENT ON COLUMN takeoff.vendor_quotes.status IS 'Quote status: active, expired, superseded, accepted, rejected';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON takeoff.vendor_pricing TO takeoff_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON takeoff.vendor_quotes TO takeoff_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON takeoff.quote_line_items TO takeoff_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON takeoff.pricing_attachments TO takeoff_user;
GRANT SELECT ON takeoff.v_current_vendor_pricing TO takeoff_user;
GRANT SELECT ON takeoff.v_price_history TO takeoff_user;
GRANT SELECT ON takeoff.v_vendor_quotes_summary TO takeoff_user;
GRANT USAGE ON SEQUENCE takeoff.vendor_pricing_pricing_id_seq TO takeoff_user;
GRANT USAGE ON SEQUENCE takeoff.vendor_quotes_quote_id_seq TO takeoff_user;
GRANT USAGE ON SEQUENCE takeoff.quote_line_items_quote_line_id_seq TO takeoff_user;
GRANT USAGE ON SEQUENCE takeoff.pricing_attachments_attachment_id_seq TO takeoff_user;
