-- Add address fields to Jobs table
-- Migration 008: Add comprehensive address fields for job locations

SET search_path TO takeoff, public;

-- Add address fields to jobs table
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS street_address VARCHAR(255);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS address_line_2 VARCHAR(255);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS state VARCHAR(50);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS zip_code VARCHAR(20);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS country VARCHAR(50) DEFAULT 'USA';

-- Add indexes for address-based searches
CREATE INDEX IF NOT EXISTS idx_jobs_city ON jobs(city);
CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state);
CREATE INDEX IF NOT EXISTS idx_jobs_zip_code ON jobs(zip_code);

-- Create a view for complete job information including address
CREATE OR REPLACE VIEW v_job_details AS
SELECT 
    j.job_id,
    j.job_name,
    j.job_number,
    j.lot_number,
    j.customer_name,
    j.street_address,
    j.address_line_2,
    j.city,
    j.state,
    j.zip_code,
    j.country,
    j.is_template,
    d.division_name,
    c.community_name,
    p.plan_name,
    pe.elevation_name,
    pe.foundation,
    po.option_name,
    po.option_type,
    -- Concatenated full address
    CASE 
        WHEN j.street_address IS NOT NULL THEN
            CONCAT_WS(', ',
                CASE 
                    WHEN j.address_line_2 IS NOT NULL AND j.address_line_2 != '' 
                    THEN CONCAT(j.street_address, ' ', j.address_line_2)
                    ELSE j.street_address
                END,
                j.city,
                CONCAT(j.state, ' ', j.zip_code)
            )
        ELSE NULL
    END as full_address
FROM takeoff.jobs j
LEFT JOIN takeoff.divisions d ON j.division_id = d.division_id
LEFT JOIN takeoff.communities c ON j.community_id = c.community_id
LEFT JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
LEFT JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
LEFT JOIN takeoff.plans p ON pe.plan_id = p.plan_id;

-- Add comments to document the new fields
COMMENT ON COLUMN jobs.street_address IS 'Street number and name (e.g., "123 Main Street")';
COMMENT ON COLUMN jobs.address_line_2 IS 'Optional second address line (unit, apartment, suite, etc.)';
COMMENT ON COLUMN jobs.city IS 'City or town name';
COMMENT ON COLUMN jobs.state IS 'State or province (2-letter code preferred)';
COMMENT ON COLUMN jobs.zip_code IS 'ZIP/postal code';
COMMENT ON COLUMN jobs.country IS 'Country name (defaults to USA)';

SELECT 'Address fields added to Jobs table successfully!' as status;
